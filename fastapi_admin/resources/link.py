from fastapi_admin.resources.base import Resource


class Link(Resource):
    url: str
    target: str = "_self"
