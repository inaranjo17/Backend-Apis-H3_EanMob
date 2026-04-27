# ========================================
# MATCHING INTELIGENTE H3
# HU-11: Coincidencias automáticas
# HU-12: Ordenamiento por relevancia
# ========================================

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from h3 import grid_distance
from ..db import get_pool
from ..auth import get_current_user
from ..h3_utils import h3_neighbors

router = APIRouter(prefix="/match", tags=["matching"])


# ────────────────────────────────────────
# MODELOS
# ────────────────────────────────────────

class MatchRequest(BaseModel):
    my_h3_origin: str
    my_h3_destination: str
    departure_time: datetime
    time_tolerance_minutes: int = 30
    max_h3_distance: int = 1
    # HU-13: filtro por comunidad (opcional)
    community_id: Optional[int] = None
    # HU-15: filtros avanzados (opcionales)
    max_cost: Optional[float] = None
    min_seats: Optional[int] = 1


class MatchCandidate(BaseModel):
    trip_id: int
    driver_name: str
    origin_h3: str
    destination_h3: str
    departure_datetime: datetime
    available_seats: int
    cost_per_passenger: Optional[float]
    distance_h3_origin: int
    time_diff_minutes: float
    relevance_score: float      # HU-12: score combinado


class MatchResponse(BaseModel):
    candidates: List[MatchCandidate]
    total: int
    message: Optional[str] = None 


# ────────────────────────────────────────
# SCORING MULTI-CRITERIO (HU-12)
# Combina distancia H3 + diferencia horaria
# Cuanto más alto el score, mejor la coincidencia
# ────────────────────────────────────────

def calculate_score(
    h3_distance: int,
    time_diff_minutes: float,
    max_h3_distance: int,
    time_tolerance: int,
) -> float:
    # Score de distancia: 1.0 si está en el mismo hex, 0.0 si está en el límite
    distance_score = 1.0 - (h3_distance / max(max_h3_distance, 1))

    # Score de tiempo: 1.0 si sale exactamente a la hora, 0.0 si está en el límite
    time_score = 1.0 - (abs(time_diff_minutes) / max(time_tolerance, 1))

    # Peso: distancia vale 60%, horario vale 40%
    return round((distance_score * 0.6) + (time_score * 0.4), 4)


# ────────────────────────────────────────
# ENDPOINT: Buscar coincidencias
# HU-11 + HU-12
# ────────────────────────────────────────

