import abc
import json
from enum import Enum as EnumCLS
from typing import Any, List, Optional, Tuple, Type, Callable

from starlette.datastructures import UploadFile

from fastapi_admin2 import constants
from fastapi_admin2.utils.files import FileManager
from fastapi_admin2.widgets import Widget


class Input(Widget):
    template = "widgets/inputs/input.html"

    def __init__(
            self, help_text: Optional[str] = None, default: Any = None, null: bool = False, **context
    ):
        super().__init__(null=null, help_text=help_text, **context)
        self.default = default

    async def parse_value(self, value: Any):
        """
        Parse value from frontend

        :param value:
        :return:
        """
        return value

    async def render(self, value: Any) -> str:
        if value is None:
            value = self.default
        return await super().render(value)


class DisplayOnly(Input):
    """
    Only display without input in edit or create
    """


class Text(Input):
    input_type: Optional[str] = "text"

    def __init__(
            self,
            help_text: Optional[str] = None,
            default: Any = None,
            null: bool = False,
            placeholder: str = "",
            disabled: bool = False,
            **context: Any
    ):
        super().__init__(
            null=null,
            default=default,
            input_type=self.input_type,
            placeholder=placeholder,
            disabled=disabled,
            help_text=help_text,
            **context
        )


class Select(Input):
    template = "widgets/inputs/select.html"

    def __init__(
            self,
            help_text: Optional[str] = None,
            default: Any = None,
            null: bool = False,
            disabled: bool = False,
    ):
        super().__init__(help_text=help_text, null=null, default=default, disabled=disabled)

    @abc.abstractmethod
    async def get_options(self) -> List[Tuple[Any, ...]]:
        """
        return list of tuple with display and value

        [("on",1),("off",2)]

        :return: list of tuple with display and value
        """

    async def render(self, value: Any) -> str:
        options = await self.get_options()
        self.context.update(options=options)
        return await super(Select, self).render(value)


class BaseForeignKeyInput(Select, abc.ABC):
    def __init__(
            self,
            model: Any,
            default: Optional[Any] = None,
            null: bool = False,
            disabled: bool = False,
            help_text: Optional[str] = None,
    ):
        super().__init__(help_text=help_text, default=default, null=null, disabled=disabled)
        self.model = model


class BaseManyToManyInput(BaseForeignKeyInput, abc.ABC):
    template = "widgets/inputs/many_to_many.html"


class Enum(Select):
    def __init__(
            self,
            enum: Type[EnumCLS],
            default: Any = None,
            enum_type: Type = int,
            null: bool = False,
            disabled: bool = False,
            help_text: Optional[str] = None,
    ):
        super().__init__(help_text=help_text, default=default, null=null, disabled=disabled)
        self.enum = enum
        self.enum_type = enum_type

    async def parse_value(self, value: Any):
        return self.enum(self.enum_type(value))

    async def get_options(self):
        options = [(v.name, v.value) for v in self.enum]
        if self.context.get("null"):
            options = [("", "")] + options
        return options


class Email(Text):
    input_type = "email"


class Json(Input):
    template = "widgets/inputs/json.html"

    def __init__(
            self,
            help_text: Optional[str] = None,
            null: bool = False,
            options: Optional[dict] = None,
            dumper: Callable[..., Any] = json.dumps
    ):
        """
        options config to jsoneditor, see https://github.com/josdejong/jsoneditor

        :param options:
        """
        super().__init__(null=null, help_text=help_text)
        if not options:
            options = {}
        self.context.update(options=options)
        self._dumper = dumper

    async def render(self, value: Any):
        if value:
            value = self._dumper(value)
        return await super().render(value)


class TextArea(Text):
    template = "widgets/inputs/textarea.html"
    input_type = "textarea"


class Editor(Text):
    template = "widgets/inputs/editor.html"


class DateTime(Text):
    input_type = "datetime"
    template = "widgets/inputs/datetime.html"

    def __init__(
            self,
            help_text: Optional[str] = None,
            default: Any = None,
            null: bool = False,
            placeholder: str = "",
            disabled: bool = False,
    ):
        super().__init__(
            null=null,
            default=default,
            placeholder=placeholder,
            disabled=disabled,
            help_text=help_text,
            enable_time=True
        )


class Date(Text):
    input_type = "date"

    def __init__(
            self,
            help_text: Optional[str] = None,
            default: Any = None,
            null: bool = False,
            placeholder: str = "",
            disabled: bool = False,
            format_: str = constants.DATE_FORMAT_FLATPICKR
    ):
        super().__init__(
            null=null,
            default=default,
            placeholder=placeholder,
            disabled=disabled,
            help_text=help_text,
            enable_time=False,
            format=format_
        )


class File(Input):
    input_type = "file"

    def __init__(
            self,
            upload: FileManager,
            default: Any = None,
            null: bool = False,
            disabled: bool = False,
            help_text: Optional[str] = None,
    ):
        super().__init__(
            null=null,
            default=default,
            input_type=self.input_type,
            disabled=disabled,
            help_text=help_text,
        )
        self.upload = upload

    async def parse_value(self, value: Optional[UploadFile]):
        if value and value.filename:
            return await self.upload.upload(value)
        return None


class Image(File):
    template = "widgets/inputs/image.html"
    input_type = "file"


class Radio(Select):
    template = "widgets/inputs/radio.html"

    def __init__(
            self,
            options: List[Tuple[str, Any]],
            help_text: Optional[str] = None,
            default: Any = None,
            disabled: bool = False,
    ):
        super().__init__(default=default, disabled=disabled, help_text=help_text)
        self.options = options

    async def get_options(self):
        return self.options


class RadioEnum(Enum):
    template = "widgets/inputs/radio.html"


class Switch(Input):
    template = "widgets/inputs/switch.html"

    async def parse_value(self, value: str):
        if value == "on":
            return True
        return False


class Password(Text):
    input_type = "password"


class Number(Text):
    input_type = "number"


class Color(Text):
    template = "widgets/inputs/color.html"
