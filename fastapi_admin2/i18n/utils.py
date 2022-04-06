from starlette.requests import Request

from fastapi_admin2.i18n.exceptions import UnableToExtractLocaleFromRequestError


def get_locale_from_request(request: Request) -> str:
    if locale := request.query_params.get("language"):
        return locale
    if locale := request.cookies.get("language"):
        return locale

    if accept_language := request.headers.get("Accept-Language"):
        return accept_language.split(",")[0].replace("-", "_")

    raise UnableToExtractLocaleFromRequestError()
