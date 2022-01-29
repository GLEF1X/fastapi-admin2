from tortoise import ForeignKeyFieldInstance, ManyToManyFieldInstance
from tortoise.fields import DatetimeField, BooleanField, IntField, DateField, JSONField
from tortoise.fields.base import Field as TortoiseField
from tortoise.fields.data import IntEnumFieldInstance, CharEnumFieldInstance

from fastapi_admin2.backends.tortoise.widgets.inputs import ForeignKey, ManyToMany
from fastapi_admin2.resources.model import ColumnToFieldConverter, FieldSpec
from fastapi_admin2.widgets import displays, inputs


class BooleanColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: BooleanField) -> FieldSpec:
        return FieldSpec(
            display=displays.Boolean(),
            input_=inputs.Switch(null=column.null, default=column.default),
        )


class DatetimeColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: DatetimeField) -> FieldSpec:
        if column.auto_now or column.auto_now_add:
            input_ = inputs.DisplayOnly()
        else:
            input_ = inputs.DateTime(null=column.null, default=column.default)

        return FieldSpec(
            display=displays.DatetimeDisplay(),
            input_=input_
        )


class DateColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: TortoiseField) -> FieldSpec:
        return FieldSpec(
            display=displays.DateDisplay(),
            input_=inputs.Date(null=column.null, default=column.default),
        )


class IntEnumColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: IntEnumFieldInstance) -> FieldSpec:
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.Enum(
                column.enum_type,
                null=column.null,
                default=column.default
            )
        )


class CharEnumColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: CharEnumFieldInstance) -> FieldSpec:
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.Enum(
                column.enum_type,
                null=column.null,
                default=column.default,
                enum_type=str
            )
        )


class JSONColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: TortoiseField) -> FieldSpec:
        return FieldSpec(
            display=displays.Json(),
            input_=inputs.Json(null=column.null)
        )


class TextColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: TortoiseField) -> FieldSpec:
        placeholder = column.description or ""
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.TextArea(
                placeholder=placeholder, null=column.null, default=column.default
            )
        )


class IntegerColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: TortoiseField) -> FieldSpec:
        placeholder = column.description or ""
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.Number(
                placeholder=placeholder, null=column.null, default=column.default
            )
        )


class ForeignKeyToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: ForeignKeyFieldInstance) -> FieldSpec:
        return FieldSpec(
            display=displays.Display(),
            input_=ForeignKey(
                column.related_model, null=column.null, default=column.default
            ),
            field_name=column.source_field
        )


class ManyToManyFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: ManyToManyFieldInstance) -> FieldSpec:
        return FieldSpec(
            display=displays.InputOnly(),
            input_=ManyToMany(column.related_model)
        )
