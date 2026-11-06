"""Exception hierarchy for SSH Desk. All user-facing errors derive from SshDeskError."""


class SshDeskError(Exception):
    """Base class for all application errors."""

    def __init__(self, message: str, hint: str = ""):
        super().__init__(message)
        self.hint = hint


class ValidationErrorX(SshDeskError):
    """Invalid user input / failed pydantic validation."""


class NotFoundError(SshDeskError):
    """Requested entity does not exist."""


class AliasExistsError(SshDeskError):
    """Alias already used by another server."""


class PathNotFoundError(SshDeskError):
    """Saved path name not found for a server."""


class KeyringUnavailableError(SshDeskError):
    """Secret Service / GNOME Keyring is not reachable."""


class SecretNotFoundError(SshDeskError):
    """Referenced secret does not exist in the keyring anymore."""


class HostKeyUnknownError(SshDeskError):
    def __init__(self, message: str, fingerprints=None, hint: str = ""):
        super().__init__(message, hint)
        self.fingerprints = fingerprints or []


class HostKeyChangedError(SshDeskError):
    def __init__(self, message: str, expected=None, actual=None, hint: str = ""):
        super().__init__(message, hint)
        self.expected = expected or []
        self.actual = actual or []


class SSHConnectionError(SshDeskError):
    """SSH connection failed."""


class AuthError(SshDeskError):
    """Authentication failed."""


class TunnelError(SshDeskError):
    """Tunnel operation failed."""


class SftpError(SshDeskError):
    """SFTP file operation failed."""


class ConfigError(SshDeskError):
    """Configuration file problem."""
