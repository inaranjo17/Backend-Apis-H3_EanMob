# Backend H3 / Matching — Estado del Desarrollo
**Repositorio:** `inaranjo17/Backend-Apis-H3_EanMob`  
**Responsable:** Isabella (inaranjo17)  
**Última actualización:** 14 de abril de 2026  
**Stack:** Python 3.14 · FastAPI · H3 Uber · aiomysql · MySQL 8.4

---

## Resumen ejecutivo

| HU | Título | Estado |
|---|---|---|
| HU-11 | Coincidencias automáticas de viajes | 🟡 En progreso |
| HU-12 | Listado ordenado por relevancia | 🟡 En progreso |
| HU-13 | Filtro por comunidad | 🔴 Pendiente |
| HU-14 | Coincidencias en tiempo real | 🔴 Pendiente |
| HU-15 | Filtros avanzados | 🟡 Parcial |
| HU-16 | Mapa con ofertantes cercanos | 🔴 Pendiente |
| HU-09 | Advertencia pico y placa | 🔴 Pendiente |
| HU-42 | Config pico y placa admin | 🔴 Pendiente |

---

## ✅ Lo que está hecho

### Infraestructura base
- **Conexión a MySQL real** (`app/db.py`) con pool de conexiones async via `aiomysql`. Reemplaza completamente el `mock_db.py` anterior que usaba datos en memoria.
- **Middleware JWT** (`app/auth.py`) que valida tokens generados por el `users-service` de Justin (Node.js). Usa el mismo `JWT_SECRET` compartido.
- **Config centralizada** (`app/config.py`) con `pydantic_settings` — lee todas las variables desde `.env`.
- **CORS configurado** correctamente antes de los routers en `main.py`.
- **Lifespan de FastAPI** para abrir y cerrar el pool de MySQL al iniciar y detener el servidor.

### HU-11 — Coincidencias automáticas
- `POST /match/find` consulta la tabla `trayectos` en MySQL real.
- Filtros SQL activos: `status='open'`, `available_seats >= min_seats`, tolerancia temporal con `ABS(TIMESTAMPDIFF(SECOND, …)) <= %s`.
- Expansión geoespacial con `grid_disk(k=max_h3_distance)` — por defecto k=1 (7 hexágonos ~174m).
- Auto-exclusión del conductor en sus propios resultados.
- JWT requerido en todos los endpoints protegidos.

### HU-12 — Ordenamiento por relevancia
- Función `calculate_score()` con ponderación: **60% distancia H3 + 40% diferencia horaria**.
- Campo `relevance_score` expuesto en cada candidato de la respuesta.
- Lista ordenada descendente — el mejor match siempre aparece primero.
- Campo `time_diff_minutes` expuesto para que el frontend lo muestre visualmente.

### HU-15 — Filtros avanzados (parcial)
- Parámetro opcional `max_cost` — filtra viajes que superen el presupuesto del pasajero.
- Parámetro opcional `min_seats` — filtra por cupos disponibles mínimos.

### Endpoints existentes y funcionando
| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| POST | `/match/find` | Buscar coincidencias H3 | ✅ JWT |
| POST | `/match/publish-trip` | Publicar viaje con geocoding + H3 | ✅ JWT |
| POST | `/maps/geocode` | Dirección → lat/lng + H3 index | No |
| POST | `/routes/compute` | Ruta → distancia + duración + polyline | No |
| GET | `/health` | Health check | No |

---

## ⏳ Pendiente por implementar

### HU-11 — Detalle faltante
- [ ] Mensaje explícito cuando no hay coincidencias (`"No se encontraron viajes..."`)
- [ ] Integrar verificación de pico y placa al matching (depende de HU-09)
- [ ] Tests de integración contra MySQL real

### HU-12 — Detalle faltante
- [ ] Incorporar **comunidad** al score (depende de HU-13)
- [ ] Incorporar **calificación histórica del conductor** al score (depende de HU-22)
- [ ] Revisar pesos 60/40 con datos reales — hoy son heurísticos

