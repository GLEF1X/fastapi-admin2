from typing import List, Type

from fastapi_admin.resources.base import Resource


class Dropdown(Resource):
    resources: List[Type[Resource]]
