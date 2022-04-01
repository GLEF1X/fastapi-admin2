from abc import ABC, abstractmethod
from typing import cast, Optional

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fastapi_admin2.i18n.core import I18nService
from fastapi_admin2.i18n.exceptions import UnableToExtractLocaleFromRequestError
from fastapi_admin2.i18n.utils import get_locale_from_request

try:
    from babel import Locale
except ImportError:  # pragma: no cover
    babel_lib_not_installed = True
    Locale = None


class AbstractI18nMiddleware(BaseHTTPMiddleware, ABC):

    def __init__(self, app: ASGIApp, i18n: Optional[I18nService] = None, ) -> None:
        super().__init__(app)

        if i18n is None:
            self.i18n_service = I18nService()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        current_locale = await self.get_locale(request)
        request.state.t = self.i18n_service.gettext
        request.state.current_locale = current_locale

        response = await call_next(request)
        response.set_cookie(key="language", value=current_locale)

        return response

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

    def __init__(self, app: ASGIApp, i18n: Optional[I18nService] = None, ) -> None:
        super().__init__(app, i18n)

        if babel_lib_not_installed:  # pragma: no cover
            raise RuntimeError(
                f"{type(self).__name__} can be used only when Babel installed\n"
                "Just install Babel (`pip install Babel`) "
                "or fastapi-admin2 with i18n support (`pip install fastapi-admin2[i18n]`)"
            )

    async def get_locale(self, request: Request) -> str:
        if babel_lib_not_installed:  # pragma: no cover
            raise RuntimeError(
                f"{type(self).__name__} can be used only when Babel installed\n"
                "Just install Babel (`pip install Babel`) "
                "or fastapi-admin2 with i18n support (`pip install fastapi-admin2[i18n]`)"
            )
        try:
            locale = get_locale_from_request(request)
        except UnableToExtractLocaleFromRequestError:
            return self.i18n_service.default_locale

        parsed_locale = Locale.parse(locale)
        if parsed_locale.language not in self.i18n_service.available_locales:
            return self.i18n_service.default_locale
        return cast(str, parsed_locale.language)

