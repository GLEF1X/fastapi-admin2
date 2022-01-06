from fastapi_admin.widgets.inputs import BaseForeignKeyInput


class ForeignKey(BaseForeignKeyInput):
    async def get_options(self):
        pass