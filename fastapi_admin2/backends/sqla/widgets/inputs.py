from fastapi_admin2.widgets.inputs import BaseForeignKeyInput


class ForeignKey(BaseForeignKeyInput):
    async def get_options(self):
        pass
