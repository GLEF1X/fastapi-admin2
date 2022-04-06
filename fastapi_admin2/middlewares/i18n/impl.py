import functools
from abc import ABC, abstractmethod
from typing import cast, Optional, List, Protocol

import pycountry
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fastapi_admin2.exceptions import RequiredThirdPartyLibNotInstalled
from fastapi_admin2.i18n.exceptions import UnableToExtractLocaleFromRequestError
from fastapi_admin2.i18n.translator import Translator, I18nTranslator
from fastapi_admin2.i18n.utils import get_locale_from_request

try:
    from babel import Locale

    babel_lib_installed = True
except ImportError:  # pragma: no cover
    babel_lib_installed = False
    Locale = None


class Language(Protocol):
    alpha_3: str
    name: str
    scope: str
    type: str


class AbstractI18nMiddleware(BaseHTTPMiddleware, ABC):

    def __init__(self, app: ASGIApp,
                 translator: Optional[Translator] = None, ) -> None:
        super().__init__(app)
        self._translator = translator
        if translator is None:
            self._translator = I18nTranslator()

        self._languages = pycountry.languages
        self._lang_iterator = iter(self._languages)  # avoid pycountry lazy loading

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        current_locale = await self.get_locale(request)
        request.state.gettext = functools.partial(self._translator.gettext, locale=current_locale)
        request.state.lazy_gettext = functools.partial(self._translator.lazy_gettext, locale=current_locale)
        request.state.current_locale = current_locale

        request.app.templates.env.globals['gettext'] = request.state.gettext
        request.app.templates.env.globals['current_locale'] = current_locale
        request.app.templates.env.globals['available_languages'] = list(self.iter_founded_locales())

        with self._translator.internationalized(new_locale=current_locale):
            response = await call_next(request)

        response.set_cookie(key="language", value=current_locale, path=request.app.admin_path)
        return response

    def iter_founded_locales(self) -> List[Language]:
        for t in self._translator.available_translations:
            try:
                lang = self._languages.get(alpha_2=t)
            except LookupError:
                continue

            if lang is None:
                continue

            yield lang

    @abstractmethod
    async def get_locale(self, request: Request) -> str:
        """
        Detect current user locale based on request.
        **This method must be defined in child classes**

        :param request:
        :return:
        """


class I18nMiddleware(AbstractI18nMiddleware):
    """
    Simple I18n middleware.
    Chooses language code from the request
    """

    def __init__(self, app: ASGIApp,
                 translator: Optional[Translator] = None, ) -> None:
        super().__init__(app, translator)
        _raise_if_babel_not_installed()

    async def get_locale(self, request: Request) -> str:

        try:
            locale = get_locale_from_request(request)
        except UnableToExtractLocaleFromRequestError:
            return self._translator.default_locale

        parsed_locale = Locale.parse(locale)
        if parsed_locale.language not in self._translator.available_translations:
            return self._translator.default_locale
        return cast(str, parsed_locale.language)


def _raise_if_babel_not_installed() -> None:
    if babel_lib_installed:  # pragma: no cover
        return None

    raise RequiredThirdPartyLibNotInstalled(
        "Babel",
        thing_that_cant_work_without_lib="i18n",
        can_be_installed_with_ext="i18n"
    )
