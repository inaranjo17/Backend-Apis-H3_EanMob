# Backend+Apis+H3_EanMob 
Backend API para sistema de co-movilidad usando H3 y Google Maps


# 🚗 Co-Movilidad Bogotá API

Backend para una plataforma de movilidad compartida (carpooling) en Bogotá, usando H3 (indexación geoespacial) para hacer matching inteligente entre conductores y pasajeros.

---

## 📌 ¿Qué hace este proyecto?

Este backend permite:

- 📍 Convertir direcciones → coordenadas → índice H3
- 🗺️ Calcular rutas usando Google Maps API
- 🤝 Hacer matching entre usuarios basado en:
  - Cercanía geográfica (hexágonos H3)
  - Destino similar
  - Compatibilidad de horario
- 🚦 Validar pico y placa urbano y regional para advertencias no bloqueantes al publicar viajes

---

## 🧱 Arquitectura del proyecto


app/
├── routers/
│ ├── geocode.py # Endpoint 1 (dirección → H3)
│ ├── routes.py # Endpoint 2 (rutas)
│ ├── match.py # Endpoint 3 (matching) (simulada parcialmente mientras se integra la BD real)
│ ├── pico_placa.py # Endpoint 4 (pico y placa urbano/regional)
│
├── models.py # Modelos de datos (User, Trip, etc.)
├── mock_db.py # Base de datos en memoria (simulada mientras se integra la BD real)
├── h3_utils.py # Funciones H3
├── maps_client.py # Cliente Google Maps
├── config.py # Configuración (.env)
└── main.py # Entrada principal FastAPI


---

## ⚙️ Tecnologías usadas

- FastAPI
- Python
- H3 (Uber)
- Google Maps API
- httpx
- Pydantic

---

## 🚀 Cómo correr el proyecto

### 1. Clonar el repositorio

```bash
git clone https://github.com/inaranjo17/Backend-Apis-H3_EanMob.git
cd TU-REPO
2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate   # Windows
3. Instalar dependencias
pip install -r requirements.txt

4. Crear tablas de pico y placa

Ejecutar `app/seed/pico_placa_seed.sql` sobre la base usada por el servicio FastAPI
(`trips_ean` por defecto). Si las tablas todavía no existen, el endpoint `/check`
usa la regla urbana por defecto de Bogotá como respaldo y deja eventos regionales vacíos.

4. Configurar variables de entorno

Crear un archivo .env en la raíz del proyecto:

GOOGLE_MAPS_API_KEY_BACKEND=tu_api_key (si se necesita me la pueden pedir. por temas de seguridad no es recomendable subirlo aqui en el repositorio)

⚠️ IMPORTANTE:

No subi .env a GitHub. Cada quien debe crear este archivo

5. Ejecutar servidor
uvicorn app.main:app --reload

Para exponer Pico y Placa como servicio independiente en el puerto definido por arquitectura:
uvicorn app.pico_placa_main:app --reload --port 8002
6. Documentación automática

Una vez corriendo:

Swagger UI:
http://127.0.0.1:8000/docs

Redoc:
http://127.0.0.1:8000/redoc

📡 Endpoints
📍 1. Geocoding + H3

POST /maps/geocode

Convierte una dirección a:

latitud

longitud

índice H3

Request:
{
  "address": "Cra 7 #72-41, Bogotá"
}
Response:
{
  "lat": 4.65,
  "lng": -74.05,
  "formatted_address": "...",
  "h3_index": "8966e42d62bffff"
}
🗺️ 2. Rutas

POST /routes/compute

Devuelve:

distancia (metros)

duración (segundos)

polyline

🤝 3. Matching

POST /match/find

Encuentra candidatos según:

ubicación (H3)

destino

horario

Request:
{
  "my_h3_origin": "8966e42d62bffff",
  "my_h3_destination": "8966e42d6b3ffff",
  "my_role": "passenger",
  "departure_time": "2026-03-20T10:00:00",
  "time_tolerance_minutes": 30
}
🧪 Datos de prueba

POST /match/add-test-data

Carga usuarios y viajes de ejemplo.

🚦 4. Pico y Placa

POST /api/v1/pico-placa/check

Verifica si una placa tiene restricción urbana o regional para una fecha/hora.
La respuesta está pensada para advertir, no para bloquear la publicación del viaje.
Para Bogotá, el motor interpreta la regla oficial de circulación: en días impares
pueden circular placas terminadas en `1,2,3,4,5` y en días pares pueden circular
placas terminadas en `6,7,8,9,0`.

Request:
{
  "plate": "ABC128",
  "datetime": "2026-05-15T10:00:00-05:00",
  "vehicle_type": "Carro",
  "city": "BOGOTA",
  "route_context": {
    "direction": "inbound",
    "corridor_id": "autopista-norte"
  }
}

Response:
{
  "success": true,
  "data": {
    "restricted": true,
    "urban_restricted": true,
    "regional_restricted": false,
    "regional_possible": false,
    "plate_last_digit": "8",
    "warnings": [
      {
        "type": "urban",
        "severity": "confirmed",
        "message": "Vehicle is restricted by Bogota urban pico y placa."
      }
    ]
  },
  "error": null,
  "message": "Verificacion completada"
}

GET /api/v1/pico-placa/rules

Lista fuentes activas, reglas urbanas activas y eventos regionales para inspección.

POST /api/v1/pico-placa/sync

Registra una corrida de sincronización. En MVP queda como no-op seguro porque no hay una API JSON oficial estable configurada; el servicio usa reglas cacheadas/sembradas y puede incorporar fuentes oficiales cuando estén disponibles.

El Trips Service consume este endpoint con `PICO_PLACA_SERVICE_URL`, por defecto `http://localhost:8002`.

🔐 Seguridad

API keys se manejan con .env

No se suben credenciales al repositorio

Se recomienda restringir API keys en Google Cloud
