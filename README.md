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

---

## 🧱 Arquitectura del proyecto


app/
├── routers/
│ ├── geocode.py # Endpoint 1 (dirección → H3)
│ ├── routes.py # Endpoint 2 (rutas)
│ ├── match.py # Endpoint 3 (matching) (simulada parcialmente mientras se integra la BD real)
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
4. Configurar variables de entorno

Crear un archivo .env en la raíz del proyecto:

GOOGLE_MAPS_API_KEY_BACKEND=tu_api_key (si se necesita me la pueden pedir. por temas de seguridad no es recomendable subirlo aqui en el repositorio)

⚠️ IMPORTANTE:

No subi .env a GitHub. Cada quien debe crear este archivo

5. Ejecutar servidor
uvicorn app.main:app --reload
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

🔐 Seguridad

API keys se manejan con .env

No se suben credenciales al repositorio

Se recomienda restringir API keys en Google Cloud
