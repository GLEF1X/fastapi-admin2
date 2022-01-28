import abc
from typing import Type, Any, List, Union, Optional, TypeVar

from starlette.datastructures import FormData
from starlette.requests import Request

from fastapi_admin2.enums import HTTPMethod
from fastapi_admin2.i18n import gettext as _
from fastapi_admin2.resources.action import ToolbarAction, Action
from fastapi_admin2.resources.base import Resource
from fastapi_admin2.resources.field import Field, ComputeField
from fastapi_admin2.widgets import inputs, displays
from fastapi_admin2.widgets.filters import AbstractFilter

Q = TypeVar("Q")


class AbstractModelResource(Resource, abc.ABC):
    model: Type[Any]
    fields: List[Union[str, Field]] = []
    page_size: int = 10
    page_pre_title: Optional[str] = None
    page_title: Optional[str] = None
    filters: List[Union[str, AbstractFilter]] = []

    @property
    @abc.abstractmethod
    def _default_filter(self) -> Type[AbstractFilter]: ...

    @classmethod
    async def render_inputs(cls, obj: Optional[Any] = None) -> List[str]:
        rendered_inputs: List[str] = []

        for field in cls.get_model_fields_for_input():
            input_ = field.input
            if isinstance(input_, inputs.DisplayOnly):
                continue
            if isinstance(input_, inputs.File):
                cls.enctype = "multipart/form-data"
            name = input_.context.get("name")
            rendered_inputs.append(await input_.render(getattr(obj, name, None)))

        return rendered_inputs

    @classmethod
    async def parse_query_params(cls, request: Request) -> dict:
        params = {}
        query_params = request.query_params
        for filter_ in cls._normalize_filters():
            name = filter_.context.get("name")
            try:
                matched_filter_value = query_params[name]
                if matched_filter_value == "":
                    raise KeyError
            except KeyError:
                continue
            params[name] = await filter_.parse_value(matched_filter_value)
        return params

    @classmethod
    @abc.abstractmethod
    async def enrich_select_with_filters(cls, request: Request, model: Any, query: Q) -> Q:
        pass

    @classmethod
    def _normalize_filters(cls) -> List[AbstractFilter]:
        normalized_filters: List[AbstractFilter] = []
        for filter_ in cls.filters:
            if isinstance(filter_, str):
                filter_ = cls._default_filter(name=filter_, label=filter_.title())
            normalized_filters.append(filter_)
        return normalized_filters

    @classmethod
    async def render_filters(cls, values: Optional[dict] = None) -> List[str]:
        if not values:
            values = {}
        rendered_filters: List[str] = []
        for filter_ in cls.filters:
            if isinstance(filter_, str):  # denotes that filter is a column name
                filter_ = cls._default_filter(name=filter_, label=filter_.title())

            value = values.get(filter_.name)
            rendered_filters.append(await filter_.render(value))
        return rendered_filters

    @classmethod
    @abc.abstractmethod
    async def resolve_form_data(cls, data: FormData):
        pass

    @classmethod
    def get_field_names(cls, display: bool = True) -> List[str]:
        return cls._get_fields_attr("name", display)

    @classmethod
    def get_model_fields_for_input(cls) -> List[Field]:
        display_fields = cls.get_model_fields_for_display()
        return [
            field for field in display_fields
            if not isinstance(field, ComputeField) and not isinstance(field.display, inputs.DisplayOnly)
        ]

    @classmethod
    @abc.abstractmethod
    def get_model_fields_for_display(cls) -> List[Field]:
        pass

    @classmethod
    def get_field_labels(cls, display: bool = True) -> List[str]:
        return cls._get_fields_attr("label", display)

    @classmethod
    def _get_fields_attr(cls, attr: str, display: bool = True) -> List[Any]:
        some_field_attribute_values = []
        for field in cls.get_model_fields_for_display():
            if display and isinstance(field.display, displays.InputOnly):
                continue
            some_field_attribute_values.append(getattr(field, attr))
        return some_field_attribute_values

    async def get_toolbar_actions(self, request: Request) -> List[ToolbarAction]:
        return [
            ToolbarAction(
                label=_("create"),
                icon="fas fa-plus",
                name="create",
                method=HTTPMethod.GET,
                ajax=False,
                class_="btn-dark",
            )
        ]

    async def row_attributes(self, request: Request, obj: Any) -> dict:
        return {}

    async def column_attributes(self, request: Request, field: Field) -> dict:
        return {}

    async def cell_attributes(self, request: Request, obj: Any, field: Field) -> dict:
        return {}

    async def get_actions(self, request: Request) -> List[Action]:
        return [
            Action(
                label=_("update"),
                icon="ti ti-edit",
                name="update",
                method=HTTPMethod.GET,
                ajax=False
            ),
            Action(
                label=_("delete"),
                icon="ti ti-trash",
                name="delete",
                method=HTTPMethod.DELETE
            ),
        ]

    async def get_bulk_actions(self, request: Request) -> List[Action]:
        return [
            Action(
                label=_("delete_selected"),
                icon="ti ti-trash",
                name="delete",
                method=HTTPMethod.DELETE,
            ),
        ]
