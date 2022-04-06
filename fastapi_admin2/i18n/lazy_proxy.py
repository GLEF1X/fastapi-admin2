from typing import Any

try:
    from babel.support import LazyProxy
except ImportError:  # pragma: no cover

    class LazyProxy:  # type: ignore
        def __init__(self, func: Any, *args: Any, **kwargs: Any) -> None:
            raise RuntimeError(
                "LazyProxy can be used only when Babel installed\n"
                "Just install Babel (`pip install Babel`) "
                "or fastapi-admin2 with localization support (`pip install fastapi-admin2[localization]`)"
            )
