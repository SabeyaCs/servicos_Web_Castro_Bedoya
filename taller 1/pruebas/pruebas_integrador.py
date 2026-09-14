import pytest
import sys
import os

# Permite localizar el archivo cliente_Integrador.py en la raíz del proyecto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cliente_Integrador import normalizar_registro, validar_localmente


# 1. Transformación correcta (Proveedor B)
def test_transformacion_correcta_proveedor_b():
    item_raw = {
        "id_trazabilidad": "PROV_B_001",
        "fuente": "proveedor_b",
        "raw": {
            "record_code": "B-101",
            "municipality": "Medellin",
            "country": "CO",
            "latitude_deg": "6.2442",
            "longitude_deg": "-75.5812",
            "temp_celsius": "22.5",
            "humidity_pct": "65.0",
            "wind_kmh": "12.0",
            "measurement_time": "2026-09-09T15:00:00-05:00",
            "origin_code": "proveedor_b"
        }
    }
    resultado = normalizar_registro(item_raw)
    assert resultado["ciudad"] == "Medellin"


# 2. Conversión de unidades (Proveedor A)
def test_conversion_unidades_proveedor_a():
    item_raw = {
        "id_trazabilidad": "PROV_A_001",
        "fuente": "proveedor_a",
        "raw": {
            "provider_record_id": "A-001",
            "station": {"city_name": "Bogota", "country_code": "CO"},
            "location": {"lat": 4.6097, "lon": -74.0817},
            "measurements": {
                "temperature_f": 68.0,
                "relative_humidity": 50.0,
                "wind_speed_ms": 10.0
            },
            "observed_at": "2026-09-09T12:00:00-05:00",
            "source": "weather_provider_a"
        }
    }
    resultado = normalizar_registro(item_raw)
    assert resultado["temperatura_c"] == 20.0
    assert resultado["viento_kmh"] == 36.0


# 3. Registro válido (Validación Local)
def test_registro_valido_localmente():
    normalizado = {
        "ciudad": "Cali",
        "pais": "CO",
        "latitud": 3.4516,
        "longitud": -76.5320,
        "temperatura_c": 25.0,
        "humedad": 70.0,
        "viento_kmh": 15.0,
        "fecha_hora": "2026-09-09T10:00:00-05:00",
        "origen": "proveedor_a"
    }
    es_valido, motivo = validar_localmente(normalizado)
    assert es_valido is True


# 4. Registro inválido (Humedad fuera de rango)
def test_registro_invalido_humedad_fuera_de_rango():
    normalizado = {
        "ciudad": "Cartagena",
        "pais": "CO",
        "latitud": 10.3997,
        "longitud": -75.5144,
        "temperatura_c": 30.0,
        "humedad": 150.0,
        "viento_kmh": 10.0,
        "fecha_hora": "2026-09-09T10:00:00-05:00",
        "origen": "proveedor_b"
    }
    es_valido, motivo = validar_localmente(normalizado)
    assert es_valido is False


# 5. Caso límite (Latitud exacta en -90.0)
def test_caso_limite_latitud_exacta():
    normalizado = {
        "ciudad": "Polo Sur",
        "pais": "AQ",
        "latitud": -90.0,
        "longitud": 0.0,
        "temperatura_c": -35.0,
        "humedad": 10.0,
        "viento_kmh": 5.0,
        "fecha_hora": "2026-09-09T00:00:00Z",
        "origen": "proveedor_a"
    }
    es_valido, motivo = validar_localmente(normalizado)
    assert es_valido is True