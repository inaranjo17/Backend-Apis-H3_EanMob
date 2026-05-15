import json
from datetime import date, time, timedelta
from typing import Any

from app.schemas.pico_placa import RegionalEvent, UrbanRule


def _parse_json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [item.strip() for item in value.split(",") if item.strip()]
        return [str(item) for item in parsed]
    return [str(value)]


def _parse_mysql_time(value: Any) -> time:
    if isinstance(value, time):
        return value
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return time(hours % 24, minutes, seconds)
    if isinstance(value, str):
        parts = [int(part) for part in value.split(":")]
        return time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)
    raise TypeError(f"Unsupported MySQL TIME value: {value!r}")


async def list_active_urban_rules(city: str) -> list[UrbanRule]:
    import aiomysql

    from app.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT
                    city,
                    weekday_start,
                    weekday_end,
                    start_time,
                    end_time,
                    odd_day_digits,
                    even_day_digits
                FROM pico_placa_rules
                WHERE active = 1 AND UPPER(city) = UPPER(%s)
                ORDER BY id ASC
                """,
                (city,),
            )
            rows = await cursor.fetchall()

    return [
        UrbanRule(
            city=row["city"],
            weekday_start=row["weekday_start"],
            weekday_end=row["weekday_end"],
            start_time=_parse_mysql_time(row["start_time"]),
            end_time=_parse_mysql_time(row["end_time"]),
            odd_day_digits=set(_parse_json_list(row["odd_day_digits"])),
            even_day_digits=set(_parse_json_list(row["even_day_digits"])),
        )
        for row in rows
    ]


async def list_active_regional_events(check_date: date) -> list[RegionalEvent]:
    import aiomysql

    from app.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT
                    e.rule_id,
                    e.event_date,
                    e.start_time,
                    e.end_time,
                    e.restricted_digits,
                    e.direction,
                    s.name AS source
                FROM pico_placa_regional_events e
                LEFT JOIN pico_placa_sources s ON s.id = e.source_id
                WHERE e.active = 1 AND e.event_date = %s
                ORDER BY e.start_time ASC, e.id ASC
                """,
                (check_date,),
            )
            rows = await cursor.fetchall()

            event_ids = [row["rule_id"] for row in rows]
            corridors_by_rule: dict[str, list[str]] = {rule_id: [] for rule_id in event_ids}
            if event_ids:
                placeholders = ", ".join(["%s"] * len(event_ids))
                await cursor.execute(
                    f"""
                    SELECT event_rule_id, corridor_id
                    FROM pico_placa_regional_corridors
                    WHERE active = 1 AND event_rule_id IN ({placeholders})
                    ORDER BY id ASC
                    """,
                    tuple(event_ids),
                )
                corridor_rows = await cursor.fetchall()
                for row in corridor_rows:
                    corridors_by_rule.setdefault(row["event_rule_id"], []).append(row["corridor_id"])

    return [
        RegionalEvent(
            rule_id=row["rule_id"],
            date=row["event_date"],
            start_time=_parse_mysql_time(row["start_time"]),
            end_time=_parse_mysql_time(row["end_time"]),
            restricted_digits=_parse_json_list(row["restricted_digits"]),
            corridor_ids=corridors_by_rule.get(row["rule_id"], []),
            direction=row["direction"],
            source=row["source"],
        )
        for row in rows
    ]


async def list_sources() -> list[dict]:
    import aiomysql

    from app.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                SELECT id, name, source_type, url, active, created_at, updated_at
                FROM pico_placa_sources
                WHERE active = 1
                ORDER BY id ASC
                """
            )
            return await cursor.fetchall()


async def create_sync_run(source_id: int | None, status: str, message: str) -> int:
    import aiomysql

    from app.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                """
                INSERT INTO pico_placa_sync_runs (source_id, status, message)
                VALUES (%s, %s, %s)
                """,
                (source_id, status, message),
            )
            return cursor.lastrowid
