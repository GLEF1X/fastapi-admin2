from contextlib import contextmanager
from typing import Optional, Generator

from starlette.requests import Request
from starlette.types import ASGIApp

from fastapi_admin.services.i18n import I18nService
from fastapi_admin.services.i18n.lazy_proxy import LazyProxy
from fastapi_admin.services.i18n.middleware import I18nMiddleware
from fastapi_admin.template import templates


class _I18nStub(I18nService):

    @contextmanager
    def context(self) -> Generator["I18nService", None, None]:
        templates.env.install_null_translations()
        token = I18nService.set_current(self)
        try:
            yield self
        finally:
            I18nService.reset_current(token)

    @contextmanager
    def use_locale(self, locale: str = None) -> Generator[None, None, None]:
        ctx_token = self.ctx_locale.set(locale)
        try:
            yield
        finally:
            self.ctx_locale.reset(ctx_token)

    def gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> str:
        return singular

    def lazy_gettext(
            self, singular: str, plural: Optional[str] = None, n: int = 1, locale: Optional[str] = None
    ) -> LazyProxy:
        return LazyProxy(lambda: singular)


class _I18nMiddlewareStub(I18nMiddleware):

    def __init__(self, app: ASGIApp):
        super().__init__(app, _I18nStub())

    async def get_locale(self, request: Request) -> str:
        pass
