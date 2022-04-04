from enum import Enum as EnumCLS
from typing import Any, Callable, Dict, Optional, Type

from sqlalchemy import between, false, true, Column
from sqlalchemy.sql import Select
from sqlalchemy.sql.operators import ilike_op, like_op, match_op, is_

from fastapi_admin2.backends.sqla.toolings import parse_like_term
from fastapi_admin2.constants import DATE_FORMAT_MOMENT
from fastapi_admin2.widgets.filters import BaseSearchFilter, BaseDateRangeFilter, BaseDateTimeRangeFilter, \
    BaseEnumFilter, BaseBooleanFilter

full_text_search_op = match_op


class Search(BaseSearchFilter):

    def __init__(
            self,
            column: Column,
            name: str,
            sqlalchemy_operator: Callable[[Any, Any], Any] = ilike_op,
            full_text_search_config: Optional[Dict[str, Any]] = None,
            placeholder: str = "",
            help_text: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(name=name, placeholder=placeholder, help_text=help_text, null=null,
                         **additional_context)
        self._column = column

        if full_text_search_config is not None and sqlalchemy_operator != full_text_search_op:
            raise Exception(
                "If you wanna to use full-text search, transmit match_op as `sqlalchemy_operator`"
            )

        self._full_text_search_config = full_text_search_config
        self._sqlalchemy_operator = sqlalchemy_operator

    def apply_to_sql_query(self, query: Select, value: str) -> Select:
        value = self.parse_input(value)
        if self._sqlalchemy_operator in {ilike_op, like_op}:
            return query.where(self._sqlalchemy_operator(self._column, value))

        return query.where(self._sqlalchemy_operator(self._column, value))

    def parse_input(self, value: Any) -> Any:
        if self._sqlalchemy_operator in {ilike_op, like_op}:
            return parse_like_term(value)

        return value


class DateRange(BaseDateRangeFilter):

    def __init__(self, column: Column, name: str,
                 date_format: str = DATE_FORMAT_MOMENT,
                 placeholder: str = "",
                 help_text: str = "",
                 null: bool = True,
                 **additional_context: Any):
        super().__init__(name, date_format, placeholder, help_text, null, **additional_context)
        self._column = column

    def apply_to_sql_query(self, query: Select, value: Any) -> Select:
        date_range = self.clean(value)
        return query.where(between(self._column, date_range.start, date_range.end))


class DateTimeRange(BaseDateTimeRangeFilter, DateRange):
    def __init__(self, column: Column, name: str, date_format: str = DATE_FORMAT_MOMENT, placeholder: str = "",
                 help_text: str = "", null: bool = True, **additional_context: Any):
        super().__init__(name, date_format, placeholder, help_text, null, **additional_context)
        self._column = column

    def apply_to_sql_query(self, query: Select, value: Any) -> Select:
        date_range = self.clean(value)
        return query.where(between(self._column, date_range.start, date_range.end))


class Enum(BaseEnumFilter):
    def __init__(
            self,
            column: Column,
            enum: Type[EnumCLS],
            name: str,
            enum_type: Type[Any] = int,
            placeholder: str = "",
            help_text: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(enum, name, enum_type, placeholder, help_text, null, **additional_context)
        self._column = column

    def apply_to_sql_query(self, query: Select, value: Any) -> Select:
        return query.where(self._column == value)


class Boolean(BaseBooleanFilter):
    def __init__(
            self,
            column: Column,
            name: str,
            placeholder: str = "",
            help_text: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(name, placeholder, help_text, null, **additional_context)
        self._column = column

    def clean(self, value: Any) -> Any:
        if not value:
            return false()

        if value == "true":
            return true()

        return false()

    def apply_to_sql_query(self, query: Select, value: Any) -> Select:
        value = self.clean(value)
        return query.where(is_(self._column, value))
