import json
from typing import Type, Optional, Any

from tortoise import Model

from fastapi_admin2.widgets.inputs import Input, BaseManyToManyInput, BaseForeignKeyInput


class ForeignKey(BaseForeignKeyInput):
    def __init__(
            self,
            model: Type[Model],
            default: Optional[Any] = None,
            null: bool = False,
            disabled: bool = False,
            help_text: Optional[str] = None,
    ):
        super().__init__(help_text=help_text, default=default, null=null, disabled=disabled)
        self.model = model

    async def get_options(self):
        ret = await self.get_queryset()
        options = [(str(x), x.pk) for x in ret]
        if self.context.get("null"):
            options = [("", "")] + options
        return options

    async def get_queryset(self):
        return await self.model.all()


class ManyToMany(BaseManyToManyInput):
    template = "widgets/inputs/many_to_many.html"

    def __init__(
            self,
            model: Type[Model],
            disabled: bool = False,
            help_text: Optional[str] = None,
    ):
        super().__init__(help_text=help_text, disabled=disabled)
        self.model = model

    async def get_options(self):
        ret = await self.get_queryset()
        options = [dict(label=str(x), value=x.pk) for x in ret]
        return options

    async def get_queryset(self):
        return await self.model.all()

    async def render(self, value: Any):
        options = await self.get_options()
        selected = list(map(lambda x: x.pk, value.related_objects if value else []))
        for option in options:
            if option.get("value") in selected:
                option["selected"] = True
        self.context.update(options=json.dumps(options))
        return await super(Input, self).render(value)
