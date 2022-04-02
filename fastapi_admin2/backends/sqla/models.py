import logging
import re
from datetime import datetime
from typing import cast, Any, Dict, Pattern, Final

from sqlalchemy import Identity, VARCHAR, BIGINT
from sqlalchemy import inspect, Column, TIMESTAMP, func
from sqlalchemy.orm import registry
from sqlalchemy.orm.decl_api import DeclarativeMeta, declarative_mixin
from sqlalchemy.util import ImmutableProperties

mapper_registry = registry()

TABLE_NAME_REGEX: Pattern[str] = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])|(?<=[^A-Z])(?=[A-Z])")
PLURAL: Final[str] = "s"

logger = logging.getLogger(__name__)


class Base(metaclass=DeclarativeMeta):
    __abstract__ = True
    __mapper_args__ = {"eager_defaults": True}

    # noinspection PyUnusedLocal
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    registry = mapper_registry
    metadata = mapper_registry.metadata

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


@declarative_mixin
class TimeStampMixin:
    __abstract__ = True

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: datetime = Column(
        TIMESTAMP(timezone=True), server_onupdate=func.now(), server_default=func.now()
    )


class SqlalchemyAdminModel(Base):
    __abstract__ = True

    id = Column(BIGINT(), Identity(always=True, cache=10), primary_key=True)
    username = Column(VARCHAR(50), unique=True)
    password = Column(VARCHAR(200), nullable=False)
    profile_pic = Column(VARCHAR(200), nullable=True)
