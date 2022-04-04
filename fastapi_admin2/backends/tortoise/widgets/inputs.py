import json
from typing import Any

from starlette.requests import Request

from fastapi_admin2.widgets.inputs import Input, BaseManyToManyInput, BaseForeignKeyInput


class ForeignKey(BaseForeignKeyInput):
    async def get_options(self):
        ret = await self.get_queryset()
        options = [(str(x), x.pk) for x in ret]
        if self.context.get("null"):
            options = [("", "")] + options
        return options

    async def get_queryset(self):
        return await self.model.all()


class ManyToMany(BaseManyToManyInput):
    template_name = "widgets/inputs/many_to_many.html"

    async def render(self, request: Request, value: Any):
        options = await self.get_options()
        selected = list(map(lambda x: x.pk, value.related_objects if value else []))
        for option in options:
            if option.get("value") in selected:
                option["selected"] = True
        self.context.update(options=json.dumps(options))
        return await super(Input, self).render(request, value)

    async def get_options(self):
        ret = await self.get_queryset()
        options = [dict(label=str(x), value=x.pk) for x in ret]
        return options

    async def get_queryset(self):
        return await self.model.all()
