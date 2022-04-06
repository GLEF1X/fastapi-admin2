from fastapi.routing import APIRouter
from starlette.requests import Request
from starlette.responses import Response

router = APIRouter(prefix="/api/v1")


@router.get("/simple")
async def handle_test(request: Request):
    print(request.headers)
    return Response(content="Hello world!")


@router.get("/simpleWithXHeader")
async def handle_simpleWithXHeader():
    return Response(content="Hello world!", headers={"X-Test": "test"})


@router.put("/complicated")
async def handle_complicated():
    return {"ok": True}
