from fastapi import FastAPI

app = FastAPI()

from app.routes import hello

app.include_router(hello.router)
