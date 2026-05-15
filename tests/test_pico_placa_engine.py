from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.pico_placa import PicoPlacaCheckInput, RegionalEvent, RouteContext, UrbanRule
from app.services.pico_placa_engine import evaluate_pico_placa, get_last_digit, normalize_plate


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def test_urban_odd_calendar_day_restricts_digits_six_to_zero():
    request = PicoPlacaCheckInput(
        plate="ABC128",
        datetime=dt("2026-05-15T10:00:00-05:00"),
    )

    result = evaluate_pico_placa(request)

    assert result.restricted is True
    assert result.urban_restricted is True
    assert result.plate_last_digit == "8"
    assert any(warning.type == "urban" for warning in result.warnings)


def test_urban_odd_calendar_day_allows_digits_one_to_five():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-15T10:00:00-05:00"),
    )

    result = evaluate_pico_placa(request)

    assert result.restricted is False
    assert result.urban_restricted is False


def test_urban_even_calendar_day_restricts_digits_one_to_five():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-18T10:00:00-05:00"),
    )

    result = evaluate_pico_placa(request)

    assert result.restricted is True
    assert result.urban_restricted is True
    assert result.plate_last_digit == "3"


def test_outside_urban_window_is_not_restricted():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-15T21:00:00-05:00"),
    )

    result = evaluate_pico_placa(request)

    assert result.restricted is False
    assert result.urban_restricted is False
    assert result.warnings == []


def test_weekend_is_not_restricted_for_urban_rule():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-16T10:00:00-05:00"),
    )

    result = evaluate_pico_placa(request)

    assert result.restricted is False
    assert result.urban_restricted is False


def test_moto_is_exempt_for_mvp():
    request = PicoPlacaCheckInput(
        plate="MOT123",
        datetime=dt("2026-05-15T10:00:00-05:00"),
        vehicle_type="Moto",
    )

    result = evaluate_pico_placa(request)

    assert result.restricted is False
    assert result.urban_restricted is False
    assert result.regional_restricted is False


def test_non_bogota_request_does_not_apply_default_bogota_urban_rule():
    request = PicoPlacaCheckInput(
        plate="ABC128",
        datetime=dt("2026-05-15T10:00:00-05:00"),
        city="MEDELLIN",
    )

    result = evaluate_pico_placa(request)

    assert result.restricted is False
    assert result.urban_restricted is False
    assert result.warnings == []


def test_empty_urban_rules_disables_default_bogota_urban_rule():
    request = PicoPlacaCheckInput(
        plate="ABC128",
        datetime=dt("2026-05-15T10:00:00-05:00"),
    )

    result = evaluate_pico_placa(request, urban_rules=[])

    assert result.restricted is False
    assert result.urban_restricted is False
    assert result.warnings == []


def test_non_bogota_urban_rule_is_ignored():
    request = PicoPlacaCheckInput(
        plate="ABC128",
        datetime=dt("2026-05-15T10:00:00-05:00"),
        city="MEDELLIN",
    )

    result = evaluate_pico_placa(request, urban_rules=[UrbanRule(city="MEDELLIN")])

    assert result.restricted is False
    assert result.urban_restricted is False


def test_regional_confirmed_restriction_when_time_digit_and_corridor_match():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-16T15:30:00-05:00"),
        route_context=RouteContext(direction="outbound", corridor_id="autopista-norte"),
    )
    event = RegionalEvent(
        rule_id="regional-2026-05-16-outbound",
        date="2026-05-16",
        start_time="14:00",
        end_time="20:00",
        restricted_digits=["3", "4"],
        corridor_ids=["autopista-norte"],
        direction="outbound",
        source="manual-test",
    )

    result = evaluate_pico_placa(request, regional_events=[event])

    assert result.restricted is True
    assert result.regional_restricted is True
    assert result.regional_possible is False
    assert any(warning.type == "regional" and warning.severity == "confirmed" for warning in result.warnings)


def test_regional_possible_warning_when_event_applies_without_corridor_context():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-16T15:30:00-05:00"),
    )
    event = RegionalEvent(
        rule_id="regional-2026-05-16-outbound",
        date="2026-05-16",
        start_time="14:00",
        end_time="20:00",
        restricted_digits=["3", "4"],
        corridor_ids=["autopista-norte"],
        direction="outbound",
        source="manual-test",
    )

    result = evaluate_pico_placa(request, regional_events=[event])

    assert result.restricted is True
    assert result.regional_restricted is False
    assert result.regional_possible is True
    assert any(warning.type == "regional" and warning.severity == "possible" for warning in result.warnings)


def test_regional_event_with_both_direction_matches_inbound_route():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-16T15:30:00-05:00"),
        route_context=RouteContext(direction="inbound", corridor_id="autopista-norte"),
    )
    event = RegionalEvent(
        rule_id="regional-2026-05-16-both",
        date="2026-05-16",
        start_time="14:00",
        end_time="20:00",
        restricted_digits=["3"],
        corridor_ids=["autopista-norte"],
        direction="both",
        source="manual-test",
    )

    result = evaluate_pico_placa(request, regional_events=[event])

    assert result.regional_restricted is True
    assert result.regional_possible is False


def test_regional_event_without_corridor_scope_is_confirmed_without_route_context():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-16T15:30:00-05:00"),
    )
    event = RegionalEvent(
        rule_id="regional-2026-05-16-all-corridors",
        date="2026-05-16",
        start_time="14:00",
        end_time="20:00",
        restricted_digits=["3"],
        corridor_ids=[],
        direction="both",
        source="manual-test",
    )

    result = evaluate_pico_placa(request, regional_events=[event])

    assert result.regional_restricted is True
    assert result.regional_possible is False


def test_regional_event_passed_as_urban_rule_is_rejected():
    request = PicoPlacaCheckInput(
        plate="ABC123",
        datetime=dt("2026-05-16T15:30:00-05:00"),
    )
    event = RegionalEvent(
        rule_id="regional-2026-05-16",
        date="2026-05-16",
        start_time="14:00",
        end_time="20:00",
        restricted_digits=["3"],
    )

    with pytest.raises(TypeError):
        evaluate_pico_placa(request, urban_rules=[event])


def test_invalid_plate_with_no_numeric_digit_validates_as_error():
    with pytest.raises(ValidationError):
        PicoPlacaCheckInput(plate="ABCXYZ", datetime=dt("2026-05-15T10:00:00-05:00"))

    with pytest.raises(ValueError):
        get_last_digit(normalize_plate("ABCXYZ"))
