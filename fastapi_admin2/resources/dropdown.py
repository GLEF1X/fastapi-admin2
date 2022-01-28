from typing import List, Type

from fastapi_admin2.resources.base import Resource


class Dropdown(Resource):
    resources: List[Type[Resource]]
