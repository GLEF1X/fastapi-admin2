from typing import Generic, TypeVar, Type, Optional

from starlette.requests import Request
from starlette.routing import Mount

T = TypeVar("T")


class DependencyResolvingError(Exception):
    pass


class Marker(Generic[T]):
    pass


def get_dependency_from_request_by_marker(request: Request,
                                          marker: Type[Marker[T]]) -> T:
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

    return request.app.dependency_overrides[marker]()
