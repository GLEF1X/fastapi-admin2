from abc import ABC, abstractmethod
from typing import cast

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from fastapi_admin2.i18n.core import I18nService
from fastapi_admin2.i18n.utils import get_locale_from_request

try:
    from babel import Locale
except ImportError:  # pragma: no cover
    Locale = None


class AbstractI18nMiddleware(BaseHTTPMiddleware, ABC):
    """
    Abstract I18n middleware.
    """

    def __init__(self, app: ASGIApp, i18n: I18nService = I18nService()) -> None:
        """
        Create an instance of middleware
        :param i18n: instance of I18n
        """
        super().__init__(app)
        self.i18n = i18n

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        current_locale = await self.get_locale(request) or self.i18n.default_locale

        with self.i18n.context(), self.i18n.use_locale(current_locale):
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
        pass


class I18nMiddleware(AbstractI18nMiddleware):
    """
    Simple I18n middleware.
    Chooses language code from the User object received in event
    """

    def __init__(self, app: ASGIApp, i18n: I18nService = I18nService(), ) -> None:
        super().__init__(app, i18n=i18n)

        if Locale is None:  # pragma: no cover
            raise RuntimeError(
                f"{type(self).__name__} can be used only when Babel installed\n"
                "Just install Babel (`pip install Babel`) "
                "or fastapi-admin2 with i18n support (`pip install fastapi-admin2[i18n]`)"
            )

    async def get_locale(self, request: Request) -> str:
        if Locale is None:  # pragma: no cover
            raise RuntimeError(
                f"{type(self).__name__} can be used only when Babel installed\n"
                "Just install Babel (`pip install Babel`) "
                "or fastapi-admin2 with i18n support (`pip install fastapi-admin2[i18n]`)"
            )
        locale = get_locale_from_request(request)
        if locale is None:
            return self.i18n.default_locale

        parsed_locale = Locale.parse(locale)
        if parsed_locale.language not in self.i18n.available_locales:
            return self.i18n.default_locale
        return cast(str, parsed_locale.language)


class ConstI18nMiddleware(AbstractI18nMiddleware):
    """
    Const middleware chooses statically defined locale
    """

    def __init__(self, app: ASGIApp, locale: str, i18n: I18nService = I18nService()) -> None:
        super().__init__(app, i18n=i18n)
        self.locale = locale

    async def get_locale(self, request: Request) -> str:
        return self.locale
