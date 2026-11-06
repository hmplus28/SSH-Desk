"""Credential management.

Security rules enforced here:
- Passwords/passphrases are stored ONLY in the Secret Service (GNOME Keyring).
- Nothing sensitive is ever written to SQLite, config files or logs.
- The database only keeps a non-secret *reference* (attribute set) to the item.
"""

import json
import logging
from typing import Optional

from ssh_desk.core.exceptions import KeyringUnavailableError

log = logging.getLogger("ssh_desk.credentials")

SCHEMA_ATTR = "xdg:schema"
APP_ATTR = "ssh-desk.application"
SCHEMA_VALUE = "org.ssh_desk.Secret"


class _Base64Json:
    pass


def _ref(attrs: dict) -> str:
    return json.dumps(attrs, sort_keys=True)


class SecretServiceStore:
    """Secret Service (GNOME Keyring) backend using SecretStorage."""

    def __init__(self):
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import secretstorage
        except ImportError as exc:  # pragma: no cover
            raise KeyringUnavailableError(
                "SecretStorage package is missing",
                hint="pip install SecretStorage",
            ) from exc
        try:
            bus = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(bus)
            if collection.is_locked():
                collection.unlock()
                if collection.is_locked():
                    raise KeyringUnavailableError(
                        "Keyring is locked",
                        hint="Unlock the keyring (seahorse / gnome-keyring-daemon) and try again",
                    )
            self._collection = collection
            return collection
        except KeyringUnavailableError:
            raise
        except Exception as exc:
            raise KeyringUnavailableError(
                f"Secret Service is not available: {type(exc).__name__}",
                hint="Install it with: sudo apt install gnome-keyring libsecret-1-0 "
                "and make sure a keyring daemon is running (gnome-keyring-daemon).",
            ) from exc

    def store(self, attrs: dict, secret: str, label: str) -> str:
        collection = self._get_collection()
        full_attrs = {**attrs, APP_ATTR: "ssh-desk", SCHEMA_ATTR: SCHEMA_VALUE}
        import secretstorage

        for item in collection.search_items({APP_ATTR: "ssh-desk", **attrs}):
            item.delete()
        collection.create_item(label, full_attrs, secret.encode("utf-8"), replace=True)
        return _ref(attrs)

    def retrieve(self, ref: str) -> Optional[str]:
        attrs = json.loads(ref)
        collection = self._get_collection()
        import secretstorage

        for item in collection.search_items(attrs):
            if item.is_locked():
                item.unlock()
            secret = item.get_secret()
            return secret.decode("utf-8") if secret else None
        return None

    def delete(self, ref: str) -> bool:
        attrs = json.loads(ref)
        collection = self._get_collection()
        deleted = False
        for item in collection.search_items(attrs):
            item.delete()
            deleted = True
        return deleted

    def purge_all(self) -> int:
        collection = self._get_collection()
        count = 0
        for item in collection.search_items({APP_ATTR: "ssh-desk"}):
            item.delete()
            count += 1
        return count

    def available(self) -> bool:
        try:
            self._get_collection()
            return True
        except KeyringUnavailableError:
            return False


class MemorySecretStore:
    """In-memory backend for automated tests ONLY (never used in the product)."""

    def __init__(self):
        self._items: dict[str, tuple[dict, str, str]] = {}

    def store(self, attrs: dict, secret: str, label: str) -> str:
        ref = _ref(attrs)
        self._items[ref] = (dict(attrs), secret, label)
        return ref

    def retrieve(self, ref: str) -> Optional[str]:
        item = self._items.get(ref)
        return item[1] if item else None

    def delete(self, ref: str) -> bool:
        return self._items.pop(ref, None) is not None

    def purge_all(self) -> int:
        count = len(self._items)
        self._items.clear()
        return count

    def available(self) -> bool:
        return True


class CredentialService:
    """High-level credential API used by services/GUI/CLI."""

    def __init__(self, ctx, store=None):
        self.ctx = ctx
        self.store = store or SecretServiceStore()

    # -- server passwords -------------------------------------------------
    def store_server_password(self, server_id: int, alias: str, password: str) -> str:
        from ssh_desk.utils.logging_setup import register_secret

        register_secret(password)
        attrs = {"ssh-desk.type": "server", "ssh-desk.id": str(server_id)}
        return self.store.store(attrs, password, f"SSH Desk - server: {alias}")

    def get_server_password(self, server) -> Optional[str]:
        ref = getattr(server, "secret_ref", None)
        if not ref:
            return None
        secret = self.store.retrieve(ref)
        if secret is None:
            raise SecretNotFoundError(
                f"Stored secret for '{server.alias}' is missing from the keyring",
                hint="Re-enter the password in the server editor.",
            )
        from ssh_desk.utils.logging_setup import register_secret

        register_secret(secret)
        return secret

    def delete_server_secret(self, server) -> None:
        ref = getattr(server, "secret_ref", None)
        if ref:
            try:
                self.store.delete(ref)
            except KeyringUnavailableError:
                log.warning("keyring unavailable; could not delete secret for %s", server.alias)

    # -- key passphrases --------------------------------------------------
    def store_key_passphrase(self, key_name: str, passphrase: str) -> str:
        from ssh_desk.utils.logging_setup import register_secret

        register_secret(passphrase)
        attrs = {"ssh-desk.type": "key", "ssh-desk.name": key_name}
        return self.store.store(attrs, passphrase, f"SSH Desk - key: {key_name}")

    def get_key_passphrase(self, ref: str) -> Optional[str]:
        secret = self.store.retrieve(ref)
        if secret:
            from ssh_desk.utils.logging_setup import register_secret

            register_secret(secret)
        return secret

    def delete_key_passphrase(self, ref: str) -> None:
        if ref:
            try:
                self.store.delete(ref)
            except KeyringUnavailableError:
                pass

    # -- ephemeral secrets (connection test before save) -------------------
    def store_ephemeral(self, purpose: str, password: str) -> str:
        from ssh_desk.utils.logging_setup import register_secret

        register_secret(password)
        attrs = {"ssh-desk.type": "ephemeral", "ssh-desk.id": purpose}
        return self.store.store(attrs, password, f"SSH Desk - ephemeral: {purpose}")

    def delete_ref(self, ref: str) -> None:
        if ref:
            try:
                self.store.delete(ref)
            except KeyringUnavailableError:
                pass

    def purge_all(self) -> int:
        return self.store.purge_all()

    def available(self) -> bool:
        return self.store.available()
