import abc
import asyncio
from dataclasses import dataclass
from typing import Type, Any, List, Union, Optional, TypeVar, Dict, Sequence, Hashable, Generic, Iterable

from starlette.datastructures import FormData
from starlette.requests import Request

from fastapi_admin2.enums import HTTPMethod
from fastapi_admin2.exceptions import FieldNotFoundError
from fastapi_admin2.resources.action import ToolbarAction, Action
from fastapi_admin2.resources.base import Resource
from fastapi_admin2.resources.field import Field, ComputedField
from fastapi_admin2.widgets import inputs, displays
from fastapi_admin2.widgets.displays import Display
from fastapi_admin2.widgets.filters import AbstractFilter
from fastapi_admin2.widgets.inputs import Input

Q = TypeVar("Q", bound=Any)
T = TypeVar("T")


@dataclass
class RenderedFields:
    rows: List[List[Any]]  # TODO rename to human-readable
    row_attributes: Iterable[dict]
    column_css_attributes: Iterable[dict]
    cell_css_attributes: Iterable[Iterable[dict]]


class ColumnToFieldConverter(abc.ABC, Generic[T]):

    def convert(self, column: T, field_name: str) -> Field:
        field_spec = self._convert_column_to_field_spec(column)
        return Field(
            name=field_spec.field_name or field_name,
            label=field_name.title(),
            display=field_spec.display,
            input_=field_spec.input_
        )

    @abc.abstractmethod
    def _convert_column_to_field_spec(self, column: T) -> "FieldSpec":
        pass


@dataclass
class FieldSpec:
    input_: Input
    display: Display
    field_name: Optional[str] = None