@router.post("/find", response_model=MatchResponse)
async def find_candidates(
    request: MatchRequest,
    user: dict = Depends(get_current_user),
):
    """
    Busca viajes disponibles compatibles usando H3.
    Ordena por score de relevancia (distancia + horario).
    """
    # 1. Expandir radio de búsqueda H3
    search_origins = h3_neighbors(request.my_h3_origin, request.max_h3_distance)
    search_dests   = h3_neighbors(request.my_h3_destination, request.max_h3_distance)

    origins_tuple = tuple(search_origins) if len(search_origins) > 1 else (search_origins[0], search_origins[0])
    dests_tuple   = tuple(search_dests)   if len(search_dests)   > 1 else (search_dests[0],   search_dests[0])

    tolerance_seconds = request.time_tolerance_minutes * 60

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    t.id,
                    t.conductor_id,
                    t.origin_h3,
                    t.destination_h3,
                    t.hora_inicio,
                    t.available_seats,
                    t.cost_per_passenger,
                    u.nombre_completo AS driver_name
                FROM trayectos t
                JOIN users_ean.usuarios u ON u.id = t.conductor_id
                WHERE
                    t.origin_h3 IN %s
                    AND t.destination_h3 IN %s
                    AND t.status = 'open'
                    AND t.available_seats >= %s
                    AND ABS(TIMESTAMPDIFF(SECOND, t.hora_inicio, %s)) <= %s
                ORDER BY t.hora_inicio ASC
                """,
                (
                    origins_tuple,
                    dests_tuple,
                    request.min_seats or 1,
                    request.departure_time,
                    tolerance_seconds,
                ),
            )
            rows = await cur.fetchall()

    # 2. Construir candidatos con score
    candidates: List[MatchCandidate] = []
    for row in rows:
        (trip_id, driver_id, origin_h3, destination_h3,
         departure_dt, available_seats, cost, driver_name) = row

        # No mostrar el propio viaje si el usuario es conductor
        if str(driver_id) == str(user.get("sub")):
            continue

        # Filtro por costo máximo (HU-15)
        if request.max_cost is not None and cost is not None:
            if float(cost) > request.max_cost:
                continue

        # Calcular distancia H3 real
        try:
            h3_dist = grid_distance(request.my_h3_origin, origin_h3)
        except Exception:
            h3_dist = 999

        # Calcular diferencia de tiempo en minutos
        time_diff = abs(
            (departure_dt - request.departure_time).total_seconds() / 60
        )

        # Calcular score de relevancia (HU-12)
        score = calculate_score(
            h3_dist,
            time_diff,
            request.max_h3_distance,
            request.time_tolerance_minutes,
        )

        candidates.append(MatchCandidate(
            trip_id=trip_id,
            driver_name=driver_name,
            origin_h3=origin_h3,
            destination_h3=destination_h3,
            departure_datetime=departure_dt,
            available_seats=available_seats,
            cost_per_passenger=float(cost) if cost else None,
            distance_h3_origin=h3_dist,
            time_diff_minutes=round(time_diff, 1),
            relevance_score=score,
        ))

    # 3. Ordenar por score descendente (mejor primero) — HU-12
    candidates.sort(key=lambda c: c.relevance_score, reverse=True)

    if not candidates:
        return MatchResponse(
            candidates=[],
            total=0,
            message="No se encontraron viajes que coincidan con tu búsqueda."
        )

    return MatchResponse(candidates=candidates, total=len(candidates))


# ────────────────────────────────────────
# ENDPOINT: Publicar viaje con H3
# ────────────────────────────────────────

class PublishTripRequest(BaseModel):
    origin_address: str
    destination_address: str
    departure_datetime: datetime
    available_seats: int
    cost_per_passenger: Optional[float] = None
    vehicle_id: Optional[int] = None


class PublishTripResponse(BaseModel):
    trip_id: int
    origin_h3: str
    destination_h3: str
    message: str


@router.post("/publish-trip", response_model=PublishTripResponse)
async def publish_trip(
    body: PublishTripRequest,
    user: dict = Depends(get_current_user),
):
    """
    Geocodifica origen y destino, calcula H3
    y guarda el viaje listo para el matching.
    """
    from ..maps_client import gmaps_client
    from ..h3_utils import lat_lng_to_h3

    origin_result = gmaps_client.geocode(body.origin_address, region="co")
    if not origin_result:
        raise HTTPException(status_code=404, detail="Dirección de origen no encontrada")

    dest_result = gmaps_client.geocode(body.destination_address, region="co")
    if not dest_result:
        raise HTTPException(status_code=404, detail="Dirección de destino no encontrada")

    origin_loc = origin_result[0]["geometry"]["location"]
    dest_loc   = dest_result[0]["geometry"]["location"]

    origin_h3 = lat_lng_to_h3(origin_loc["lat"], origin_loc["lng"])
    dest_h3   = lat_lng_to_h3(dest_loc["lat"],   dest_loc["lng"])

    conductor_id = int(user["sub"])

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO trayectos
                  (conductor_id, nombre_prestador, origen, destino,
                   hora_inicio, available_seats, cost_per_passenger,
                   vehicle_id, status, origin_h3, destination_h3,
                   origin_lat, origin_lng, destination_lat, destination_lng)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'open', %s, %s, %s, %s, %s, %s)
                """,
                (
                    conductor_id,
                    user.get("correo", ""),
                    body.origin_address,
                    body.destination_address,
                    body.departure_datetime,
                    body.available_seats,
                    body.cost_per_passenger,
                    body.vehicle_id,
                    origin_h3,
                    dest_h3,
                    origin_loc["lat"],
                    origin_loc["lng"],
                    dest_loc["lat"],
                    dest_loc["lng"],
                ),
            )
            trip_id = cur.lastrowid

    return PublishTripResponse(
        trip_id=trip_id,
        origin_h3=origin_h3,
        destination_h3=dest_h3,
        message="Viaje publicado correctamente",
    )




# ────────────────────────────────────────
# MODELOS — HU-16
# ────────────────────────────────────────

class NearbyTripMarker(BaseModel):
    trip_id: int
    driver_name: str
    # Coordenadas para el marcador en Google Maps
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    # Datos para el popup del marcador
    origin_address: str
    destination_address: str
    departure_datetime: datetime
    available_seats: int
    cost_per_passenger: Optional[float]
    distance_h3_origin: int
    relevance_score: float


