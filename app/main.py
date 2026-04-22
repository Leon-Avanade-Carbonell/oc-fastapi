from fastapi import FastAPI

app = FastAPI()

from app.routes import hello, climate, opensky
from app.routes.climate_mvt import router as climate_mvt_router

app.include_router(hello.router)
app.include_router(climate.router)
app.include_router(climate_mvt_router.router)
app.include_router(opensky.router)
