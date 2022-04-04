from typing import Any, Literal

from fastapi_admin2.widgets.filters import BaseSearchFilter, BaseDateRangeFilter, \
    BaseEnumFilter, BaseBooleanFilter, Q, BaseDateTimeRangeFilter

SearchMode = Literal[
    "equal", "contains", "icontains", "startswith",
    "istartswith", "endswith", "iendswith", "iexact", "search"
]


class Search(BaseSearchFilter):

    def __init__(
            self,
            name: str,
            search_mode: SearchMode = "equal",
            placeholder: str = "",
            null: bool = True,
            **additional_context: Any
    ) -> None:
        super().__init__(name, placeholder, null, **additional_context)
        self._search_mode = search_mode

    def _apply_to_sql_query(self, query: Q, value: Any) -> Q:
        return query.filter(**{self.name: f"{self.name}__{self._search_mode}"})


class DateRange(BaseDateRangeFilter):
    def _apply_to_sql_query(self, query: Q, value: Any) -> Q:
        return query.filter(**{self.name: f"{self.name}__range"})


class DateTimeRange(BaseDateTimeRangeFilter):
    def _apply_to_sql_query(self, query: Q, value: Any) -> Q:
        return query.filter(**{self.name: f"{self.name}__range"})


class Enum(BaseEnumFilter):
    def _apply_to_sql_query(self, query: Q, value: Any) -> Q:
        return query.filter(**{self.name: value})


class Boolean(BaseBooleanFilter):

    def clean(self, value: Any) -> Any:
        if value == "true":
            return True
        return False

    def _apply_to_sql_query(self, query: Q, value: Any) -> Q:
        return query.filter(**{self.name: value})
