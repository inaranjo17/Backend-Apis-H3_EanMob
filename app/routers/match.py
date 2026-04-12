################### ENDPOINT 3 ################
# Matching inteligente usando H3 + FILTRO POR TIEMPO
#
# Recibe:
# - H3 origen
# - H3 destino
# - Rol (conductor / pasajero)
# - Hora de salida deseada
#
# Lógica:
# - Expande búsqueda con grid_disk (hexágono + vecinos)
# - Filtra por cercanía geográfica (H3)
# - Filtra por compatibilidad de destino
# - 🔥 NUEVO: filtra por cercanía en el tiempo
#
# Devuelve:
# - Lista de candidatos ordenados por cercanía real (distancia H3)


from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

# Modelos
from app.models import UserRole, MatchCandidate, User, Trip

# H3 utils
from app.h3_utils import h3_neighbors
from h3 import grid_distance

# Mock DB
from app.mock_db import get_users_by_h3_and_role, get_trips_by_h3, add_user, add_trip
from app.mock_db import users, trips

from datetime import datetime, timedelta


router = APIRouter(prefix="/match", tags=["matching"])


# ========================================
# REQUEST / RESPONSE
# ========================================

class MatchRequest(BaseModel):
    my_h3_origin: str
    my_h3_destination: str
    my_role: UserRole
    departure_time: datetime  # 🔥 Hora en la que el usuario quiere salir
    time_tolerance_minutes: int = 30  # 🔥 margen permitido (+/- minutos)
    max_h3_distance: int = 1


class MatchResponse(BaseModel):
    candidates: List[MatchCandidate]
    total: int


# ========================================
# ENDPOINT PRINCIPAL
# ========================================

@router.post("/find", response_model=MatchResponse)
def find_candidates(request: MatchRequest):

    # ========================================
    # PASO 1: Expandir radio H3
    # ========================================
    search_origin_h3s = h3_neighbors(request.my_h3_origin, request.max_h3_distance)
    search_dest_h3s = h3_neighbors(request.my_h3_destination, request.max_h3_distance)

    candidates = []

    # ========================================
    # FUNCIÓN AUXILIAR: FILTRO DE TIEMPO
    # ========================================
    def is_time_compatible(trip_time: datetime) -> bool:
        """
        Verifica si el viaje está dentro del rango de tiempo permitido.
        """
        diff_seconds = abs((trip_time - request.departure_time).total_seconds())
        return diff_seconds <= request.time_tolerance_minutes * 60

    # ========================================
    # PASO 2: LÓGICA SEGÚN ROL
    # ========================================

    if request.my_role == UserRole.DRIVER:
        # CONDUCTOR busca PASAJEROS
        passengers = get_users_by_h3_and_role(search_origin_h3s, UserRole.PASSENGER)

        for p in passengers:
            if p.h3_destination in search_dest_h3s:

                distance = grid_distance(request.my_h3_origin, p.h3_origin)

                candidates.append(MatchCandidate(
                    id=p.id,
                    name=p.name,
                    h3_origin=p.h3_origin,
                    h3_destination=p.h3_destination,
                    distance_h3_origin=distance
                ))

    elif request.my_role == UserRole.PASSENGER:
        # PASAJERO busca VIAJES
        matching_trips = get_trips_by_h3(search_origin_h3s, search_dest_h3s)

        for trip in matching_trips:

            # 🔥 FILTRO DE TIEMPO (CLAVE)
            if not is_time_compatible(trip.departure_datetime):
                continue  # Ignora viajes fuera del rango

            driver = next((u for u in users if u.id == trip.driver_id), None)

            if driver:
                distance = grid_distance(request.my_h3_origin, trip.origin_h3)

                candidates.append(MatchCandidate(
                    id=trip.id,
                    name=f"{driver.name} (viaje {trip.available_seats} cupos)",
                    h3_origin=trip.origin_h3,
                    h3_destination=trip.destination_h3,
                    distance_h3_origin=distance
                ))

    # ========================================
    # PASO 3: ORDENAR RESULTADOS
    # ========================================
    candidates.sort(key=lambda x: x.distance_h3_origin)

    # ========================================
    # RESPUESTA FINAL
    # ========================================
    return MatchResponse(
        candidates=candidates,
        total=len(candidates)
    )


# ========================================
# ENDPOINT PARA DATOS DE PRUEBA
# ========================================

@router.post("/add-test-data")
def add_test_data():

    users.clear()
    trips.clear()

    # ========================
    # PASAJEROS
    # ========================
    add_user(User(
        id="p1",
        name="Ana",
        role=UserRole.PASSENGER,
        h3_origin="8966e42d62bffff",
        h3_destination="8966e42d6b3ffff"
    ))

    add_user(User(
        id="p2",
        name="Luis",
        role=UserRole.PASSENGER,
        h3_origin="8966e42d633ffff",
        h3_destination="8966e42d6b3ffff"
    ))

    # ========================
    # CONDUCTOR
    # ========================
    add_user(User(
        id="d1",
        name="Carlos",
        role=UserRole.DRIVER,
        h3_origin="8966e42d62bffff",
        h3_destination="8966e42d6b3ffff"
    ))

    # ========================
    # VIAJE
    # ========================
    add_trip(Trip(
        id="t1",
        driver_id="d1",
        origin_h3="8966e42d62bffff",
        destination_h3="8966e42d6b3ffff",
        departure_datetime=datetime.now() + timedelta(hours=1),
        available_seats=3
    ))

    return {
        "status": "ok",
        "users": len(users),
        "trips": len(trips)
    }