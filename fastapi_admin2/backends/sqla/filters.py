from enum import Enum as EnumCLS
from typing import Any, Callable, Dict, Optional, Type

from sqlalchemy import between, false, true, Column, func
from sqlalchemy.sql import Select
from sqlalchemy.sql.operators import ilike_op, like_op, match_op, is_

from fastapi_admin2.backends.sqla.toolings import parse_like_term
from fastapi_admin2.default_settings import DATE_FORMAT_MOMENT
from fastapi_admin2.ui.widgets.filters import BaseSearchFilter, BaseDateRangeFilter, BaseDateTimeRangeFilter, \
    BaseEnumFilter, BaseBooleanFilter, DateRangeDTO

full_text_search_op = match_op


class Search(BaseSearchFilter):

    def __init__(
            self,
            column: Column,
            name: str,
            sqlalchemy_operator: Callable[[Any, Any], Any] = ilike_op,
            full_text_search_config: Optional[Dict[str, Any]] = None,
            placeholder: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(name=name, placeholder=placeholder, null=null, **additional_context)
        self._column = column

        if full_text_search_config is not None and sqlalchemy_operator != full_text_search_op:
            raise Exception(
                "If you wanna to use full-text search, transmit match_op as `sqlalchemy_operator`"
            )

        self._full_text_search_config = full_text_search_config
        self._sqlalchemy_operator = sqlalchemy_operator

    def _apply_to_sql_query(self, query: Select, value: str) -> Select:
        if self._sqlalchemy_operator in {ilike_op, like_op}:
            return query.where(self._sqlalchemy_operator(self._column, value))

        return query.where(self._sqlalchemy_operator(self._column, value))

    def clean(self, value: Any) -> Any:
        if self._sqlalchemy_operator in {ilike_op, like_op}:
            return parse_like_term(value)

        return func.plainto_tsquery(value)


class DateRange(BaseDateRangeFilter):

    def __init__(self, column: Column, name: str,
                 date_format: str = DATE_FORMAT_MOMENT,
                 placeholder: str = "",
                 null: bool = True,
                 **additional_context: Any):
        super().__init__(name, date_format, placeholder, null, **additional_context)
        self._column = column

    def _apply_to_sql_query(self, query: Select, value: DateRangeDTO) -> Select:
        return query.where(between(self._column, value.start, value.end))


class DateTimeRange(BaseDateTimeRangeFilter):
    def __init__(self, column: Column, name: str, date_format: str = DATE_FORMAT_MOMENT, placeholder: str = "",
                 null: bool = True, **additional_context: Any):
        super().__init__(name, date_format, placeholder, null, **additional_context)
        self._column = column

    def _apply_to_sql_query(self, query: Select, value: DateRangeDTO) -> Select:
        return query.where(between(self._column, value.start, value.end))


class Enum(BaseEnumFilter):
    def __init__(
            self,
            column: Column,
            enum: Type[EnumCLS],
            name: str,
            enum_type: Type[Any] = int,
            placeholder: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(enum, name, enum_type, placeholder, null, **additional_context)
        self._column = column

    def _apply_to_sql_query(self, query: Select, value: Any) -> Select:
        return query.where(self._column == value)


class Boolean(BaseBooleanFilter):
    def __init__(
            self,
            column: Column,
            name: str,
            placeholder: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(name, placeholder, null, **additional_context)
        self._column = column

    def clean(self, value: Any) -> Any:
        if not value:
            return false()

        if value == "true":
            return true()

        return false()

    def _apply_to_sql_query(self, query: Select, value: Any) -> Select:
        value = self.clean(value)
        return query.where(is_(self._column, value))
