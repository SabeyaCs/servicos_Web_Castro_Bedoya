import json
import csv
import os
import time
from datetime import datetime
import requests
import pytest



URL_BASE = "https://appsweb.quantaiot.co"
EQUIPO = "EQUIPO-13-APPSWEB"                         

RUTA_PROVEEDOR_A = "datos/proveedor_a.json"
RUTA_PROVEEDOR_B = "datos/proveedor_b.csv"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUTA_SALIDA_NORMALIZADAS = os.path.join(BASE_DIR, "salida", "normalizadas.json")
RUTA_SALIDA_REPORTE = os.path.join(BASE_DIR, "salida", "reporte.json")


def cargar_datos_proveedor_a(ruta):
    """Carga de manera segura el archivo JSON del Proveedor A."""
    registros = []
    if not os.path.exists(ruta):
        print(f"[ERROR] Archivo no encontrado: {ruta}")
        return registros

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
            items = datos.get("records", []) if isinstance(datos, dict) else datos
            for i, item in enumerate(items):
                registros.append({
                    "id_trazabilidad": f"PROV_A_{item.get('provider_record_id', i)}",
                    "raw": item,
                    "fuente": "proveedor_a"
                })
    except (json.JSONDecodeError, Exception) as e:
        print(f"[ERROR] No se pudo leer {ruta}: {e}")
    
    return registros


def cargar_datos_proveedor_b(ruta):
    """Carga de manera segura el archivo CSV del Proveedor B."""
    registros = []
    if not os.path.exists(ruta):
        print(f"[ERROR] Archivo no encontrado: {ruta}")
        return registros

    try:
        with open(ruta, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=";")
            for i, fila in enumerate(reader):
                rec_code = fila.get("record_code") or f"ROW_{i}"
                registros.append({
                    "id_trazabilidad": f"PROV_B_{rec_code}",
                    "raw": fila,
                    "fuente": "proveedor_b"
                })
    except Exception as e:
        print(f"[ERROR] No se pudo leer {ruta}: {e}")
    
    return registros



def normalizar_registro(item_procesado):
    """
    Transforma un registro crudo a la representación del contrato institucional.
    Retorna el diccionario normalizado o lanza ValueError si hay error de normalización.
    """
    raw = item_procesado["raw"]
    fuente = item_procesado["fuente"]

    try:
        if fuente == "proveedor_a":
            station = raw.get("station", {})
            location = raw.get("location", {})
            measurements = raw.get("measurements", {})

            ciudad = str(station.get("city_name", "")).strip()
            pais = str(station.get("country_code", "")).strip()
            latitud = float(location.get("lat"))
            longitud = float(location.get("lon"))


            temp_f = float(measurements.get("temperature_f"))
            temperatura_c = round((temp_f - 32) / 1.8, 2)

            humedad = float(measurements.get("relative_humidity"))

            viento_ms = float(measurements.get("wind_speed_ms"))
            viento_kmh = round(viento_ms * 3.6, 2)

            fecha_hora = str(raw.get("observed_at", "")).strip()
            origen = "proveedor_a"

        elif fuente == "proveedor_b":
            ciudad = str(raw.get("municipality", "")).strip()
            pais = str(raw.get("country", "")).strip()
            latitud = float(raw.get("latitude_deg"))
            longitud = float(raw.get("longitude_deg"))
            temperatura_c = float(raw.get("temp_celsius"))
            humedad = float(raw.get("humidity_pct"))
            viento_kmh = float(raw.get("wind_kmh"))
            fecha_hora = str(raw.get("measurement_time", "")).strip()
            origen = "proveedor_b"
        
        else:
            raise ValueError(f"Fuente desconocida: {fuente}")


        if not ciudad or not pais or not fecha_hora:
            raise ValueError("Campos de texto obligatorios están vacíos.")

        datetime.fromisoformat(fecha_hora.replace("Z", "+00:00"))

        return {
            "ciudad": ciudad,
            "pais": pais,
            "latitud": latitud,
            "longitud": longitud,
            "temperatura_c": temperatura_c,
            "humedad": humedad,
            "viento_kmh": viento_kmh,
            "fecha_hora": fecha_hora,
            "origen": origen
        }

    except (ValueError, TypeError, KeyError) as e:
        raise ValueError(f"Error de normalización: {e}")



def validar_localmente(normalizado):
    """
    Aplica las reglas de negocio sobre un registro normalizado.
    Retorna (True, None) si es válido o (False, "motivo") si es rechazado localmente.
    """
    if not (-90.0 <= normalizado["latitud"] <= 90.0):
        return False, "Latitud fuera de rango [-90, 90]"
    
    if not (-180.0 <= normalizado["longitud"] <= 180.0):
        return False, "Longitud fuera de rango [-180, 180]"
    
    if not (0.0 <= normalizado["humedad"] <= 100.0):
        return False, "Humedad fuera de rango [0, 100]"
    
    if normalizado["viento_kmh"] < 0:
        return False, "Viento km/h no puede ser negativo"

    if normalizado["origen"] not in ["proveedor_a", "proveedor_b"]:
        return False, "Origen no permitido por el contrato"

    return True, None



