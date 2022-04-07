from sqlalchemy import Column

from fastapi_admin2.ui.resources.model import ColumnToFieldConverter, FieldSpec
from fastapi_admin2.ui.widgets import displays, inputs


class BooleanColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.Boolean(),
            input_=inputs.Switch(null=column.nullable, default=column.default),
        )


class DatetimeColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        if column.default or column.server_default:
            input_ = inputs.DisplayOnly()
        else:
            input_ = inputs.DateTime(null=column.nullable, default=column.server_default)

        return FieldSpec(
            display=displays.DatetimeDisplay(),
            input_=input_
        )


class DateColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.DateDisplay(),
            input_=inputs.Date(null=column.nullable, default=column.default),
        )


class EnumColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.Enum(
                column.type.__class__,
                null=column.nullable,
                default=column.default
            )
        )


class JSONColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        return FieldSpec(
            display=displays.Json(),
            input_=inputs.Json(null=column.nullable)
        )


class StringColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        placeholder = column.description or ""
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.TextArea(
                placeholder=placeholder, null=column.nullable, default=column.default
            )
        )


class IntegerColumnToFieldConverter(ColumnToFieldConverter):
    def _convert_column_to_field_spec(self, column: Column) -> FieldSpec:
        placeholder = column.description or ""
        return FieldSpec(
            display=displays.Display(),
            input_=inputs.Number(
                placeholder=placeholder, null=column.nullable, default=column.default
            )
        )
