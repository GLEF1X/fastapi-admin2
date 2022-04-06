import abc
import contextlib
from dataclasses import dataclass
from gettext import GNUTranslations
from pathlib import Path
from typing import Dict, Optional, ContextManager, Set

from fastapi_admin2.default_settings import PATH_TO_LOCALES
from fastapi_admin2.localization.lazy_proxy import LazyProxy


@dataclass(frozen=True, slots=True)
class Language:
    name: str
    flag: str
    code: str


class Translator(abc.ABC):
    @abc.abstractmethod
    def gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> str:
        pass

    @abc.abstractmethod
    def lazy_gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> LazyProxy:
        pass

    @property
    @abc.abstractmethod
    def available_translations(self) -> Set[str]:
        pass

    @abc.abstractmethod
    def reload_locales(self) -> None:
        pass

    @property
    @abc.abstractmethod
    def default_locale(self) -> str:
        pass

    @abc.abstractmethod
    def internationalized(self, new_locale: str) -> ContextManager[None]:
        pass


class I18nTranslator(Translator):
    def __init__(
            self,
            *,
            path_to_default_translations: Path = PATH_TO_LOCALES,
            path_to_extra_translations: Optional[Path] = None,
            default_locale: str = "en",
            domain: str = "messages",
    ) -> None:
        self._path_to_extra_translations = path_to_extra_translations
        self._default_locale = default_locale
        self._domain = domain
        self._path_to_default_translations = path_to_default_translations
        self._locales = self._find_locales()
        self._current_locale = self._default_locale

    def reload_locales(self) -> None:
        self._locales = self._find_locales()

    @property
    def default_locale(self) -> str:
        return self._default_locale

    @property
    def available_translations(self) -> Set[str]:
        return set(self._locales.keys())

    @contextlib.contextmanager
    def internationalized(self, new_locale: str) -> ContextManager[None]:
        previous_locale = self._current_locale
        try:
            self._current_locale = new_locale
            yield
        finally:
            self._current_locale = previous_locale

    def gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> str:
        locale = self._current_locale

        if locale not in self._locales:
            if n == 1:
                return singular
            return plural if plural else singular

        translator = self._locales[locale]

        if plural is None:
            return translator.gettext(singular)
        return translator.ngettext(singular, plural, n)

    def lazy_gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> LazyProxy:
        return LazyProxy(self.gettext, singular=singular, plural=plural, n=n, locale=locale)

    def _find_locales(self) -> Dict[str, GNUTranslations]:
        """
        Load all compiled locales from path

        :return: dict with locales
        """
        translations = self._get_default_translations()

        if self._path_to_extra_translations:
            translations.update(**self._parse_translations(self._path_to_extra_translations))
        return translations

    def _get_default_translations(self) -> Dict[str, GNUTranslations]:
        return self._parse_translations(self._path_to_default_translations)

    def _parse_translations(self, path: Path) -> Dict[str, GNUTranslations]:
        translations: Dict[str, GNUTranslations] = {}

        for file in path.iterdir():  # in linux directory is a file
            if not file.is_dir():
                continue
            compiled_translation = file / "LC_MESSAGES" / (self._domain + ".mo")

            if compiled_translation.exists():
                with open(compiled_translation, "rb") as fp:
                    translations[file.stem] = GNUTranslations(fp)
            elif compiled_translation.with_suffix(".po"):  # pragma: no cover
                raise RuntimeError(f"Found locale '{file}' but this language is not compiled!")

        return translations
