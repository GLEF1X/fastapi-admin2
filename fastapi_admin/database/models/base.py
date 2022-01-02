import re
from typing import Optional, Type, cast, Any, Dict, Pattern

from sqlalchemy import inspect
from sqlalchemy.orm import registry, has_inherited_table, declared_attr
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.util import ImmutableProperties

mapper_registry = registry()

# Split a string by Uppercase as long as the each word is not all caps already
TABLE_NAME_REGEX: Pattern[str] = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])|(?<=[^A-Z])(?=[A-Z])")


def _make_plural(n: str) -> str:
    return f"{n}s"


class OrmModelBase(metaclass=DeclarativeMeta):
    __abstract__ = True
    __mapper_args__ = {"eager_defaults": True}

    # noinspection PyUnusedLocal
    def __init__(self, *args: Any, **kwargs: Any) -> None:  # __init__ here only for type checking
        for key, value in kwargs.items():
            setattr(self, key, value)

    # these are supplied by the sqlalchemy2-stubs, so may be omitted
    # when they are installed
    registry = mapper_registry
    metadata = mapper_registry.metadata

    @declared_attr
    def __tablename__(self) -> Optional[str]:
        """
        Converts tablename to convention, e.g.:
        OrderItem -> order_items
        Order -> orders
        """
        if has_inherited_table(cast(Type[OrmModelBase], self)):
            return None
        cls_name = cast(Type[OrmModelBase], self).__qualname__
        table_name_parts = re.split(TABLE_NAME_REGEX, cls_name)
        formatted_table_name = "".join(
            table_name_part.lower() + "_" for i, table_name_part in enumerate(table_name_parts)
        )
        last_underscore = formatted_table_name.rfind("_")
        return _make_plural(formatted_table_name[:last_underscore])

    def _get_attributes(self) -> Dict[Any, Any]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def __str__(self) -> str:
        attributes = "|".join(str(v) for k, v in self._get_attributes().items())
        return f"{self.__class__.__qualname__} {attributes}"

    def __repr__(self) -> str:
        table_attrs = cast(ImmutableProperties, inspect(self).attrs)
        primary_keys = " ".join(
            f"{key.name}={table_attrs[key.name].value}"
            for key in inspect(self.__class__).primary_key
        )
        return f"{self.__class__.__qualname__}->{primary_keys}"

    def as_dict(self) -> Dict[Any, Any]:
        return self._get_attributes()
