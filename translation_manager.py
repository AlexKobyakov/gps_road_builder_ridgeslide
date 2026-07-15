# -*- coding: utf-8 -*-
"""
Translation Manager for GPS Road Builder
Менеджер переводов (портирован из плагина garmin_export).

Динамически загружает словари из пакета translations/. Новый язык добавляется
файлом translations/<code>.py со словарём `translations` и записью в
LANGUAGE_LABELS.

Author: Кобяков Александр Викторович (Alex Kobyakov)
Email: kobyakov@lesburo.ru
Year: 2026
"""

import importlib

# Языки с письмом справа налево (для setLayoutDirection)
RTL_LANGUAGES = set()

# Отображаемые названия языков (эндоним) в порядке для UI. Флаг рисуется
# ИКОНКОЙ (см. LANGUAGE_FLAGS + gui), а не эмодзи — Windows не рисует
# regional-indicator глифы (ADD4 п.8).
LANGUAGE_LABELS = [
    ('ru', 'Русский'),
    ('en', 'English'),
]

# Код языка → имя файла флага в resources/flags/. Иконку подставляет GUI.
LANGUAGE_FLAGS = {
    'ru': 'ru.svg',
    'en': 'en.svg',
}


class TranslationManager:
    """Менеджер переводов с fallback на язык по умолчанию."""

    def __init__(self):
        self.current_language = 'ru'
        self.fallback_language = 'en'
        self.loaded_languages = {}

        self.supported_languages = [code for code, _ in LANGUAGE_LABELS]

        self._load_language(self.current_language)
        if self.current_language != self.fallback_language:
            self._load_language(self.fallback_language)

    def _load_language(self, language_code):
        """Загрузить словарь языка (динамический импорт translations.<code>)."""
        if language_code in self.loaded_languages:
            return True
        if language_code not in self.supported_languages:
            return False
        try:
            package = __package__ or __name__.rpartition('.')[0]
            module = importlib.import_module(
                '.translations.{0}'.format(language_code), package)
            if hasattr(module, 'translations'):
                self.loaded_languages[language_code] = module.translations
                return True
            print("Warning: translations.{0} has no 'translations' dict"
                  .format(language_code))
            return False
        except ImportError as exc:
            print("Warning: could not load translations for {0}: {1}"
                  .format(language_code, exc))
            return False
        except Exception as exc:
            print("Error loading translations for {0}: {1}"
                  .format(language_code, exc))
            return False

    def get_language_labels(self):
        """Список (код, отображаемое_название) для заполнения UI."""
        return list(LANGUAGE_LABELS)

    def is_rtl(self, language_code=None):
        return (language_code or self.current_language) in RTL_LANGUAGES

    def set_language(self, language_code):
        if language_code in self.supported_languages and \
                self._load_language(language_code):
            self.current_language = language_code
            return True
        return False

    def get_text(self, key, language=None):
        """Перевод по ключу с fallback; если не найден — вернуть сам ключ."""
        lang = language or self.current_language
        if lang in self.loaded_languages and key in self.loaded_languages[lang]:
            return self.loaded_languages[lang][key]
        if self.fallback_language in self.loaded_languages and \
                lang != self.fallback_language:
            fb = self.loaded_languages[self.fallback_language]
            if key in fb:
                return fb[key]
        return key

    def get_current_language(self):
        return self.current_language

    def get_supported_languages(self):
        return self.supported_languages.copy()

    def is_language_loaded(self, language_code):
        return language_code in self.loaded_languages

    def reload_language(self, language_code):
        self.loaded_languages.pop(language_code, None)
        return self._load_language(language_code)


# Глобальный объект переводов
translations = TranslationManager()
