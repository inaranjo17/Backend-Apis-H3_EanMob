from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .routers import pico_placa

app = FastAPI(title="EANMob — Pico y Placa API")
app.include_router(pico_placa.router)
app.add_exception_handler(RequestValidationError, pico_placa.validation_exception_handler)


@app.get("/health")
def health():
    return {"status": "ok"}
