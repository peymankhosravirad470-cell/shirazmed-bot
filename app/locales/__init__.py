 from importlib import import_module
from typing import Any, Optional

SUPPORTED_LANGUAGES = {
    "fa": "app.locales.fa",
    "en": "app.locales.en",
    "ar": "app.locales.ar",
}

DEFAULT_LANGUAGE = "fa"


def _normalize_lang(lang: Optional[str]) -> str:
    if not lang:
        return DEFAULT_LANGUAGE
    lang = str(lang).strip().lower()
    if lang in SUPPORTED_LANGUAGES:
        return lang
    aliases = {
        "persian": "fa", "farsi": "fa", "english": "en", "arabic": "ar",
        "فارسی": "fa", "انگلیسی": "en", "عربی": "ar",
    }
    return aliases.get(lang, DEFAULT_LANGUAGE)


def _get_language_module(lang: Optional[str]):
    lang = _normalize_lang(lang)
    return import_module(SUPPORTED_LANGUAGES[lang])


def get_msg(lang: Optional[str], key: Optional[str] = None) -> Any:
    module = _get_language_module(lang)
    messages = getattr(module, "MSG", {})
    if key is None:
        return messages
    return messages.get(key, key)


def get_msg_btn(lang: Optional[str], key: Optional[str] = None) -> Any:
    module = _get_language_module(lang)
    buttons = getattr(module, "MSG_BTN", {})
    if key is None:
        return buttons
    return buttons.get(key, key)