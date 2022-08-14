from typing import cast, Optional

from starlette.requests import Request
from starlette.types import ASGIApp

from fastapi_admin2.exceptions import RequiredThirdPartyLibNotInstalled
from fastapi_admin2.i18n.exceptions import UnableToExtractLocaleFromRequestError
from fastapi_admin2.i18n.translator import Translator
from fastapi_admin2.i18n.utils import get_locale_from_request
from fastapi_admin2.middlewares.i18n.base import AbstractI18nMiddleware

try:
    from babel import Locale
except ImportError:  # pragma: no cover
    Locale = None


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
    if Locale is not None:  # pragma: no cover
        return

    raise RequiredThirdPartyLibNotInstalled(
        "Babel",
        thing_that_cant_work_without_lib="i18n",
        can_be_installed_with_ext="i18n"
    )
