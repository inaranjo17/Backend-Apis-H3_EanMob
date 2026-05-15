from datetime import date

from fastapi import APIRouter, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.repositories import pico_placa_repo
from app.schemas.pico_placa import PicoPlacaCheckInput, UrbanRule
from app.services.pico_placa_engine import evaluate_pico_placa

router = APIRouter(prefix="/api/v1/pico-placa", tags=["pico-placa"])


def envelope(data, message: str):
    return {
        "success": True,
        "data": jsonable_encoder(data),
        "error": None,
        "message": message,
    }


async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "data": None,
            "error": jsonable_encoder(exc.errors()),
            "message": "Solicitud invalida",
        },
    )


async def _active_urban_rules(city: str):
    try:
        return await pico_placa_repo.list_active_urban_rules(city)
    except Exception:
        if city.upper() == "BOGOTA":
            return [UrbanRule(city="BOGOTA")]
        return []


async def _active_regional_events(check_date: date):
    try:
        return await pico_placa_repo.list_active_regional_events(check_date)
    except Exception:
        return []


async def _sources():
    try:
        return await pico_placa_repo.list_sources()
    except Exception:
        return []


@router.post("/check")
async def check_pico_placa(payload: PicoPlacaCheckInput):
    urban_rules = await _active_urban_rules(payload.city)
    regional_events = await _active_regional_events(payload.datetime.date())
    result = evaluate_pico_placa(
        payload,
        urban_rules=urban_rules,
        regional_events=regional_events,
    )
    return envelope(result, "Verificacion completada")


@router.get("/rules")
async def list_rules(city: str = "BOGOTA", check_date: date | None = None):
    target_date = check_date or date.today()
    sources = await _sources()
    urban_rules = await _active_urban_rules(city)
    regional_events = await _active_regional_events(target_date)
    return envelope(
        {
            "sources": sources,
            "urban_rules": urban_rules,
            "regional_events": regional_events,
        },
        "Reglas consultadas",
    )


@router.post("/sync")
async def sync_pico_placa():
    message = "Pico y placa sync no-op: no parseable official API source is configured for MVP."
    try:
        sync_run_id = await pico_placa_repo.create_sync_run(
            source_id=None,
            status="noop",
            message=message,
        )
    except Exception:
        sync_run_id = None
    return envelope(
        {
            "sync_run_id": sync_run_id,
            "status": "noop",
        },
        message,
    )