### HU-09 — Pico y Placa (no iniciado)
- [ ] Endpoint `POST /pico-placa/check` — recibe placa + fecha/hora, devuelve si tiene restricción
- [ ] Tabla `pico_placa_calendario` ya creada en BD local
- [ ] Lógica: último dígito de placa → día de la semana → horarios 6-8:30am y 3-7:30pm
- [ ] Integrar al `/match/find` para filtrar conductores restringidos

### HU-42 — Config Pico y Placa admin (no iniciado)
- [ ] Endpoint `PUT /pico-placa/update` para que el admin actualice el calendario
- [ ] Depende de HU-09

### HU-13 — Filtro por comunidad (no iniciado)
- [ ] Parámetro `community_id` ya definido en `MatchRequest` pero sin lógica
- [ ] Necesita JOIN con tabla `usuario_comunidad` para verificar pertenencia
- [ ] Ajustar score para priorizar coincidencias de la misma comunidad

### HU-16 — Mapa ofertantes cercanos (no iniciado)
- [ ] Nuevo endpoint `GET /match/nearby` que devuelve viajes con coordenadas para marcadores
- [ ] Formato de respuesta: lista con `lat`, `lng`, resumen del viaje para el popup del mapa
- [ ] Requiere frontend con Google Maps JS API

### HU-14 — Tiempo real (post-MVP)
- [ ] WebSocket o SSE para notificar al pasajero cuando aparece un viaje nuevo compatible
- [ ] Requiere broker de mensajes o polling con Redis

---

## Estructura del proyecto

```
Backend-Apis-H3_EanMob-main/
├── .env                      ← variables de entorno (NO subir a Git)
├── .env.example              ← plantilla para el equipo
├── requirements.txt          ← dependencias Python
├── app/
│   ├── __init__.py
│   ├── main.py               ← app FastAPI con lifespan
│   ├── config.py             ← configuración con pydantic_settings
│   ├── db.py                 ← pool MySQL async (NUEVO)
│   ├── auth.py               ← middleware JWT (NUEVO)
│   ├── h3_utils.py           ← utilidades H3 (lat_lng_to_h3, h3_neighbors, h3_distance)
│   ├── maps_client.py        ← cliente Google Maps
│   ├── models.py             ← modelos Pydantic base
│   └── routers/
│       ├── geocode.py        ← POST /maps/geocode
│       ├── routes.py         ← POST /routes/compute
│       └── match.py          ← POST /match/find, POST /match/publish-trip
```

---

## Cómo correrlo localmente

### Requisitos previos
- Python 3.11+ instalado
- MySQL 8.x corriendo en `localhost:3306`
- Base de datos `trips_ean` y `users_ean` creadas con las migraciones

### 1. Clonar el repositorio
```bash
git clone https://github.com/inaranjo17/Backend-Apis-H3_EanMob.git
cd Backend-Apis-H3_EanMob
```

### 2. Crear entorno virtual
```bash
# Si tienes Python 3.14 (tiene bug con pip):
python -m venv .venv --without-pip

# Si tienes Python 3.11 / 3.12 / 3.13:
python -m venv .venv
```

### 3. Activar el entorno virtual
```bash
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Si da error de permisos, primero ejecutar:
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Mac / Linux:
source .venv/bin/activate
```

### 4. Instalar dependencias
```bash
pip install fastapi uvicorn h3 googlemaps httpx pydantic-settings python-dotenv aiomysql PyJWT cryptography
```

### 5. Crear el archivo .env
Copia `.env.example` como `.env` y rellena tus valores:
```env
GOOGLE_MAPS_API_KEY_BACKEND=tu_api_key_aqui
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_contraseña_mysql
DB_NAME=trips_ean
JWT_SECRET=super_secreto_ean_2025_cambiame
```

> ⚠️ El `JWT_SECRET` debe ser **exactamente igual** al que usa Justin en su `users-service`.

### 6. Ejecutar las migraciones SQL
En MySQL Workbench o DBeaver, ejecutar en orden:
1. `docs/data-model/migrations/001_initial_schema.sql`
2. `docs/data-model/migrations/002_mvp_extensions.sql`
3. `docs/data-model/migrations/003_requirements_alignment.sql`

