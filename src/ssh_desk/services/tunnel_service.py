"""Port forwarding (local/remote/dynamic) via detached tunnel daemon processes."""

import logging
import os
import subprocess
import sys
from typing import Optional

from sqlalchemy import select

from ssh_desk.core.events import TOPIC_TUNNELS
from ssh_desk.core.exceptions import NotFoundError, TunnelError
from ssh_desk.database.models import Server, Tunnel
from ssh_desk.ssh import client
from ssh_desk.utils.procs import pid_alive, port_bindable
from ssh_desk.utils.validation import TunnelInput

log = logging.getLogger("ssh_desk.tunnels")


class TunnelService:
    def __init__(self, ctx):
        self.ctx = ctx

    # ------------------------------------------------------------------ CRUD
    def create(self, server_id: int, name: str, data: TunnelInput) -> Tunnel:
        with self.ctx.db.session() as session:
            if not session.get(Server, server_id):
                raise NotFoundError("Server not found")
            exists = session.scalars(
                select(Tunnel).where(Tunnel.server_id == server_id, Tunnel.name == name)
            ).first()
            if exists:
                raise TunnelError(f"Tunnel '{name}' already exists for this server")
            tunnel = Tunnel(
                server_id=server_id,
                name=name,
                tunnel_type=data.tunnel_type,
                local_host=data.local_host,
                local_port=data.local_port,
                remote_host=data.remote_host,
                remote_port=data.remote_port,
            )
            session.add(tunnel)
            session.commit()
            session.refresh(tunnel)
            tunnel_id = tunnel.id
        self.ctx.events.publish(TOPIC_TUNNELS, {"action": "create", "id": tunnel_id})
        return self.get(tunnel_id)

    def update(self, tunnel_id: int, name: str, data: TunnelInput) -> Tunnel:
        with self.ctx.db.session() as session:
            tunnel = session.get(Tunnel, tunnel_id)
            if not tunnel:
                raise NotFoundError("Tunnel not found")
            if tunnel.status == "running":
                raise TunnelError("Stop the tunnel before editing it")
            tunnel.name = name
            tunnel.tunnel_type = data.tunnel_type
            tunnel.local_host = data.local_host
            tunnel.local_port = data.local_port
            tunnel.remote_host = data.remote_host
            tunnel.remote_port = data.remote_port
            session.commit()
            session.refresh(tunnel)
        self.ctx.events.publish(TOPIC_TUNNELS, {"action": "update", "id": tunnel_id})
        return tunnel

    def delete(self, tunnel_id: int) -> None:
        self.stop(tunnel_id, silent=True)
        with self.ctx.db.session() as session:
            tunnel = session.get(Tunnel, tunnel_id)
            if tunnel:
                session.delete(tunnel)
                session.commit()
        self.ctx.events.publish(TOPIC_TUNNELS, {"action": "delete", "id": tunnel_id})

    def get(self, tunnel_id: int) -> Tunnel:
        with self.ctx.db.session() as session:
            tunnel = session.get(Tunnel, tunnel_id)
            if not tunnel:
                raise NotFoundError("Tunnel not found")
            return tunnel

    def list(self) -> list[Tunnel]:
        with self.ctx.db.session() as session:
            return list(session.scalars(select(Tunnel).order_by(Tunnel.name)))

    # ------------------------------------------------------------------ control
    def port_spec(self, tunnel: Tunnel) -> str:
        if tunnel.tunnel_type == "local":
            return f"-L {tunnel.local_host}:{tunnel.local_port}:{tunnel.remote_host}:{tunnel.remote_port}"
        if tunnel.tunnel_type == "remote":
            return f"-R {tunnel.local_host}:{tunnel.local_port}:{tunnel.remote_host}:{tunnel.remote_port}"
        return f"-D {tunnel.local_host}:{tunnel.local_port}"

    def start(self, tunnel_id: int) -> Tunnel:
        tunnel = self.get(tunnel_id)
        if tunnel.status == "running" and tunnel.pid and pid_alive(tunnel.pid):
            return tunnel
        if not port_bindable(tunnel.local_host, tunnel.local_port):
            raise TunnelError(
                f"Cannot bind {tunnel.local_host}:{tunnel.local_port} - port already in use or not permitted"
            )
        server = self.ctx.servers.get(tunnel.server_id)
        if server.auth_type == "key" and server.private_key_path:
            key_record = self.ctx.keys.get_by_path(server.private_key_path)
            if key_record and key_record.passphrase_ref:
                server.key_passphrase_ref = key_record.passphrase_ref
        from ssh_desk.services.connection_service import NonInteractiveGate

        self.ctx.connections.check_host_key(server, NonInteractiveGate())
        argv, env = client.build_tunnel_argv(self.ctx, server, port_spec=self.port_spec(tunnel))

        log_file = open(os.path.join(self.ctx.data_dir, "logs", f"tunnel-{tunnel.id}.log"), "ab")
        runner_module = "ssh_desk.ssh.tunnel_runner"
        proc = subprocess.Popen(
            [sys.executable, "-m", runner_module, str(tunnel.id)],
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={**os.environ, **env},
        )
        log.info("tunnel daemon started for '%s' (runner pid %s)", tunnel.name, proc.pid)
        return self.refresh_status(tunnel.id)

    def stop(self, tunnel_id: int, silent: bool = False) -> Tunnel:
        tunnel = self.get(tunnel_id)
        if tunnel.pid:
            from ssh_desk.utils.procs import terminate_tree

            terminate_tree(tunnel.pid)
        if not silent:
            return self.refresh_status(tunnel_id)
        with self.ctx.db.session() as session:
            row = session.get(Tunnel, tunnel_id)
            if row:
                row.status = "stopped"
                row.pid = None
                session.commit()
        self.ctx.events.publish(TOPIC_TUNNELS, {"action": "stopped", "id": tunnel_id})
        return self.get(tunnel_id)

    def refresh_status(self, tunnel_id: int) -> Tunnel:
        with self.ctx.db.session() as session:
            tunnel = session.get(Tunnel, tunnel_id)
            if not tunnel:
                raise NotFoundError("Tunnel not found")
            if tunnel.status == "running":
                if not (tunnel.pid and pid_alive(tunnel.pid)):
                    tunnel.status = "stopped"
                    tunnel.pid = None
            session.commit()
            session.refresh(tunnel)
        self.ctx.events.publish(TOPIC_TUNNELS, {"action": "refresh", "id": tunnel_id})
        return tunnel

    def refresh_all(self) -> None:
        for tunnel in self.list():
            self.refresh_status(tunnel.id)
