"""Connection history recording. Terminal contents and passwords are never stored."""

from __future__ import annotations

import logging

from sqlalchemy import select

from ssh_desk.core.events import TOPIC_HISTORY
from ssh_desk.database.models import ConnectionHistory

log = logging.getLogger("ssh_desk.history")


class HistoryService:
    def __init__(self, ctx):
        self.ctx = ctx

    def start(self, server) -> int:
        with self.ctx.db.session() as session:
            row = ConnectionHistory(
                server_id=server.id,
                server_alias=server.alias,
                server_name=server.name,
                status="connected",
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            history_id = row.id
        self.ctx.events.publish(TOPIC_HISTORY, {"action": "start"})
        return history_id

    def close(self, history_id: int, status: str, error_message: str | None = None) -> None:
        error = (error_message or "")[:500]
        from ssh_desk.database.models import utcnow

        with self.ctx.db.session() as session:
            row = session.get(ConnectionHistory, history_id)
            if not row:
                return
            row.disconnected_at = utcnow()
            row.status = status
            if error:
                row.error_message = error
            session.commit()
        self.ctx.events.publish(TOPIC_HISTORY, {"action": "close"})

    def list(self, *, server_id=None, alias: str = "", status: str = "", limit: int = 50) -> list[ConnectionHistory]:
        with self.ctx.db.session() as session:
            query = select(ConnectionHistory).order_by(ConnectionHistory.connected_at.desc()).limit(int(limit))
            if server_id is not None:
                query = query.where(ConnectionHistory.server_id == server_id)
            if alias:
                query = query.where(ConnectionHistory.server_alias.like(f"%{alias.lower()}%"))
            if status:
                query = query.where(ConnectionHistory.status == status)
            return list(session.scalars(query))

    def recent(self, limit: int = 8) -> list[ConnectionHistory]:
        return self.list(limit=limit)

    def clear(self) -> int:
        with self.ctx.db.session() as session:
            rows = list(session.scalars(select(ConnectionHistory)))
            count = len(rows)
            for row in rows:
                session.delete(row)
            session.commit()
        self.ctx.events.publish(TOPIC_HISTORY, {"action": "clear"})
        return count
