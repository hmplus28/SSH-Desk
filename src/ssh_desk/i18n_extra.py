"""Extra language tables merged into ``ssh_desk.i18n.STRINGS`` on import."""

from ssh_desk.translations.ar import TABLE as _AR
from ssh_desk.translations.es import TABLE as _ES
from ssh_desk.translations.fr import TABLE as _FR
from ssh_desk.translations.ru import TABLE as _RU
from ssh_desk.translations.zh import TABLE as _ZH

EXTRA_LANGS: dict[str, dict[str, str]] = {
    "ar": _AR,
    "zh": _ZH,
    "ru": _RU,
    "es": _ES,
    "fr": _FR,
}
