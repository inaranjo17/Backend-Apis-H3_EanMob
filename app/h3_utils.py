# ========================================
# SERVICIO H3 (INDEXACIÓN GEOESPACIAL)
# ========================================
#
# Este módulo se encarga de:
# - Convertir coordenadas (lat/lng) a índices H3
# - Obtener hexágonos vecinos (búsqueda por proximidad)
# - Calcular distancia entre celdas H3 (clave para matching inteligente)
#
# H3 es un sistema desarrollado por Uber que divide el mundo
# en hexágonos jerárquicos → ideal para sistemas de movilidad


import h3  # Librería oficial H3


# ========================================
# CONFIGURACIÓN
# ========================================
# Resolución H3:
# 9 ≈ ~150-200 metros (nivel barrio/manzana en Bogotá)
# Puedes ajustar:
# - 8 → más amplio (~500m)
# - 10 → más preciso (~50m)
H3_RESOLUTION = 9  


# ========================================
# CONVERSIÓN: LAT/LNG → H3
# ========================================
def lat_lng_to_h3(lat: float, lng: float) -> str:
    """
    Convierte coordenadas geográficas a índice H3 único.

    Args:
        lat (float): Latitud
        lng (float): Longitud

    Returns:
        str: Índice H3 (string)
    """
    return h3.latlng_to_cell(lat, lng, H3_RESOLUTION)


# ========================================
# VECINOS H3 (BÚSQUEDA POR RADIO)
# ========================================
def h3_neighbors(h3_index: str, k: int = 1) -> list[str]:
    """
    Devuelve los hexágonos vecinos dentro de un radio k.

    IMPORTANTE:
    - grid_disk YA incluye el hexágono central
    - k = 1 → hexágono + vecinos inmediatos (~7 celdas)
    - k = 2 → vecinos de vecinos (~19 celdas)

    Args:
        h3_index (str): Índice H3 central
        k (int): Radio de búsqueda

    Returns:
        list[str]: Lista de índices H3
    """
    return list(h3.grid_disk(h3_index, k))


# ========================================
# DISTANCIA ENTRE HEXÁGONOS (CLAVE)
# ========================================
def h3_distance(h3_a: str, h3_b: str) -> int:
    """
    Calcula la distancia entre dos celdas H3.

    Esto es FUNDAMENTAL para el matching:
    - 0 → mismo hexágono
    - 1 → vecino inmediato
    - 2+ → más lejos

    Args:
        h3_a (str): H3 origen
        h3_b (str): H3 destino

    Returns:
        int: Distancia en pasos hexagonales
    """
    return h3.grid_distance(h3_a, h3_b)