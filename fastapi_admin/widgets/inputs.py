import abc
import json
from enum import Enum as EnumCLS
from typing import Any, List, Optional, Tuple, Type, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile
from starlette.requests import Request

from fastapi_admin import constants
from fastapi_admin.utils.file_upload import FileUploader
from fastapi_admin.general_dependencies import SessionMakerDependencyMarker
from fastapi_admin.utils.depends import get_dependency_from_request_by_marker
from fastapi_admin.utils.sqlalchemy import get_primary_key, get_related_querier_from_model_by_foreign_key
from fastapi_admin.widgets import Widget


class Input(Widget):
    template = "widgets/inputs/input.html"

    def __init__(
            self, help_text: Optional[str] = None, default: Any = None, null: bool = False, **context
    ):
        super().__init__(null=null, help_text=help_text, **context)
        self.default = default

    async def parse_value(self, request: Request, value: Any):
        """
        Parse value from frontend
        :param request:
        :param value:
        :return:
        """
        return value

    async def render(self, request: Request, value: Any) -> str:
        if value is None:
            value = self.default
        return await super(Input, self).render(request, value)


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
    async def get_options(self):
        """
        return list of tuple with display and value

        [("on",1),("off",2)]

        :return: list of tuple with display and value
        """

    async def render(self, request: Request, value: Any):
        options = await self.get_options()
        self.context.update(options=options)
        return await super(Select, self).render(request, value)


class ForeignKey(Input):
    template = "widgets/inputs/select.html"

    def __init__(
            self,
            to_column: Any,
            default: Any = None,
            null: bool = False,
            disabled: bool = False,
            help_text: Optional[str] = None,
    ):
        super().__init__(help_text=help_text, default=default, null=null, disabled=disabled)
        self.querier = get_related_querier_from_model_by_foreign_key(to_column)
        self._pk = get_primary_key(self.querier)

    async def render(self, request: Request, value: Any):
        session_pool = get_dependency_from_request_by_marker(request, SessionMakerDependencyMarker)
        async with session_pool.begin() as session:  # type: AsyncSession
            results = (await session.execute(select(self.querier))).scalars().all()
            options = [(str(model), getattr(model, self._pk)) for model in results]
        self.context.update(options=options)
        return await super().render(request, value)


class ManyToMany(Input):
    template = "widgets/inputs/many_to_many.html"

    def __init__(
            self,
            model: Type[Any],
            disabled: bool = False,
            help_text: Optional[str] = None,
    ):
        super().__init__(help_text=help_text, disabled=disabled)
        self.model = model

    async def get_options(self):
        ret = await self.get_queryset()
        options = [dict(label=str(x), value=x.pk) for x in ret]
        return options

    async def get_queryset(self):
        return await self.model.all()

    async def render(self, request: Request, value: Any):
        options = await self.get_options()
        selected = list(map(lambda x: x.pk, value.related_objects if value else []))
        for option in options:
            if option.get("value") in selected:
                option["selected"] = True
        self.context.update(options=json.dumps(options))
        return await super(Input, self).render(request, value)


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

    async def parse_value(self, request: Request, value: Any):
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

    async def render(self, request: Request, value: Any):
        if value:
            value = self._dumper(value)
        return await super().render(request, value)


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
            upload: FileUploader,
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

    async def parse_value(self, request: Request, value: Optional[UploadFile]):
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

    async def parse_value(self, request: Request, value: str):
        if value == "on":
            return True
        return False


class Password(Text):
    input_type = "password"


class Number(Text):
    input_type = "number"


class Color(Text):
    template = "widgets/inputs/color.html"
