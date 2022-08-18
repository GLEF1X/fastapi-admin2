from typing import Any

from fastapi_admin2.exceptions import RequiredThirdPartyLibNotInstalled

try:
    from babel.support import LazyProxy
except ImportError:  # pragma: no cover

    class LazyProxy:  # type: ignore
        def __init__(self, func: Any, *args: Any, **kwargs: Any) -> None:
            raise RequiredThirdPartyLibNotInstalled(
                lib_name="Babel",
                thing_that_cant_work_without_lib="LazyProxy",
                can_be_installed_with_ext="i18n"
            )
