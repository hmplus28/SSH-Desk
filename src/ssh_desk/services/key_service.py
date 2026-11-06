"""SSH key management: generation (OpenSSH format via cryptography), import/export, fingerprints."""

import logging
import shutil
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from sqlalchemy import select

from ssh_desk.core.events import TOPIC_KEYS
from ssh_desk.core.exceptions import NotFoundError, ValidationErrorX
from ssh_desk.database.models import Server, SSHKey
from ssh_desk.ssh.hostkeys import fingerprint_from_blob
from ssh_desk.utils.validation import KeyInput

log = logging.getLogger("ssh_desk.keys")


class KeyService:
    def __init__(self, ctx):
        self.ctx = ctx

    @property
    def keys_dir(self) -> Path:
        d = Path(self.ctx.data_dir) / "keys"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------ generate
    def generate(self, name: str, key_type: str = "ed25519", bits: int = 4096,
                 comment: str = "", passphrase: str = "") -> SSHKey:
        data = KeyInput(name=name)
        name = data.name
        target_dir = self.keys_dir / name
        if target_dir.exists():
            raise ValidationErrorX(f"Key '{name}' already exists")
        target_dir.mkdir(parents=True)
        private_path = target_dir / f"id_{key_type}"
        public_path = target_dir / f"id_{key_type}.pub"

        encryption = (
            serialization.BestAvailableEncryption(passphrase.encode())
            if passphrase
            else serialization.NoEncryption()
        )
        if key_type == "ed25519":
            private_key = ed25519.Ed25519PrivateKey.generate()
            ssh_type = "ssh-ed25519"
        elif key_type == "rsa":
            if bits < 2048:
                raise ValidationErrorX("RSA key size must be at least 2048 bits")
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
            ssh_type = "ssh-rsa"
        elif key_type == "ecdsa":
            private_key = ec.generate_private_key(ec.SECP256R1())
            ssh_type = "ecdsa-sha2-nistp256"
        else:
            raise ValidationErrorX(f"Unsupported key type: {key_type}")

        pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            encryption,
        )
        public = private_key.public_key().public_bytes(
            serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
        )
        comment_part = f" {comment}" if comment else ""
        public_path.write_bytes(public + comment_part.encode() + b"\n")
        private_path.write_bytes(pem)
        private_path.chmod(0o600)
        public_path.chmod(0o644)

        blob = public.decode().split()[1]
        fingerprint = fingerprint_from_blob(blob)
        return self._register(
            name=name,
            private_path=str(private_path),
            public_path=str(public_path),
            key_type=key_type,
            bits=bits if key_type == "rsa" else None,
            fingerprint=fingerprint,
            comment=comment,
            passphrase=passphrase,
            stored_copy=True,
        )

    # ------------------------------------------------------------------ import
    def import_key(self, name: str, private_path: str, copy_into_store: bool = False,
                   passphrase: str = "") -> SSHKey:
        data = KeyInput(name=name)
        name = data.name
        src = Path(private_path).expanduser()
        if not src.exists():
            raise NotFoundError(f"Private key file not found: {src}")

        key_type, bits, fingerprint, public_text = self._load_private(src, passphrase)

        if copy_into_store:
            target_dir = self.keys_dir / name
            if target_dir.exists():
                raise ValidationErrorX(f"Key '{name}' already exists in SSH Desk storage")
            target_dir.mkdir(parents=True)
            dst_private = target_dir / src.name
            shutil.copy2(src, dst_private)
            dst_private.chmod(0o600)
            private_final = str(dst_private)
            public_path = target_dir / (src.name + ".pub")
            if public_text:
                public_path.write_text(public_text)
                public_path.chmod(0o644)
            public_final = str(public_path)
            stored_copy = True
        else:
            # reference the original file; never copy private material without consent
            private_final = str(src)
            pub_candidate = Path(str(src) + ".pub")
            public_final = str(pub_candidate) if pub_candidate.exists() else ""
            stored_copy = False

        return self._register(
            name=name,
            private_path=private_final,
            public_path=public_final,
            key_type=key_type,
            bits=bits,
            fingerprint=fingerprint,
            comment="",
            passphrase=passphrase if copy_into_store else "",
            stored_copy=stored_copy,
        )

    # ------------------------------------------------------------------ queries
    def list(self) -> list[SSHKey]:
        with self.ctx.db.session() as session:
            return list(session.scalars(select(SSHKey).order_by(SSHKey.name)))

    def get(self, key_id: int) -> SSHKey:
        with self.ctx.db.session() as session:
            key = session.get(SSHKey, key_id)
            if not key:
                raise NotFoundError(f"Key id={key_id} not found")
            return key

    def get_by_path(self, path: str) -> Optional[SSHKey]:
        with self.ctx.db.session() as session:
            return session.scalars(select(SSHKey).where(SSHKey.private_key_path == str(path))).first()

    def delete(self, key_id: int, delete_files: bool = False) -> None:
        with self.ctx.db.session() as session:
            key = session.get(SSHKey, key_id)
            if not key:
                raise NotFoundError("Key not found")
            if key.passphrase_ref:
                self.ctx.credentials.delete_key_passphrase(key.passphrase_ref)
            private_path, public_path = key.private_key_path, key.public_key_path
            session.delete(key)
            session.commit()
        if delete_files and private_path:
            try:
                Path(private_path).unlink(missing_ok=True)
                if public_path:
                    Path(public_path).unlink(missing_ok=True)
            except OSError as exc:
                log.warning("could not delete key files: %s", exc)
        self.ctx.events.publish(TOPIC_KEYS, {"action": "delete", "id": key_id})

    def export_public(self, key_id: int) -> str:
        key = self.get(key_id)
        candidates = []
        if key.public_key_path:
            candidates.append(Path(key.public_key_path))
        candidates.append(Path(key.private_key_path + ".pub"))
        for path in candidates:
            if path.exists():
                return path.read_text().strip()
        # derive from the private key
        key_obj = self._load_private_object(Path(key.private_key_path))
        return key_obj.public_key().public_bytes(
            serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
        ).decode()

    def linked_servers(self, key_id: int) -> list[Server]:
        key = self.get(key_id)
        with self.ctx.db.session() as session:
            return list(session.scalars(select(Server).where(Server.private_key_path == key.private_key_path)))

    def set_passphrase(self, key_id: int, passphrase: str) -> SSHKey:
        with self.ctx.db.session() as session:
            key = session.get(SSHKey, key_id)
            if not key:
                raise NotFoundError("Key not found")
            if passphrase:
                key.passphrase_ref = self.ctx.credentials.store_key_passphrase(key.name, passphrase)
            else:
                self.ctx.credentials.delete_key_passphrase(key.passphrase_ref or "")
                key.passphrase_ref = None
            session.commit()
            session.refresh(key)
        return key

    # ------------------------------------------------------------------ internals
    def _register(self, *, name, private_path, public_path, key_type, bits, fingerprint, comment, passphrase, stored_copy) -> SSHKey:
        with self.ctx.db.session() as session:
            exists = session.scalars(select(SSHKey).where(SSHKey.name == name)).first()
            if exists:
                raise ValidationErrorX(f"Key name '{name}' is already registered")
            key = SSHKey(
                name=name,
                private_key_path=private_path,
                public_key_path=public_path or None,
                key_type=key_type,
                bits=bits,
                fingerprint=fingerprint,
                comment=comment,
                stored_copy=stored_copy,
            )
            session.add(key)
            session.commit()
            session.refresh(key)
            key_id = key.id
        if passphrase:
            self.set_passphrase(key_id, passphrase)
        self.ctx.events.publish(TOPIC_KEYS, {"action": "create", "id": key_id})
        log.info("SSH key registered: %s (%s)", name, fingerprint)
        return self.get(key_id)

    def _load_private(self, path: Path, passphrase: str):
        key_obj = self._load_private_object(path, passphrase)
        key_type, bits = self._classify(key_obj)
        public = key_obj.public_key().public_bytes(
            serialization.Encoding.OpenSSH, serialization.PublicFormat.OpenSSH
        ).decode()
        blob = public.split()[1]
        fingerprint = fingerprint_from_blob(blob)
        return key_type, bits, fingerprint, public

    @staticmethod
    def _load_private_object(path: Path, passphrase: str = ""):
        password = passphrase.encode() if passphrase else None
        try:
            return serialization.load_ssh_private_key(path.read_bytes(), password=password)
        except Exception:
            try:
                return serialization.load_pem_private_key(path.read_bytes(), password=password)
            except Exception as exc:
                kind = "wrong passphrase" if passphrase else "encrypted key or unsupported format"
                raise ValidationErrorX(f"Cannot read private key {path}: {kind} ({type(exc).__name__})") from exc

    @staticmethod
    def _classify(key_obj) -> tuple[str, Optional[int]]:
        if isinstance(key_obj, ed25519.Ed25519PrivateKey):
            return "ed25519", None
        if isinstance(key_obj, rsa.RSAPrivateKey):
            return "rsa", key_obj.key_size
        if isinstance(key_obj, ec.EllipticCurvePrivateKey):
            return "ecdsa", key_obj.curve.key_size
        return "unknown", None
