# módulo de configuración


from pydantic_settings import BaseSettings  # Pydantic v2 para manejar .env

class Settings(BaseSettings):
    # Variable de entorno que debe existir en .env
    google_maps_api_key_backend: str

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "root1234"
    db_name: str = "trips_ean"
 
    jwt_secret: str = "super_secreto_ean_2025_cambiame"

    model_config = {
        "env_file": ".env"
        }                     # Archivo .env donde están las variables

# Instancia global para usar en toda la app
settings = Settings()