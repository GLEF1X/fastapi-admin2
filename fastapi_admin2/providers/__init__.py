import typing

if typing.TYPE_CHECKING:
    from fastapi_admin2.app import FastAPIAdmin


class Provider:
    name = "provider"

    def register(self, app: "FastAPIAdmin"):
        setattr(app, self.name, self)
