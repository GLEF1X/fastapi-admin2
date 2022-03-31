from gettext import GNUTranslations
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi_admin2.constants import PATH_TO_LOCALES
from fastapi_admin2.i18n.lazy_proxy import LazyProxy
from fastapi_admin2.template import templates


class I18nService:
    def __init__(
            self,
            *,
            path_to_default_translations: Path = PATH_TO_LOCALES,
            path_to_extra_translations: Optional[Path] = None,
            default_locale: str = "en",
            domain: str = "messages",
    ) -> None:
        self.path_to_extra_translations = path_to_extra_translations
        self.default_locale = default_locale
        self.domain = domain
        self._path_to_default_translations = path_to_default_translations
        self.locales = self._find_locales()

        templates.env.install_gettext_callables(self.gettext, self.gettext)

    def reload_locales(self) -> None:
        self.locales = self._find_locales()

    @property
    def available_locales(self) -> Tuple[str, ...]:
        return tuple(self.locales.keys())

    def gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> str:
        if locale is None:
            locale = self.default_locale

        if locale not in self.locales:
            if n == 1:
                return singular
            return plural if plural else singular

        translator = self.locales[locale]

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

        if self.path_to_extra_translations:
            translations.update(**self._parse_translations(self.path_to_extra_translations))
        return translations

    def _get_default_translations(self) -> Dict[str, GNUTranslations]:
        return self._parse_translations(self._path_to_default_translations)

    def _parse_translations(self, path: Path) -> Dict[str, GNUTranslations]:
        translations: Dict[str, GNUTranslations] = {}

        for file in path.iterdir():  # in linux directory is a file
            if not file.is_dir():
                continue
            mo_path = file / "LC_MESSAGES" / (self.domain + ".mo")

            if mo_path.exists():
                with open(mo_path, "rb") as fp:
                    translations[name] = GNUTranslations(fp)  # type: ignore
            elif mo_path.with_suffix(".po"):  # pragma: no cover
                raise RuntimeError(f"Found locale '{file}' but this language is not compiled!")

        return translations