def enviar_a_api(registro_normalizado):
    """
    Envía una medición válida a la API según CONTRATO_API.md.
    Maneja hasta 3 intentos en caso de errores 5xx, timeout o fallos de red.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Equipo": EQUIPO  
    }
    endpoint = f"{URL_BASE}/api/v1/mediciones"  
    
    intentos = 0
    max_intentos = 3

    while intentos < max_intentos:
        intentos += 1
        try:
            response = requests.post(
                endpoint, 
                json=registro_normalizado, 
                headers=headers, 
                timeout=5
            )
            code = response.status_code

            if code == 201:
                return "aceptado", code, response.json() if response.text else {}
            elif code in [400, 409, 422]:
                return "rechazado_api", code, response.json() if response.text else {}
            elif 500 <= code <= 599:
                if intentos < max_intentos:
                    time.sleep(1)
                    continue
                return "error_comunicacion", code, {"mensaje": f"Error del servidor HTTP {code}"}
            else:
                return "error_comunicacion", code, {"mensaje": f"Código inesperado: {code}"}

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if intentos < max_intentos:
                time.sleep(1)
                continue
            return "error_comunicacion", None, {"mensaje": f"Fallo de conexión o timeout: {e}"}

    return "error_comunicacion", None, {"mensaje": "Intentos agotados"}


def consultar_registros_guardados():
    """
    Consulta la API mediante GET usando el Query Parameter 'equipo'
    según Sección 4 de CONTRATO_API.md.
    """
    endpoint = f"{URL_BASE}/api/v1/mediciones"
    params = {"equipo": EQUIPO}
    
    try:
        response = requests.get(endpoint, params=params, timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Respuesta inesperada con código {response.status_code}"}
    except Exception as e:
        return {"error": f"No se pudo realizar la consulta GET: {e}"}



def guardar_salidas(normalizadas, reporte):
    """Crea la carpeta salida/ no existente y guarda los archivos JSON correspondientes."""
    os.makedirs("salida", exist_ok=True)
    
    with open(RUTA_SALIDA_NORMALIZADAS, "w", encoding="utf-8") as f:
        json.dump(normalizadas, f, indent=2, ensure_ascii=False)
        
    with open(RUTA_SALIDA_REPORTE, "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)


def ejecutar_integrador():
    print("--- Iniciando Proceso de Integración ---")
    

    raw_a = cargar_datos_proveedor_a(RUTA_PROVEEDOR_A)
    raw_b = cargar_datos_proveedor_b(RUTA_PROVEEDOR_B)
    todos = raw_a + raw_b
    

    reporte = {
        "procesados": len(todos),
        "normalizados_totales": 0,
        "errores_normalizacion": 0,
        "validos_localmente": 0,
        "rechazados_localmente": 0,
        "enviados": 0,
        "aceptados_api": 0,
        "rechazados_api": 0,
        "errores_comunicacion": 0,
        "detalle_trazabilidad": []
    }
    
    normalizadas_para_json = []

    for item in todos:
        trazabilidad_id = item["id_trazabilidad"]
        

        try:
            norm = normalizar_registro(item)
            reporte["normalizados_totales"] += 1
            normalizadas_para_json.append(norm)
        except ValueError as err:
            reporte["errores_normalizacion"] += 1
            reporte["detalle_trazabilidad"].append({
                "id": trazabilidad_id,
                "estado": "error_normalizacion",
                "motivo": str(err)
            })
            continue

        es_valido, motivo_rechazo = validar_localmente(norm)
        if not es_valido:
            reporte["rechazados_localmente"] += 1
            reporte["detalle_trazabilidad"].append({
                "id": trazabilidad_id,
                "estado": "rechazado_localmente",
                "motivo": motivo_rechazo
            })
            continue

        reporte["validos_localmente"] += 1


        reporte["enviados"] += 1
        estado_envio, http_code, res_payload = enviar_a_api(norm)

        if estado_envio == "aceptado":
            reporte["aceptados_api"] += 1
        elif estado_envio == "rechazado_api":
            reporte["rechazados_api"] += 1
        else:
            reporte["errores_comunicacion"] += 1

        reporte["detalle_trazabilidad"].append({
            "id": trazabilidad_id,
            "estado": estado_envio,
            "codigo_http": http_code,
            "respuesta": res_payload
        })


    print("Consultando registros almacenados en la API...")
    reporte["consulta_final_almacenados"] = consultar_registros_guardados()


    guardar_salidas(normalizadas_para_json, reporte)
    
    print("\n--- Integración Finalizada ---")
    print(f"Total procesados: {reporte['procesados']}")
    print(f"Normalizados guardados en salida/: {len(normalizadas_para_json)}")
    print(f"Archivos creados en {RUTA_SALIDA_NORMALIZADAS} y {RUTA_SALIDA_REPORTE}")


if __name__ == "__main__":
    ejecutar_integrador()

