import gettext
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Dict, Generator, Optional, Tuple

from fastapi_admin2.constants import PATH_TO_LOCALES
from fastapi_admin2.i18n.lazy_proxy import LazyProxy
from fastapi_admin2.i18n._context_mixin import ContextInstanceMixin
from fastapi_admin2.template import templates


class I18nService(ContextInstanceMixin["I18nService"]):
    def __init__(
            self,
            *,
            path_to_default_translations: os.PathLike = PATH_TO_LOCALES,
            path_to_extra_translations: Optional[os.PathLike] = None,
            default_locale: str = "en",
            domain: str = "messages",
    ) -> None:
        self.path_to_extra_translations = path_to_extra_translations
        self.default_locale = default_locale
        self.domain = domain
        self.ctx_locale = ContextVar("fastapi_admin_ctx_locale", default=default_locale)
        self._path_to_default_translations = path_to_default_translations
        self.locales = self.find_locales()

    @property
    def current_locale(self) -> str:
        return self.ctx_locale.get()

    @current_locale.setter
    def current_locale(self, value: str) -> None:
        self.ctx_locale.set(value)

    @contextmanager
    def use_locale(self, locale: str) -> Generator[None, None, None]:
        """
        Create context with specified locale
        """
        ctx_token = self.ctx_locale.set(locale)
        try:
            yield
        finally:
            self.ctx_locale.reset(ctx_token)

    @contextmanager
    def context(self) -> Generator["I18nService", None, None]:
        """
        Use I18n context
        """
        token = self.set_current(self)
        try:
            templates.env.install_gettext_callables(self.gettext, self.gettext)
            yield self
        finally:
            self.reset_current(token)

    def find_locales(self) -> Dict[str, gettext.GNUTranslations]:
        """
        Load all compiled locales from path
        :return: dict with locales
        """
        translations = self._get_default_translations()

        if not self.path_to_extra_translations:
            return translations
        return {**translations, **self._parse_translations(self.path_to_extra_translations)}

    def _get_default_translations(self) -> Dict[str, gettext.GNUTranslations]:
        return self._parse_translations(self._path_to_default_translations)

    def _parse_translations(self, path: os.PathLike) -> Dict[str, gettext.GNUTranslations]:
        translations: Dict[str, gettext.GNUTranslations] = {}

        for name in os.listdir(path):
            if not os.path.isdir(os.path.join(path, name)):
                continue
            mo_path = os.path.join(path, name, "LC_MESSAGES", self.domain + ".mo")

            if os.path.exists(mo_path):
                with open(mo_path, "rb") as fp:
                    translations[name] = gettext.GNUTranslations(fp)  # type: ignore
            elif os.path.exists(mo_path[:-2] + "po"):  # pragma: no cover
                raise RuntimeError(f"Found locale '{name}' but this language is not compiled!")

        return translations

    def reload(self) -> None:
        """
        Hot reload locales
        """
        self.locales = self.find_locales()

    @property
    def available_locales(self) -> Tuple[str, ...]:
        """
        list of loaded locales
        :return:
        """
        return tuple(self.locales.keys())

    def gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> str:
        if locale is None:
            locale = self.current_locale

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
