#################### ENDPOINT 1 ###################
# geocodificar una dirección de Bogotá 
# Convertir dirección de Bogotá → lat/lng usando Geocoding API.
# Convertir lat/lng → H3 (resolución 9)


from fastapi import APIRouter, HTTPException  # Router para agrupar endpoints + manejo de errores
from pydantic import BaseModel  # Modelos de entrada/salida con validación automática
from ..maps_client import gmaps_client  # Cliente Google Maps
from ..h3_utils import lat_lng_to_h3  # Utilidades H3

router = APIRouter(prefix="/maps", tags=["maps"])  # Todos los endpoints empiezan en /maps/*

# Modelo de entrada: qué recibe el endpoint
class GeocodeRequest(BaseModel):
    address: str

# Modelo de salida: qué devuelve (con H3 incluido)
class GeocodeH3Response(BaseModel):
    lat: float
    lng: float
    formatted_address: str
    h3_index: str

@router.post("/geocode", response_model=GeocodeH3Response)
def geocode_address(payload: GeocodeRequest):  # payload se valida automáticamente
    # Llama a Google Geocoding con región Colombia ("co")
    geocode_result = gmaps_client.geocode(payload.address, region="co")
    if not geocode_result:
        raise HTTPException(status_code=404, detail="Dirección no encontrada")
    
    # Extrae coordenadas del primer resultado
    loc = geocode_result[0]["geometry"]["location"]
    lat = loc["lat"]
    lng = loc["lng"]
    # Convierte coordenadas a índice H3
    h3_index = lat_lng_to_h3(lat, lng)

    return GeocodeH3Response(
        lat=lat,
        lng=lng,
        formatted_address=geocode_result[0]["formatted_address"],
        h3_index=h3_index,
    )