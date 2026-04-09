from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def hello_world():
    """Hello world endpoint"""
    return {"message": "Hello, World!"}
