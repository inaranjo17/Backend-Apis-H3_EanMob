from datetime import time

from app.schemas.pico_placa import (
    PicoPlacaCheckInput,
    PicoPlacaCheckResult,
    PicoPlacaWarning,
    RegionalEvent,
    UrbanRule,
)


def normalize_plate(plate: str) -> str:
    return "".join(character for character in plate.upper() if character.isalnum())


def get_last_digit(plate: str) -> str:
    for character in reversed(plate):
        if character.isdigit():
            return character
    raise ValueError("plate must contain at least one numeric digit")


def evaluate_pico_placa(
    request: PicoPlacaCheckInput,
    urban_rules: list[UrbanRule] | None = None,
    regional_events: list[RegionalEvent] | None = None,
) -> PicoPlacaCheckResult:
    plate = normalize_plate(request.plate)
    last_digit = get_last_digit(plate)
    warnings: list[PicoPlacaWarning] = []

    urban_restricted = False
    for rule in _resolve_urban_rules(urban_rules):
        if _evaluate_urban_rule(request, rule, last_digit):
            urban_restricted = True
            break

    if urban_restricted:
        warnings.append(
            PicoPlacaWarning(
                type="urban",
                severity="confirmed",
                message="Vehicle is restricted by Bogota urban pico y placa.",
            )
        )

    regional_restricted = False
    regional_possible = False
    for event in regional_events or []:
        match = _evaluate_regional_event(request, event, last_digit)
        if match == "confirmed":
            regional_restricted = True
            warnings.append(
                PicoPlacaWarning(
                    type="regional",
                    severity="confirmed",
                    message="Vehicle is restricted by a regional pico y placa event.",
                    rule_id=event.rule_id,
                    source=event.source,
                )
            )
        elif match == "possible":
            regional_possible = True
            warnings.append(
                PicoPlacaWarning(
                    type="regional",
                    severity="possible",
                    message="A regional pico y placa event may apply; route corridor is unknown.",
                    rule_id=event.rule_id,
                    source=event.source,
                )
            )

    return PicoPlacaCheckResult(
        restricted=urban_restricted or regional_restricted or regional_possible,
        urban_restricted=urban_restricted,
        regional_restricted=regional_restricted,
        regional_possible=regional_possible,
        plate=plate,
        plate_last_digit=last_digit,
        warnings=warnings,
    )


def _resolve_urban_rules(urban_rules: list[UrbanRule] | None) -> list[UrbanRule]:
    if urban_rules is None:
        return [UrbanRule()]
    if not all(isinstance(rule, UrbanRule) for rule in urban_rules):
        raise TypeError("urban_rules must contain only UrbanRule instances")
    return urban_rules


def _evaluate_urban_rule(
    request: PicoPlacaCheckInput,
    rule: UrbanRule,
    last_digit: str,
) -> bool:
    if request.vehicle_type.lower() == "moto":
        return False

    if request.city.upper() != "BOGOTA" or rule.city.upper() != "BOGOTA":
        return False
    if request.city.upper() != rule.city.upper():
        return False

    current_dt = request.datetime
    current_time = current_dt.time()

    if not rule.weekday_start <= current_dt.weekday() <= rule.weekday_end:
        return False
    if not _time_in_window(current_time, rule.start_time, rule.end_time):
        return False

    restricted_digits = rule.odd_day_digits if current_dt.day % 2 else rule.even_day_digits
    return last_digit in restricted_digits


def _evaluate_regional_event(
    request: PicoPlacaCheckInput,
    event: RegionalEvent,
    last_digit: str,
) -> str | None:
    current_dt = request.datetime
    if current_dt.date() != event.date:
        return None
    if not _time_in_window(current_dt.time(), event.start_time, event.end_time):
        return None
    if last_digit not in event.restricted_digits:
        return None

    route_context = request.route_context
    if not event.corridor_ids and (event.direction in (None, "both")):
        return "confirmed"
    if route_context is None or route_context.corridor_id is None:
        return "possible"

    if event.direction and event.direction != "both" and route_context.direction != event.direction:
        return None
    if event.corridor_ids and route_context.corridor_id not in event.corridor_ids:
        return None

    return "confirmed"


def _time_in_window(value: time, start: time, end: time) -> bool:
    return start <= value < end
