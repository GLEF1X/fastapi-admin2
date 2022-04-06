import typing

from fastapi_admin2.utils.templating import JinjaTemplates

if typing.TYPE_CHECKING:
    from fastapi_admin2.app import FastAPIAdmin


class Provider:
    name = "provider"
    templates: typing.Optional[JinjaTemplates] = None

    def register(self, app: "FastAPIAdmin"):
        setattr(app, self.name, self)

        self.templates = app.templates
