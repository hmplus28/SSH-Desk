"""Backward-compatible re-export: the real i18n lives in ``ssh_desk.i18n``."""

from ssh_desk.i18n import (  # noqa: F401
    LANGS,
    LANGUAGE_NAMES,
    RTL_LANGS,
    STRINGS,
    current_language,
    is_rtl,
    set_language,
    tr,
)
