from typing import Any

from fastapi_admin2.i18n.core import I18nService
from fastapi_admin2.i18n.lazy_proxy import LazyProxy


def get_i18n() -> I18nService:
    i18n = I18nService.get_current(no_error=True)
    if i18n is None:
        raise LookupError("I18n context is not set")
    return i18n


def gettext(*args: Any, **kwargs: Any) -> str:
    return get_i18n().gettext(*args, **kwargs)


def lazy_gettext(*args: Any, **kwargs: Any) -> LazyProxy:
    return LazyProxy(gettext, *args, **kwargs)


ngettext = gettext
lazy_ngettext = lazy_gettext
