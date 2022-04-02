import inspect
from typing import Type, cast, Optional, Union, Callable

from fastapi import Form
from pydantic import BaseModel


class FormBaseModel(BaseModel):

    @classmethod
    def as_form(cls) -> BaseModel:
        """Generated in as_form function"""


def as_form(maybe_cls: Optional[Type[BaseModel]] = None) -> Union[
    Type[FormBaseModel], Callable[[Type[BaseModel]], Type[FormBaseModel]]
]:
    def wrap(cls):
        return _transform_to_form(cls)

    if maybe_cls is None:
        return wrap

    return _transform_to_form(maybe_cls)


def _transform_to_form(cls: Type[BaseModel]) -> Type[FormBaseModel]:
    new_parameters = []

    for field_name, model_field in cls.__fields__.items():
        model_field: ModelField  # type: ignore

        new_parameters.append(
            inspect.Parameter(
                model_field.alias,
                inspect.Parameter.POSITIONAL_ONLY,
                default=Form(...) if not model_field.required else Form(model_field.default),
                annotation=model_field.outer_type_,
            )
        )

    async def as_form_func(**data):
        return cls(**data)

    sig = inspect.signature(as_form_func)
    sig = sig.replace(parameters=new_parameters)
    as_form_func.__signature__ = sig  # type: ignore
    setattr(cls, 'as_form', as_form_func)
    return cast(Type[FormBaseModel], cls)
