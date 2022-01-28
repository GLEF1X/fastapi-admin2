import functools
from datetime import date, datetime
from typing import Any, Callable, Dict
from typing import Tuple, Union

import pendulum
from sqlalchemy import Column, between
from sqlalchemy.sql import ClauseElement
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.operators import is_, match_op, ilike_op, eq as equals, like_op

from fastapi_admin2.widgets.filters import BaseSearchFilter, BaseDateRangeFilter, BaseDatetimeRangeFilter, \
    BaseEnumFilter, BaseBooleanFilter, PublicFilter


def between(
        column: Column[Union[date, datetime]],
        date_range: Tuple[pendulum.DateTime, pendulum.DateTime]
) -> BinaryExpression:
    lower_bound = date_range[0]
    upper_bound = date_range[1]
    return between(column, lower_bound, upper_bound)


class Search(BaseSearchFilter):

    def __init__(
            self,
            name: str,
            label: str,
            sqlalchemy_operator: Callable[[Any, Any], ClauseElement] = ilike_op,
            full_text_search_config: Dict[Any, Any] = None,
            **context: Any
    ):
        super().__init__(name, label, **context)
        self._sqlalchemy_operator = sqlalchemy_operator

        if full_text_search_config is not None and sqlalchemy_operator != match_op:
            raise Exception(
                "If you wanna to use full-text search, transmit match_op as `sqlalchemy_operator`"
            )

        if not full_text_search_config:
            full_text_search_config = {}

        self._full_text_search_config = full_text_search_config

    @property
    def operator(self) -> Any:
        return functools.partial(self._sqlalchemy_operator, **self._full_text_search_config)

    async def generate_public_filter(self, value: Any) -> PublicFilter:
        if self._sqlalchemy_operator in {ilike_op, like_op}:
            value = f"%{value}%"

        return PublicFilter(
            name=self.name,
            operator=self.operator,
            value=value
        )


class DateRange(BaseDateRangeFilter):
    operator = between


class DateTimeRange(BaseDatetimeRangeFilter, DateRange):
    pass


class Enum(BaseEnumFilter):
    operator = equals


class Boolean(BaseBooleanFilter):
    operator = is_
