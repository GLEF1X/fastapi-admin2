from dataclasses import dataclass, field
from typing import Optional, Mapping, Any, List, Callable

from starlette.requests import Request

from fastapi_admin2.ui.widgets import displays, inputs
from fastapi_admin2.ui.widgets.inputs import Input


@dataclass
class Field:
    name: str
    label: str
    display: displays.Display = field(default_factory=displays.Display)
    input: inputs.Input = field(default_factory=inputs.Input)
    validators: List[Callable[[Any], bool]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.display.context.update(label=self.label)
        self.input.context.update(label=self.label)


class ComputedField(Field):
    async def get_value(self, request: Request, obj: Mapping[str, Any]) -> Optional[Any]:
        return obj.get(self.name)
