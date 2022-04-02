from typing import Any, List, Type

from starlette.datastructures import FormData
from starlette.requests import Request
from tortoise import Model as TortoiseModel, ForeignKeyFieldInstance, ManyToManyFieldInstance
from tortoise.fields import BooleanField, DatetimeField, DateField, JSONField, TextField, IntField
from tortoise.fields.base import Field as TortoiseField
from tortoise.fields.data import CharEnumFieldInstance, IntEnumFieldInstance

from fastapi_admin2.backends.tortoise.field_converters import BooleanColumnToFieldConverter, \
    DatetimeColumnToFieldConverter, DateColumnToFieldConverter, TextColumnToFieldConverter, \
    IntegerColumnToFieldConverter, JSONColumnToFieldConverter, CharEnumColumnToFieldConverter, \
    IntEnumColumnToFieldConverter, ForeignKeyToFieldConverter, ManyToManyFieldConverter
from fastapi_admin2.backends.tortoise.filters import Search
from fastapi_admin2.backends.tortoise.widgets.inputs import ManyToMany
from fastapi_admin2.resources import Field
from fastapi_admin2.resources.model import AbstractModelResource, Q
from fastapi_admin2.widgets import displays, inputs
from fastapi_admin2.widgets.inputs import DisplayOnly


class Model(AbstractModelResource):
    model: Type[TortoiseModel]
    _default_filter = Search

    def __init__(self):
        super().__init__()
        self._pk_column_name = self.model._meta.db_pk_column
        self._converters = {
            CharEnumFieldInstance: CharEnumColumnToFieldConverter(),
            IntEnumFieldInstance: IntEnumColumnToFieldConverter(),
            ForeignKeyFieldInstance: ForeignKeyToFieldConverter(),
            ManyToManyFieldInstance: ManyToManyFieldConverter(),
            DatetimeField: DatetimeColumnToFieldConverter(),
            BooleanField: BooleanColumnToFieldConverter(),
            IntField: IntegerColumnToFieldConverter(),
            DateField: DateColumnToFieldConverter(),
            TextField: TextColumnToFieldConverter(),
            JSONField: JSONColumnToFieldConverter(),
        }
        self._converters.update(self.converters)

    async def enrich_select_with_filters(self, request: Request, model: Any, query: Q) -> Q:
        parsed_query_params = await self.parse_query_params(request)
        for filter_ in self._normalized_filters:
            if not parsed_query_params.get(filter_.name):
                continue

            f = await filter_.generate_public_filter(parsed_query_params[filter_.name])
            query = query.filter(**{f.name + f.operator: f.value})

        return query

    async def resolve_form_data(self, data: FormData):
        ret = {}
        m2m_ret = {}
        for field in self.input_fields:
            input_ = field.input
            if input_.internationalized.get("disabled") or isinstance(input_, DisplayOnly):
                continue
            name = input_.internationalized.get("name")
            if isinstance(input_, ManyToMany):
                v = data.getlist(name)
                value = await input_.parse(v)
                m2m_ret[name] = await input_.model.filter(pk__in=value)
            else:
                v = data.get(name)
                value = await input_.parse(v)
                if value is None:
                    continue
                ret[name] = value
        return ret, m2m_ret

    def _scaffold_model_fields_for_display(self) -> List[Field]:
        fields: List[Field] = []
        for field in self.fields or self.model._meta.fields:
            if isinstance(field, str):
                if field == self._pk_column_name:
                    continue
                field = self._create_field_by_field_name(field)
            if isinstance(field, str):
                field = self._create_field_by_field_name(field)
            if isinstance(field.display, displays.InputOnly):
                continue
            if (
                    field.name in self.model._meta.fetch_fields
                    and field.name not in self.model._meta.fk_fields | self.model._meta.m2m_fields
            ):
                continue
            fields.append(field)
        fields.insert(0, self._create_field_by_field_name(self._pk_column_name))
        return fields

    def _get_column_by_name(self, name: str) -> Any:
        return self.model._meta.fields_map.get(name)

    def _convert_column_for_which_no_converter_found(self, column: TortoiseField, field_name: str) -> Field:
        placeholder = column.description or ""
        return Field(
            display=displays.Display(),
            input_=inputs.Input(
                placeholder=placeholder, null=column.null, default=column.default
            ),
            name=field_name,
            label=field_name.title()
        )
