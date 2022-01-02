from typing import Optional, Mapping

from starlette.requests import Request

from fastapi_admin.widgets import displays, inputs, Widget


class Field:
    name: str
    label: str
    display: displays.Display
    input: inputs.Input

    def __init__(
            self,
            name: str,
            label: Optional[str] = None,
            display: Optional[displays.Display] = None,
            input_: Optional[Widget] = None,
    ):
        self.name = name
        self.label = label or name.title()
        if not display:
            display = displays.Display()
        display.context.update(label=self.label)
        self.display = display
        if not input_:
            input_ = inputs.Input()
        input_.context.update(label=self.label, name=name)
        self.input = input_


class ComputeField(Field):
    async def get_value(self, request: Request, obj: Mapping):
        return obj.get(self.name)
