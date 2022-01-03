from __future__ import annotations

from typing import Generic, TypeVar, Type, Optional, TYPE_CHECKING

from starlette.requests import Request
from starlette.routing import Mount

if TYPE_CHECKING:
    from fastapi_admin.app import FastAPIAdmin

T = TypeVar("T")


class DependencyResolvingError(Exception):
    pass


class Marker(Generic[T]):
    pass


def get_dependency_from_request_by_marker(request: Request,
                                          marker: Type[Marker[T]]) -> T:
    fastapi_admin_instance = get_fastapi_admin_instance_from_request(request)
    return fastapi_admin_instance.dependency_overrides[marker]()


def get_fastapi_admin_instance_from_request(request: Request) -> FastAPIAdmin:
    from fastapi_admin.app import FastAPIAdmin

    app: Optional[FastAPIAdmin] = None
    if not isinstance(request.app, FastAPIAdmin):
        for route in request.app.router.routes:
            if not isinstance(route, Mount):
                continue
            if not isinstance(route.app, FastAPIAdmin):
                continue
            app = request.app
    else:
        app = request.app

    if app is None:
        raise DependencyResolvingError()
    return app
