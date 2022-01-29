from typing import Any, Literal

from fastapi_admin2.widgets.filters import BaseSearchFilter, BaseDatetimeRangeFilter, BaseDateRangeFilter, \
    BaseEnumFilter, BaseBooleanFilter

SearchMode = Literal[
    "equal", "contains", "icontains", "startswith",
    "istartswith", "endswith", "iendswith", "iexact", "search"
]

TORTOISE_EQUAL_OP = ""


class Search(BaseSearchFilter):

    def __init__(self, name: str, label: str, search_mode: SearchMode = "equal", **context: Any):
        """

        :param name:
        :param label:
        :param search_mode: equal,contains,icontains,startswith,istartswith,endswith,iendswith,iexact,search
        :param context:
        """
        super().__init__(name, label, **context)
        if search_mode == "equal":
            self._search_mode = ""
        else:
            self._search_mode = search_mode

    @property
    def operator(self) -> Any:
        return self._search_mode


class DateRange(BaseDateRangeFilter):
    operator = TORTOISE_EQUAL_OP


class DateTimeRange(BaseDatetimeRangeFilter, DateRange):
    pass


class Enum(BaseEnumFilter):
    operator = TORTOISE_EQUAL_OP


class Boolean(BaseBooleanFilter):
    operator = TORTOISE_EQUAL_OP
