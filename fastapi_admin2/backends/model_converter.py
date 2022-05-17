import abc
import inspect
from typing import Any, Callable, Type, no_type_check


@no_type_check
def converts(*args: str) -> Callable:
    def _inner(func: Callable) -> Callable:
        func._converter_for = frozenset(args)
        return func

    return _inner


class BaseModelToFormConverter(abc.ABC):
    _convert_for = None

    def __init__(self) -> None:
        self._converters = {}

        for name in dir(self):
            obj = getattr(self, name)
            if hasattr(obj, "_converter_for"):
                for classname in obj._converter_for:
                    self._converters[classname] = obj

    def get_converter(self, column_type: Type[Any]) -> Callable:
        types = inspect.getmro(column_type)

        # Search by module + name
        for col_type in types:
            type_string = f"{col_type.__module__}.{col_type.__name__}"

            if type_string in self._converters:
                return self._converters[type_string]

        # Search by name
        for col_type in types:
            if col_type.__name__ in self._converters:
                return self._converters[col_type.__name__]

        raise Exception(  # pragma: nocover
            f"Could not find field converter for column {column_type} ({types[0]!r})."
        )

    @abc.abstractmethod
    async def get_form(self, model: Any):
        pass