### 7. Insertar datos de prueba (opcional)
```sql
USE users_ean;
INSERT INTO usuarios 
  (nombre_completo, correo, rol, password_hash, email_verified, tipo_documento, numero_identificacion, fecha_nacimiento)
VALUES 
  ('Carlos Conductor', 'carlos@universidadean.edu.co', 'Estudiante', '$2b$10$dummy', TRUE, 'CC', '12345678', '1995-01-01'),
  ('Ana Pasajera', 'ana@universidadean.edu.co', 'Estudiante', '$2b$10$dummy', TRUE, 'CC', '87654321', '1997-05-15');

USE trips_ean;
INSERT INTO trayectos 
  (conductor_id, nombre_prestador, origen, destino, hora_inicio, available_seats, status, origin_h3, destination_h3, origin_lat, origin_lng, destination_lat, destination_lng)
VALUES
  (1, 'carlos@universidadean.edu.co', 'Calle 72 con Caracas, Bogotá', 'Universidad EAN, Bogotá',
   '2026-04-20 07:30:00', 3, 'open', '8966e42d62bffff', '8966e42d6b3ffff', 4.6582, -74.0936, 4.6761, -74.0522);
```

### 8. Levantar el servidor
```bash
uvicorn app.main:app --reload
```

Si ves esto, todo está correcto:
```
✅ Conexión a MySQL establecida
INFO: Uvicorn running on http://127.0.0.1:8000
```

### 9. Probar en Swagger
Abre en el navegador: **http://127.0.0.1:8000/docs**

---

## Cómo generar un token JWT de prueba

Mientras el `users-service` de Justin no esté disponible, genera un token local así:

```bash
python -c "
import jwt, datetime
token = jwt.encode(
  {
    'sub': 2,
    'rol': 'Estudiante',
    'correo': 'ana@universidadean.edu.co',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
  },
  'super_secreto_ean_2025_cambiame',
  algorithm='HS256'
)
print(token)
"
```

Copia el token, ve a Swagger → botón **Authorize** → pega el token → dale Authorize.

---

## Cómo probar el endpoint principal

### POST /match/find
```json
{
  "my_h3_origin": "8966e42d62bffff",
  "my_h3_destination": "8966e42d6b3ffff",
  "departure_time": "2026-04-20T07:45:00",
  "time_tolerance_minutes": 30,
  "max_h3_distance": 1
}
```

Respuesta esperada:
```json
{
  "candidates": [
    {
      "trip_id": 1,
      "driver_name": "Carlos Conductor",
      "origin_h3": "8966e42d62bffff",
      "destination_h3": "8966e42d6b3ffff",
      "departure_datetime": "2026-04-20T07:30:00",
      "available_seats": 3,
      "cost_per_passenger": null,
      "distance_h3_origin": 0,
      "time_diff_minutes": 15.0,
      "relevance_score": 0.8
    }
  ],
  "total": 1
}
```

**`distance_h3_origin: 0`** = mismo hexágono (~174m). **`relevance_score: 0.8`** = alta compatibilidad.

---

## Dependencias del equipo

| Necesito de | Qué necesito | Para qué HU |
|---|---|---|
| Justin (darkavenger0528) | BD MySQL compartida en Railway u Oracle VM | Todas |
| Justin | `JWT_SECRET` exacto de su `users-service` | Todas (auth) |
| Justin | Migraciones ejecutadas en BD compartida | HU-11, HU-12 |
| Miguel (mrshelll) | Acceso al repo de arquitectura | Referencia |
| Sara (sarita08-coder) | Coordinación en HU-11, HU-12, HU-09 | HU-11, HU-12, HU-09 |

---

## Decisiones técnicas

| Decisión | Razón |
|---|---|
| H3 resolución 9 (~174m) | Granularidad ideal para barrio/manzana en Bogotá |
| Score 60% distancia + 40% horario | Heurístico inicial — revisar con datos reales |
| `aiomysql` para conexión BD | Compatible con FastAPI async, no bloquea el event loop |
| JWT stateless con secreto compartido | Consistente con el `users-service` de Justin |
| `--without-pip` en venv | Bug conocido de Python 3.14 con `ensurepip` |

---

*Generado el 14 de abril de 2026 — EANMob · Universidad EAN · Bogotá*
