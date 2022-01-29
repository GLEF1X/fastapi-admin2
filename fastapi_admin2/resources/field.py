from typing import Optional, Mapping, Any

from starlette.requests import Request

from fastapi_admin2.widgets import displays, inputs
from fastapi_admin2.widgets.inputs import Input


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
            input_: Optional[Input] = None,
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


class ComputedField(Field):
    async def get_value(self, request: Request, obj: Mapping) -> Optional[Any]:
        return obj.get(self.name)
