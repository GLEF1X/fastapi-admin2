from fastapi_admin2.resources.base import Resource


class Link(Resource):
    url: str
    target: str = "_self"
