from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _normalize_plate_value(value: str) -> str:
    return "".join(character for character in value.upper() if character.isalnum())


class RouteContext(BaseModel):
    direction: Literal["inbound", "outbound", "both"] | None = None
    corridor_id: str | None = None


class UrbanRule(BaseModel):
    city: str = "Bogota"
    weekday_start: int = 0
    weekday_end: int = 4
    start_time: time = time(6, 0)
    end_time: time = time(21, 0)
    odd_day_digits: set[str] = Field(default_factory=lambda: {"6", "7", "8", "9", "0"})
    even_day_digits: set[str] = Field(default_factory=lambda: {"1", "2", "3", "4", "5"})


class PicoPlacaCheckInput(BaseModel):
    plate: str
    datetime: datetime
    city: str = "BOGOTA"
    vehicle_type: str = "Carro"
    route_context: RouteContext | None = None

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, value: str) -> str:
        normalized = _normalize_plate_value(value)
        if not any(character.isdigit() for character in normalized):
            raise ValueError("plate must contain at least one numeric digit")
        return normalized


class PicoPlacaWarning(BaseModel):
    type: Literal["urban", "regional"]
    severity: Literal["confirmed", "possible"]
    message: str
    rule_id: str | None = None
    source: str | None = None


class PicoPlacaCheckResult(BaseModel):
    restricted: bool
    urban_restricted: bool
    regional_restricted: bool
    regional_possible: bool
    plate: str
    plate_last_digit: str
    warnings: list[PicoPlacaWarning] = Field(default_factory=list)


class RegionalEvent(BaseModel):
    rule_id: str
    date: date
    start_time: time
    end_time: time
    restricted_digits: list[str]
    corridor_ids: list[str] = Field(default_factory=list)
    direction: Literal["inbound", "outbound", "both"] | None = None
    source: str | None = None

    @field_validator("restricted_digits", mode="before")
    @classmethod
    def normalize_restricted_digits(cls, value: list[str]) -> list[str]:
        return [str(digit)[-1] for digit in value]
