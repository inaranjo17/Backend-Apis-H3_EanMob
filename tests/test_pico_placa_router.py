from datetime import date
from datetime import timedelta

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from app.routers import pico_placa
from app.schemas.pico_placa import UrbanRule
from app.repositories.pico_placa_repo import _parse_mysql_time


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(pico_placa.router)
    app.add_exception_handler(RequestValidationError, pico_placa.validation_exception_handler)
    return TestClient(app)


def test_check_returns_restricted_result(monkeypatch):
    async def fake_list_active_urban_rules(city: str):
        assert city == "BOGOTA"
        return [UrbanRule(city="BOGOTA")]

    async def fake_list_active_regional_events(check_date: date):
        assert check_date == date(2026, 5, 15)
        return []

    monkeypatch.setattr(
        pico_placa.pico_placa_repo,
        "list_active_urban_rules",
        fake_list_active_urban_rules,
    )
    monkeypatch.setattr(
        pico_placa.pico_placa_repo,
        "list_active_regional_events",
        fake_list_active_regional_events,
    )

    client = build_client()
    response = client.post(
            "/api/v1/pico-placa/check",
            json={
                "plate": "ABC128",
                "datetime": "2026-05-15T10:00:00-05:00",
            },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["message"] == "Verificacion completada"
    assert body["data"]["restricted"] is True
    assert body["data"]["plate"] == "ABC128"


def test_check_rejects_invalid_plate():
    client = build_client()
    response = client.post(
        "/api/v1/pico-placa/check",
        json={
            "plate": "ABCXYZ",
            "datetime": "2026-05-15T10:00:00-05:00",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["message"] == "Solicitud invalida"


def test_rules_returns_active_sources_rules_and_events(monkeypatch):
    async def fake_list_sources():
        return [{"id": 1, "name": "Bogota Movilidad", "active": True}]

    async def fake_list_active_urban_rules(city: str):
        assert city == "BOGOTA"
        return [UrbanRule(city="BOGOTA")]

    async def fake_list_active_regional_events(check_date: date):
        assert isinstance(check_date, date)
        return []

    monkeypatch.setattr(pico_placa.pico_placa_repo, "list_sources", fake_list_sources)
    monkeypatch.setattr(
        pico_placa.pico_placa_repo,
        "list_active_urban_rules",
        fake_list_active_urban_rules,
    )
    monkeypatch.setattr(
        pico_placa.pico_placa_repo,
        "list_active_regional_events",
        fake_list_active_regional_events,
    )

    client = build_client()
    response = client.get("/api/v1/pico-placa/rules")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["sources"][0]["name"] == "Bogota Movilidad"
    assert body["data"]["urban_rules"][0]["city"] == "BOGOTA"
    assert body["data"]["regional_events"] == []


def test_sync_records_noop_run(monkeypatch):
    calls = []

    async def fake_create_sync_run(source_id: int | None, status: str, message: str):
        calls.append((source_id, status, message))
        return 42

    monkeypatch.setattr(
        pico_placa.pico_placa_repo,
        "create_sync_run",
        fake_create_sync_run,
    )

    client = build_client()
    response = client.post("/api/v1/pico-placa/sync")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["sync_run_id"] == 42
    assert body["data"]["status"] == "noop"
    assert "no parseable official API source is configured" in body["message"]
    assert calls == [(None, "noop", body["message"])]


def test_parse_mysql_time_accepts_timedelta_values():
    parsed = _parse_mysql_time(timedelta(hours=6, minutes=30))

    assert parsed.hour == 6
    assert parsed.minute == 30
    assert parsed.second == 0


def test_check_falls_back_to_default_urban_rule_when_rule_table_is_unavailable(monkeypatch):
    async def broken_list_active_urban_rules(_city: str):
        raise RuntimeError("table does not exist")

    async def broken_list_active_regional_events(_check_date: date):
        raise RuntimeError("table does not exist")

    monkeypatch.setattr(
        pico_placa.pico_placa_repo,
        "list_active_urban_rules",
        broken_list_active_urban_rules,
    )
    monkeypatch.setattr(
        pico_placa.pico_placa_repo,
        "list_active_regional_events",
        broken_list_active_regional_events,
    )

    client = build_client()
    response = client.post(
        "/api/v1/pico-placa/check",
        json={
            "plate": "ABC128",
            "datetime": "2026-05-15T10:00:00-05:00",
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["urban_restricted"] is True
