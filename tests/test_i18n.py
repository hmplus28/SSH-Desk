"""i18n: 7 languages must be complete, consistent and RTL-correct."""

import re

from ssh_desk.i18n import LANGS, LANGUAGE_NAMES, STRINGS, is_rtl, set_language, tr

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def _placeholders(text: str) -> list[str]:
    return sorted(PLACEHOLDER_RE.findall(text))


def test_seven_languages_defined():
    assert set(LANGS) == {"en", "fa", "ar", "zh", "ru", "es", "fr"}
    assert set(LANGUAGE_NAMES) == set(LANGS)


def test_every_key_has_every_language():
    missing = [
        (key, lang)
        for key, entry in STRINGS.items()
        for lang in LANGS
        if lang not in entry
    ]
    assert missing == []


def test_placeholders_match_english():
    """Formatted values ({alias}, {ms}, {n}, ...) must exist in every language."""
    bad = []
    for key, entry in STRINGS.items():
        base = _placeholders(entry["en"])
        for lang, value in entry.items():
            if _placeholders(value) != base:
                bad.append((key, lang))
    assert bad == []


def test_no_empty_translations():
    empty = [
        (key, lang)
        for key, entry in STRINGS.items()
        for lang, value in entry.items()
        if not value.strip()
    ]
    assert empty == []


def test_fallback_to_english(monkeypatch):
    monkeypatch.setattr("ssh_desk.i18n._current_lang", "en")
    assert tr("ok") == "OK"


def test_unknown_key_returns_key():
    set_language("en")
    assert tr("no_such_key_xyz") == "no_such_key_xyz"


def test_format_arguments():
    set_language("en")
    assert tr("statusbar_sessions", n=3) == "3 active session(s)"
    assert tr("session_ended", code=0) == "Session ended (code 0)"


def test_set_language_accepts_locale_suffix():
    set_language("fa_IR")
    assert is_rtl() and current_lang() == "fa"
    set_language("zh_CN.UTF-8")
    assert current_lang() == "zh"
    set_language("fr_FR")
    assert current_lang() == "fr"
    set_language("xx_UNKNOWN")
    assert current_lang() == "en"


def current_lang() -> str:
    from ssh_desk import i18n

    return i18n._current_lang


def test_rtl_languages_are_fa_and_ar():
    set_language("fa")
    assert is_rtl()
    set_language("ar")
    assert is_rtl()
    set_language("en")
    assert not is_rtl()
    for lang in ("zh", "ru", "es", "fr"):
        set_language(lang)
        assert not is_rtl()


def test_all_ui_languages_translate_common_words():
    set_language("ar")
    assert tr("connect") == "اتصال"
    set_language("zh")
    assert tr("connect") == "连接"
    set_language("ru")
    assert tr("connect") == "Подключиться"
    set_language("es")
    assert tr("connect") == "Conectar"
    set_language("fr")
    assert tr("connect") == "Se connecter"
    set_language("fa")
    assert tr("connect") == "اتصال"


def test_gui_shim_shares_state():
    """gui.i18n must expose the same module state (single source of truth)."""
    from ssh_desk import i18n as core_i18n
    from ssh_desk.gui import i18n as gui_i18n

    set_language("fa")
    assert gui_i18n.current_language() == core_i18n._current_lang
    assert gui_i18n.tr("connect") == "اتصال"
