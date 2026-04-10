from fastapi import FastAPI

app = FastAPI()

from app.routes import hello, climate

app.include_router(hello.router)
app.include_router(climate.router)