class AbstractModelResource(Resource, abc.ABC):
    model: Type[Any]
    fields: Sequence[Union[str, Field]] = ()
    page_pre_title: Optional[str] = None
    page_title: Optional[str] = None
    filters: Sequence[Union[str, AbstractFilter]] = ()

    # for jinja templates(established in runtime in AbstractModelResource.from_http_request method)
    toolbar_actions: Sequence[Action]
    actions: List[Action]
    bulk_actions: List[Action]

    show_pk: bool = True

    # Must be overwritten in subclasses
    _default_filter: Type[AbstractFilter]

    converters: Dict[Hashable, ColumnToFieldConverter[Any]] = {}

    paginator: Any = object()

    def __init__(self) -> None:
        self._converters: Dict[Hashable, ColumnToFieldConverter[Any]] = {}

        self._normalized_filters = self._scaffold_filters()
        self.input_fields = self._scaffold_model_fields_for_input()
        self.display_fields = self._scaffold_model_fields_for_display()
        self._field_names = self.get_field_names()

    def __init_subclass__(cls, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "_default_filter"):
            raise NotImplementedError(
                "`_default_filter` must be specified in subclasses of AbstractModelResource"
            )

    @classmethod
    async def from_http_request(cls, request: Request) -> "AbstractModelResource":
        model_resource = cls()

        actions, bulk_actions, toolbar_actions = await asyncio.gather(
            model_resource.get_actions(request),
            model_resource.get_bulk_actions(request),
            model_resource.get_toolbar_actions(request)
        )

        # set attributes for jinja templates
        model_resource.toolbar_actions = toolbar_actions
        model_resource.actions = actions
        model_resource.bulk_actions = bulk_actions

        return model_resource

    async def render_fields(self, orm_models: Sequence[Any], request: Request) -> RenderedFields:
        result = await asyncio.gather(
            self._assemble_rows_list(orm_models, request),
            self._generate_css_attributes_for_rows(orm_models, request),
            self._generate_css_attributes_for_columns(request),
            self._generate_css_for_cells(orm_models, request)
        )
        return RenderedFields(*result)

    async def _generate_css_attributes_for_columns(self, request: Request) -> Iterable[Dict[Any, Any]]:
        return await asyncio.gather(*[
            self.generate_column_css_attributes(request, field)
            for field in self.display_fields
        ])

    async def _generate_css_attributes_for_rows(self, values: Sequence[Any],
                                                request: Request) -> Iterable[Dict[Any, Any]]:
        return await asyncio.gather(*[
            self.generate_row_attributes(request, orm_model_instance)
            for orm_model_instance in values
        ])

    async def _generate_css_for_cells(self, values: Sequence[Any], request: Request) -> List[List[dict]]:
        result = []
        for orm_model_instance in values:
            cell_css_attributes = []
            for field in self.display_fields:
                cell_css_attributes.append(
                    await self.generate_cell_css_attributes(request, orm_model_instance, field))
            result.append(cell_css_attributes)
        return result

    async def _assemble_rows_list(self, orm_models: Sequence[Any], request: Request) -> List[List[str]]:
        result = []
        for orm_model_instance in orm_models:
            row = []
            for field in self.display_fields:
                if isinstance(field, ComputedField):
                    field_value = await field.get_value(request, orm_model_instance)
                else:
                    field_value = getattr(orm_model_instance, field.name, None)

                row.append(await field.display.render(request, field_value))

            result.append(row)
        return result

    async def render_inputs(self, request: Request, obj: Optional[Any] = None) -> List[str]:
        rendered_inputs: List[str] = []

        for field in self.input_fields:
            input_ = field.input
            if isinstance(input_, inputs.DisplayOnly):
                continue
            if isinstance(input_, inputs.File):
                self.enctype = "multipart/form-data"
            name = input_.context.get("name")
            rendered_inputs.append(await input_.render(request, getattr(obj, name, None)))

        return rendered_inputs

    async def render_filters(self, request: Request) -> List[str]:
        rendered_filters: List[str] = []
        for filter_ in self._normalized_filters:
            if isinstance(filter_, str):  # denotes that filter is a column name
                filter_ = self._default_filter(name=filter_, label=filter_.title())
            rendered_filters.append(await filter_.render(request))
        return rendered_filters

    def get_field_labels(self, display: bool = True) -> List[str]:
        return self._get_fields_attr("label", display)

    def get_field_names(self, display: bool = True) -> List[str]:
        return self._get_fields_attr("name", display)

    def _get_fields_attr(self, attr: str, display: bool = True) -> List[Any]:
        some_field_attribute_values = []
        for field in self._scaffold_model_fields_for_display():
            if display and isinstance(field.display, displays.InputOnly):
                continue
            some_field_attribute_values.append(getattr(field, attr))
        return some_field_attribute_values

    async def generate_row_attributes(self, request: Request, obj: Any) -> Dict[str, Any]:
        return {}

    async def generate_column_css_attributes(self, request: Request, field: Field) -> Dict[str, Any]:
        return {}

    async def generate_cell_css_attributes(self, request: Request, obj: Any, field: Field) -> Dict[str, Any]:
        return {}

    async def get_toolbar_actions(self, request: Request) -> List[ToolbarAction]:
        return [
            ToolbarAction(
                label=request.state.gettext("create"),
                icon="fas fa-plus",
                name="create",
                method=HTTPMethod.GET,
                ajax=False,
                class_="btn-dark",
            )
        ]

    async def get_actions(self, request: Request) -> List[Action]:
        return [
            Action(
                label=request.state.gettext("update"),
                icon="ti ti-edit",
                name="update",
                method=HTTPMethod.GET,
                ajax=False
            ),
            Action(
                label=request.state.gettext("delete"),
                icon="ti ti-trash",
                name="delete",
                method=HTTPMethod.DELETE
            ),
        ]

    async def get_bulk_actions(self, request: Request) -> List[Action]:
        return [
            Action(
                label=request.state.gettext("delete_selected"),
                icon="ti ti-trash",
                name="delete",
                method=HTTPMethod.DELETE,
            ),
        ]

    def _create_field_by_field_name(self, field_name: str) -> Field:
        """
        Create field if you have passed on string to fields
        and rely only on built-in recognition of field type

        for instance:
        >>> class MyModelResource(AbstractModelResource):
        >>>     model = SomeModel
        >>>     fields = ["id", "json_column", "some_column"]

        In this case, fields would be transformed to appropriate field inputs and displays automaticly

        :param field_name:
        :return:
        """
        column = self._get_column_by_name(field_name)
        if not column:
            raise FieldNotFoundError(f"Can't found field '{field_name}' in model {self.model}")


        try:
            converter = self._converters[column]
        except KeyError:
            return self._convert_column_for_which_no_converter_found(column, field_name)

        return converter.convert(column, field_name)

    @abc.abstractmethod
    def _get_column_by_name(self, name: str) -> Any:
        pass

    @abc.abstractmethod
    def _convert_column_for_which_no_converter_found(self, column: Any, field_name: str) -> Field:
        pass

    @abc.abstractmethod
    async def enrich_select_with_filters(self, request: Request, model: Any, query: Q) -> Q:
        pass

    @abc.abstractmethod
    async def resolve_form_data(self, data: FormData):
        pass

    def _scaffold_model_fields_for_input(self) -> List[Field]:
        fields_for_display = self._scaffold_model_fields_for_display()
        return [
            f for f in fields_for_display
            if not isinstance(f, ComputedField) and not isinstance(f.display, inputs.DisplayOnly)
        ]

    @abc.abstractmethod
    def _scaffold_model_fields_for_display(self) -> List[Field]:
        pass

    def _scaffold_filters(self) -> Sequence[AbstractFilter]:
        """
        Iterate filters and convert string filters(by default it means searching by some column with operator ilike)
        to _default_filter(which should be set in ORM dialect)

        :return:
        """
        filters: List[AbstractFilter] = []
        for filter_ in self.filters:
            if isinstance(filter_, str):
                filter_ = self._default_filter(name=filter_, label=filter_.title())
            filters.append(filter_)
        return filters
