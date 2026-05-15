from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
 
from .config import settings
from .db import get_pool, close_pool
from .routers import geocode, routes, match, pico_placa
 
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    print("✅ Conexión a MySQL establecida")
    yield
    await close_pool()
    print("🔴 Pool de MySQL cerrado")
 
 
app = FastAPI(title="EANMob — Matching & Geo API", lifespan=lifespan)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.include_router(geocode.router)
app.include_router(routes.router)
app.include_router(match.router)
app.include_router(pico_placa.router)
app.add_exception_handler(RequestValidationError, pico_placa.validation_exception_handler)
 
 
@app.get("/health")
def health():
    return {"status": "ok"}
 
 
@app.get("/config-test")
def config_test():
    return {"maps_key_loaded": bool(settings.google_maps_api_key_backend)}
