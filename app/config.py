# módulo de configuración


from pydantic_settings import BaseSettings  # Pydantic v2 para manejar .env

class Settings(BaseSettings):
    # Variable de entorno que debe existir en .env
    google_maps_api_key_backend: str

    model_config = {
        "env_file": ".env"
        }                     # Archivo .env donde están las variables

# Instancia global para usar en toda la app
settings = Settings()