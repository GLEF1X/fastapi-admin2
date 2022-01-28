from typing import Any, List, Type

from starlette.datastructures import FormData
from starlette.requests import Request
from tortoise import ForeignKeyFieldInstance, ManyToManyFieldInstance
from tortoise import Model as TortoiseModel
from tortoise.fields import BooleanField, DateField, DatetimeField, JSONField
from tortoise.fields.data import CharEnumFieldInstance, IntEnumFieldInstance, IntField, TextField

from fastapi_admin2.dialects.tortoise.widgets.inputs import ManyToMany, ForeignKey
from fastapi_admin2.exceptions import FieldNotFoundError
from fastapi_admin2.resources import Field
from fastapi_admin2.resources.model import AbstractModelResource, Q
from fastapi_admin2.widgets import displays, inputs
from fastapi_admin2.widgets.inputs import DisplayOnly


class Model(AbstractModelResource):
    model: Type[TortoiseModel]

    @classmethod
    async def enrich_select_with_filters(cls, request: Request, model: Any, query: Q) -> Q:
        parsed_query_params = await cls.parse_query_params(request)
        for filter_ in cls._normalize_filters():
            if not parsed_query_params.get(filter_.name):
                continue

            f = await filter_.generate_public_filter(parsed_query_params[filter_.name])
            query = query.filter(**{f.name + f.operator: f.value})

        return query

    @classmethod
    async def resolve_form_data(cls, data: FormData):
        ret = {}
        m2m_ret = {}
        for field in cls.get_model_fields_for_input():
            input_ = field.input
            if input_.context.get("disabled") or isinstance(input_, DisplayOnly):
                continue
            name = input_.context.get("name")
            if isinstance(input_, ManyToMany):
                v = data.getlist(name)
                value = await input_.parse_value(v)
                m2m_ret[name] = await input_.model.filter(pk__in=value)
            else:
                v = data.get(name)
                value = await input_.parse_value(v)
                if value is None:
                    continue
                ret[name] = value
        return ret, m2m_ret

    @classmethod
    def get_model_fields_for_display(cls) -> List[Field]:
        fields: List[Field] = []
        pk_column = cls.model._meta.db_pk_column
        for field in cls.fields or cls.model._meta.fields:
            if isinstance(field, str):
                if field == pk_column:
                    continue
                field = cls._create_field_by_field_name(field)
            if isinstance(field, str):
                field = cls._create_field_by_field_name(field)
            if isinstance(field.display, displays.InputOnly):
                continue
            if (
                    field.name in cls.model._meta.fetch_fields
                    and field.name not in cls.model._meta.fk_fields | cls.model._meta.m2m_fields
            ):
                continue
            fields.append(field)
        fields.insert(0, cls._create_field_by_field_name(pk_column))
        return fields

    @classmethod
    def _create_field_by_field_name(cls, field_name: str) -> Field:
        fields_map = cls.model._meta.fields_map
        field = fields_map.get(field_name)
        if not field:
            raise FieldNotFoundError(f"Can't found field '{field_name}' in model {cls.model}")
        label = field_name
        null = field.null
        placeholder = field.description or ""
        display, input_ = displays.Display(), inputs.Input(
            placeholder=placeholder, null=null, default=field.default
        )
        if field.pk or field.generated:
            display, input_ = displays.Display(), inputs.DisplayOnly()
        elif isinstance(field, BooleanField):
            display, input_ = displays.Boolean(), inputs.Switch(null=null, default=field.default)
        elif isinstance(field, DatetimeField):
            if field.auto_now or field.auto_now_add:
                input_ = inputs.DisplayOnly()
            else:
                input_ = inputs.DateTime(null=null, default=field.default)
            display, input_ = displays.DatetimeDisplay(), input_
        elif isinstance(field, DateField):
            display, input_ = displays.DateDisplay(), inputs.Date(null=null, default=field.default)
        elif isinstance(field, IntEnumFieldInstance):
            display, input_ = displays.Display(), inputs.Enum(
                field.enum_type, null=null, default=field.default
            )
        elif isinstance(field, CharEnumFieldInstance):
            display, input_ = displays.Display(), inputs.Enum(
                field.enum_type, enum_type=str, null=null, default=field.default
            )
        elif isinstance(field, JSONField):
            display, input_ = displays.Json(), inputs.Json(null=null)
        elif isinstance(field, TextField):
            display, input_ = displays.Display(), inputs.TextArea(
                placeholder=placeholder, null=null, default=field.default
            )
        elif isinstance(field, IntField):
            display, input_ = displays.Display(), inputs.Number(
                placeholder=placeholder, null=null, default=field.default
            )
        elif isinstance(field, ForeignKeyFieldInstance):
            display, input_ = displays.Display(), ForeignKey(
                field.related_model, null=null, default=field.default
            )
            field_name = field.source_field
        elif isinstance(field, ManyToManyFieldInstance):
            display, input_ = displays.InputOnly(), ManyToMany(field.related_model)
        return Field(name=field_name, label=label.title(), display=display, input_=input_)
