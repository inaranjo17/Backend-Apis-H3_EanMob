#################### ENDPOINT 1 ###################
# geocodificar una dirección de Bogotá 

import googlemaps
from .config import settings # Importa las settings donde está tu API key

#Crea el cliente con mi API key backend
try:
    gmaps_client = googlemaps.Client(key=settings.google_maps_api_key_backend)
except Exception as e:
    raise RuntimeError(f"Google Maps init error: {e}")