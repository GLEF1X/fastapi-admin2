from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER


def to_init_page(request: Request) -> RedirectResponse:
    return RedirectResponse(
        url=request.app.admin_path + "/init",
        status_code=HTTP_303_SEE_OTHER
    )


def to_login_page(request: Request) -> RedirectResponse:
    return RedirectResponse(
        request.app.admin_path + "/login",
        status_code=HTTP_303_SEE_OTHER
    )
