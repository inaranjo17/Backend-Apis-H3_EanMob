from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Rol del usuario: driver or passenger
class UserRole(Enum):
    DRIVER = "driver"
    PASSENGER = "passenger"

# Usuario simplificado (sin auth por ahora)
class User(BaseModel):
    id: str = Field(..., description="ID único del usuario")
    name: str
    role: UserRole
    h3_origin: str  # H3 de origen/residencia
    h3_destination: str  # H3 de destino/trabajo

#Status viaje
class TripStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

    
# Viaje que ofrece/crea un conductor
class Trip(BaseModel):
    id: str
    driver_id: str
    origin_h3: str
    destination_h3: str
    departure_datetime: datetime  # cuándo sale
    available_seats: int
    status: TripStatus = TripStatus.OPEN  # open, in_progress, completed


# Respuesta del matching: candidatos encontrados
class MatchCandidate(BaseModel):
    id: str
    name: str
    h3_origin: str
    h3_destination: str
    distance_h3_origin: int  # distancia H3 del origen (0=mismo hex, 1=vecino...)