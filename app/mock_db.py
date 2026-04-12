from typing import List
# Importa los modelos que acabamos de definir
from app.models import User, Trip, UserRole
from app.models import TripStatus

# ========================================
# SIMULACIÓN DE BASE DE DATOS EN MEMORIA (reemplazar con base de datos real (PostgreSQL))
# ========================================
# Lista que simula tabla "users" (se pierde al reiniciar servidor)
users: List[User] = []          # Todos los usuarios registrados

# Lista que simula tabla "trips" 
trips: List[Trip] = []          # Todos los viajes publicados

# ========================================
# FUNCIONES CRUD SIMULADAS
# ========================================
def add_user(user: User):
    """Agrega un usuario a la "base de datos"""
    users.append(user)              # Solo lo mete en la lista

def add_trip(trip: Trip):
    """Publica un nuevo viaje"""
    trips.append(trip)              # Lo mete en la lista de viajes

def get_users_by_h3_and_role(h3_indexes: List[str], role: UserRole) -> List[User]:
    """
    Busca usuarios en H3 específicos Y con rol específico
    Ejemplo: busca pasajeros en hexágonos cercanos
    """
    # Filtra: solo usuarios cuyo h3_origin está en la lista Y tienen el rol pedido
    return [u for u in users if u.role == role and u.h3_origin in h3_indexes]

def get_trips_by_h3(h3_origin_indexes: List[str], h3_dest_indexes: List[str]) -> List[Trip]:
    """
    Busca viajes cuyos origen Y destino coincidan con los hexágonos pedidos
    """
    # Filtra viajes abiertos que salgan de los H3 origen Y vayan a los H3 destino
    return [t for t in trips 
            if t.origin_h3 in h3_origin_indexes          # Sale de un H3 cercano
            and t.destination_h3 in h3_dest_indexes       # Va a un H3 cercano
            and t.status == TripStatus.OPEN]                      # Solo viajes disponibles