class NearbyTripsResponse(BaseModel):
    markers: List[NearbyTripMarker]
    total: int
    center_lat: float   # Centro del mapa (ubicación del pasajero)
    center_lng: float   # Centro del mapa (ubicación del pasajero)
    message: Optional[str] = None


# ────────────────────────────────────────
# ENDPOINT: Mapa con ofertantes cercanos
# HU-16
# ────────────────────────────────────────

@router.get("/nearby", response_model=NearbyTripsResponse)
async def get_nearby_trips(
    my_h3_origin: str,
    my_h3_destination: str,
    my_lat: float,
    my_lng: float,
    departure_time: datetime,
    time_tolerance_minutes: int = 30,
    max_h3_distance: int = 1,
    user: dict = Depends(get_current_user),
):
    """
    Devuelve viajes disponibles cercanos al pasajero con coordenadas
    listas para pintar marcadores en Google Maps.
    HU-16: Ver mapa con ofertantes cercanos.
    """
    # 1. Expandir radio de búsqueda H3
    search_origins = h3_neighbors(my_h3_origin, max_h3_distance)
    search_dests   = h3_neighbors(my_h3_destination, max_h3_distance)

    origins_tuple = tuple(search_origins) if len(search_origins) > 1 else (search_origins[0], search_origins[0])
    dests_tuple   = tuple(search_dests)   if len(search_dests)   > 1 else (search_dests[0],   search_dests[0])

    tolerance_seconds = time_tolerance_minutes * 60

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT
                    t.id,
                    t.conductor_id,
                    t.origin_h3,
                    t.destination_h3,
                    t.origen,
                    t.destino,
                    t.hora_inicio,
                    t.available_seats,
                    t.cost_per_passenger,
                    t.origin_lat,
                    t.origin_lng,
                    t.destination_lat,
                    t.destination_lng,
                    u.nombre_completo AS driver_name
                FROM trayectos t
                JOIN users_ean.usuarios u ON u.id = t.conductor_id
                WHERE
                    t.origin_h3 IN %s
                    AND t.destination_h3 IN %s
                    AND t.status = 'open'
                    AND t.available_seats > 0
                    AND t.origin_lat IS NOT NULL
                    AND t.origin_lng IS NOT NULL
                    AND ABS(TIMESTAMPDIFF(SECOND, t.hora_inicio, %s)) <= %s
                ORDER BY t.hora_inicio ASC
                """,
                (origins_tuple, dests_tuple, departure_time, tolerance_seconds),
            )
            rows = await cur.fetchall()

    # 2. Construir marcadores
    markers: List[NearbyTripMarker] = []

    for row in rows:
        (trip_id, driver_id, origin_h3, destination_h3,
         origen, destino, departure_dt, available_seats,
         cost, o_lat, o_lng, d_lat, d_lng, driver_name) = row

        # Excluir el propio conductor
        if str(driver_id) == str(user.get("sub")):
            continue

        # Saltar viajes sin coordenadas
        if o_lat is None or o_lng is None:
            continue

        try:
            h3_dist = grid_distance(my_h3_origin, origin_h3)
        except Exception:
            h3_dist = 999

        time_diff = abs(
            (departure_dt - departure_time).total_seconds() / 60
        )

        score = calculate_score(
            h3_dist,
            time_diff,
            max_h3_distance,
            time_tolerance_minutes,
        )

        markers.append(NearbyTripMarker(
            trip_id=trip_id,
            driver_name=driver_name,
            origin_lat=float(o_lat),
            origin_lng=float(o_lng),
            destination_lat=float(d_lat) if d_lat else 0.0,
            destination_lng=float(d_lng) if d_lng else 0.0,
            origin_address=origen,
            destination_address=destino,
            departure_datetime=departure_dt,
            available_seats=available_seats,
            cost_per_passenger=float(cost) if cost else None,
            distance_h3_origin=h3_dist,
            relevance_score=score,
        ))

    # 3. Ordenar por score
    markers.sort(key=lambda m: m.relevance_score, reverse=True)

    if not markers:
        return NearbyTripsResponse(
            markers=[],
            total=0,
            center_lat=my_lat,
            center_lng=my_lng,
            message="No hay conductores disponibles cerca de tu ubicación.",
        )

    return NearbyTripsResponse(
        markers=markers,
        total=len(markers),
        center_lat=my_lat,
        center_lng=my_lng,
    )