from fastapi import FastAPI  # Framework principal para crear APIs REST
from .config import settings  # Tu configuración con API keys
from .routers import geocode, routes, match  # Importa los routers (grupos de endpoints)

app = FastAPI(title="Co-Movilidad Bogotá API")  # Crea la app FastAPI con título para docs

# Registra TODOS los routers (agrupa endpoints relacionados)
app.include_router(geocode.router)  # Endpoints de mapas/geocoding en /maps/*
app.include_router(routes.router)   # Endpoints de rutas en /router/*
app.include_router(match.router)    # Endpoints de match en /router/*

# Endpoint de salud básico para verificar que el servidor está vivo
@app.get("/health")
def health():
    return {"status": "ok"}

# Endpoint de test para verificar que carga la API key desde .env
@app.get("/config-test")
def config_test():
    return {"maps_key_loaded": bool(settings.google_maps_api_key_backend)} 


# ========================================
# CONFIGURACIÓN CORS
# ========================================
# Permite que el frontend (React) se comunique con este backend.
#
# Sin esto, el navegador bloqueará las peticiones si vienen de otro origen
# (por ejemplo: localhost:3000 → localhost:8000).
#
# IMPORTANTE:
# En producción NO usar "*", sino dominios específicos.
# Importa el middleware de CORS desde FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Agrega el middleware a tu aplicación FastAPI
app.add_middleware(
    CORSMiddleware,

    # Lista de orígenes permitidos (frontend que puede llamar al backend)
    # "*" = permite TODOS (solo para desarrollo ⚠️)
    allow_origins=["*"],

    # Permite enviar cookies, tokens o headers de autenticación
    allow_credentials=True,

    # Métodos HTTP permitidos (GET, POST, PUT, DELETE, etc.)
    # "*" = todos los métodos
    allow_methods=["*"],

    # Headers permitidos en las peticiones (ej: Authorization, Content-Type)
    # "*" = todos los headers
    allow_headers=["*"],
)