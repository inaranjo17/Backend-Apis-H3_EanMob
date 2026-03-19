################### ENDPOINT 2 ################
#Endpoint /routes/compute - Modelo de request/response
#endpoint en FastAPI que reciba origen y destino (lat/lng) y devuelva: Distancia (metros), Duración (segundos), Polyline codificada (para que el frontend pinte la línea en el mapa)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx  # Cliente HTTP async para llamar a Google Routes API
from ..config import settings

router = APIRouter(prefix="/routes", tags=["routes"])

# URL oficial de Google Routes API v2
ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

# Modelo para coordenadas (con descripción para Swagger)
class LatLng(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

# Entrada: origen y destino
class RouteRequest(BaseModel):
    origin: LatLng
    destination: LatLng

# Salida: datos clave para pintar ruta en frontend
class RouteResponse(BaseModel):
    distance_meters: int
    duration_seconds: int
    polyline: str  # Cadena codificada para dibujar en Maps JS

@router.post("/compute", response_model=RouteResponse)
async def compute_route(body: RouteRequest):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.google_maps_api_key_backend,
        # Solo pide estos campos para ahorrar quota y datos
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline",
    }

    # Payload JSON exacto que espera Routes API
    payload = {
        "origin": {
            "location": {
                "latLng": {
                    "latitude": body.origin.lat,
                    "longitude": body.origin.lng,
                }
            }
        },
        "destination": {
            "location": {
                "latLng": {
                    "latitude": body.destination.lat,
                    "longitude": body.destination.lng,
                }
            }
        },
        "travelMode": "DRIVE",  # Modo carro (puedes cambiar a WALK, etc.)
    }

    # Llamada async a Google con timeout de 10s
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(ROUTES_API_URL, json=payload, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Routes API error: {resp.text}",
        )

    data = resp.json()
    if not data.get("routes"):
        raise HTTPException(status_code=404, detail="No se encontró ruta")

    route = data["routes"][0]  # Primera ruta encontrada
    distance_meters = route.get("distanceMeters", 0)
    duration_str = route.get("duration", "0s")  # Formato "165s"
    duration_seconds = int(duration_str.replace("s", "")) if duration_str.endswith("s") else 0
    polyline = route["polyline"]["encodedPolyline"]  # Para pintar en frontend

    return RouteResponse(
        distance_meters=distance_meters,
        duration_seconds=duration_seconds,
        polyline=polyline,
    )