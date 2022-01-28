import abc
from dataclasses import dataclass
from enum import Enum as EnumCLS
from typing import Any, List, Optional, Tuple, Type

import pendulum

from fastapi_admin2 import constants
from fastapi_admin2.i18n.context import lazy_gettext as _
from fastapi_admin2.widgets.inputs import Input


@dataclass
class PublicFilter:
    name: str
    operator: Any
    value: Any


class AbstractFilter(Input, abc.ABC):

    def __init__(self, name: str, label: str, placeholder: str = "", null: bool = True,
                 **context: Any) -> None:
        """
        Parent class for all filters
        :param name: model field name
        :param label:
        """
        super().__init__(name=name, label=label, placeholder=placeholder, null=null, **context)

    async def generate_public_filter(self, value: Any) -> PublicFilter:
        return PublicFilter(
            name=self.context.get("name"),
            operator=self.operator,
            value=value
        )

    @property
    @abc.abstractmethod
    def operator(self) -> Any: ...

    @property
    def name(self) -> str:
        return self.context["name"]


class BaseSearchFilter(AbstractFilter, abc.ABC):
    template = "widgets/filters/search.html"


class BaseDateRangeFilter(AbstractFilter, abc.ABC):
    def __init__(
            self,
            name: str,
            label: str,
            format_: str = constants.DATE_FORMAT_MOMENT,
            null: bool = True,
            placeholder: str = ""
    ):
        super().__init__(
            name=name,
            label=label,
            format=format_,
            null=null,
            placeholder=placeholder
        )
        self.context.update(date=True)

    async def parse_value(self, value: Optional[str]):
        if value:
            ranges = value.split(" - ")
            return pendulum.parse(ranges[0]), pendulum.parse(ranges[1])

    async def render(self, value: Tuple[pendulum.DateTime, pendulum.DateTime]):
        format_ = self.context.get("format")
        if value is not None:
            value = value[0].format(format_) + " - " + value[1].format(format_)
        return await super().render(value)


class BaseDatetimeRangeFilter(BaseDateRangeFilter, abc.ABC):
    template = "widgets/filters/datetime.html"

    def __init__(
            self,
            name: str,
            label: str,
            format_: str = constants.DATETIME_FORMAT_MOMENT,
            null: bool = True,
            placeholder: str = "",
    ):
        super().__init__(name, label, null=null, format_=format_, placeholder=placeholder, )
        self.context.update(date=False)


class BaseSelectFilter(AbstractFilter):
    template = "widgets/filters/select.html"

    def __init__(self, name: str, label: str, null: bool = True):
        super().__init__(name, label, null=null)

    @abc.abstractmethod
    async def get_options(self):
        """
        return list of tuple with display and value

        [("on",1),("off",2)]

        :return: list of tuple with display and value
        """

    async def render(self, value: Any):
        options = await self.get_options()
        self.context.update(options=options)
        return await super().render(value)


class BaseEnumFilter(BaseSelectFilter, abc.ABC):
    def __init__(
            self,
            enum: Type[EnumCLS],
            name: str,
            label: str,
            enum_type: Type = int,
            null: bool = True,
    ):
        super().__init__(name=name, label=label, null=null)
        self.enum = enum
        self.enum_type = enum_type

    async def parse_value(self, value: Any):
        return self.enum(self.enum_type(value))

    async def get_options(self):
        options = [(v.name, v.value) for v in self.enum]
        if self.context.get("null"):
            options = [("", "")] + options
        return options


class BaseBooleanFilter(BaseSelectFilter, abc.ABC):

    async def get_options(self) -> List[Tuple[str, str]]:
        """Return list of possible values to select from."""
        options = [
            (_("TRUE"), "true"),
            (_("FALSE"), "false"),
        ]
        if self.context.get("null"):
            options.insert(0, ("", ""))

        return options
