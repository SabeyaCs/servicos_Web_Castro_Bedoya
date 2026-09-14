 Informe de Análisis Técnico e Integración de Proveedores
 Santiago Galvis Galvis
 Samuel Castro Bedoya

 1. Diferencias encontradas entre los contratos de los proveedores
Durante la integración de los flujos de datos provenientes de los distintos proveedores, se identificaron divergencias estructurales y de formato significativas en sus contratos de datos (esquemas de entrada):
Formato de Fecha y Hora: El Proveedor A utilizaba marcas de tiempo compatibles o cercanas al estándar ISO 8601, mientras que el Proveedor B entregaba las fechas en un formato localizado (DD/MM/YYYY HH:MM), lo cual impedía el parseo directo sin una transformación previa.
Nomenclatura y Tipado de Campos: Se encontraron discrepancias en el nombramiento de las variables meteorológicas y de ubicación, así como variaciones en el tipado (valores numéricos representados como cadenas de texto, presencia de nulos como cadenas vacías '' o identificadores 'N/A').
Estructura de Identificadores: Los códigos de registro y estaciones presentaban prefijos y delimitadores propios por cada fuente (e.g., PROV_A_A-XXXX frente a esquemas alternativos del Proveedor B).

2. Transformaciones necesarias
Para lograr un esquema unificado compatible con el modelo de dominio central y la API de destino, se implementaron las siguientes transformaciones automatizadas:
Normalización Temporal: Conversión de cadenas de fecha y hora localizadas a objetos de fecha/hora estándar con soporte ISO format.
Limpieza y Conversión de Tipos: Manejo defensivo de valores atípicos (remplazo de 'N/A', espacios en blanco o valores nulos a tipos numéricos flotantes o enteros según correspondiera).
Validación de Integridad Textual: Verificación de que los campos de texto obligatorios no estuvieran vacíos antes de proceder con el procesamiento.

3. Tipos de errores encontrados antes de enviar información
Los errores detectados en la fase previa al envío se dividieron en dos grandes categorías según el informe de ejecución:
Errores de Normalización (206 casos): Fallos ocurridos durante la lectura y conversión inicial de los datos crudos. Ejemplos destacados incluyen:
Invalid isoformat string: Cadenas con formatos de fecha inválidos o corrompidos (e.g., '01/09/2026 06:00' o fechas anómalas como '31/13/2026 28:75').
Error de conversión numérica: Intentos fallidos de convertir cadenas no numéricas a flotantes (e.g., could not convert string to float: 'N/A' o 'error').
Campos obligatorios vacíos: Ausencia de información textual indispensable en el registro.
Errores de Validación Local (4 casos): Registros que lograron normalizarse sintácticamente pero infringieron las reglas de negocio y restricciones físicas locales:
Humedad fuera del rango permitido [0, 100] (e.g., PROV_A_A-0015).
Latitud fuera de rango [-90, 90] y Longitud fuera de rango [-180, 180] (e.g., PROV_A_A-0031, PROV_A_A-0175).
Valores físicos negativos en magnitudes que no lo permiten, como velocidad del viento en km/h (e.g., PROV_A_A-0088).

4. Diferencias entre validación local y validación del servidor
Dimensión
Validación Local
Validación del Servidor (API)
 
Objetivo
Filtrar datos corruptos, tipados incorrectos y violaciones de rangos físicos elementales antes de consumir recursos de red.
Garantizar la consistencia transaccional global, unicidad de registros y reglas de negocio a nivel de base de datos corporativa.
Alcance
Estructural, sintáctico y restricciones de dominio acotadas (rangos geográficos, límites físicos).
Restricciones de unicidad, llaves primarias, estado histórico y dependencias cruzadas.
Resultado en Ejecución
Rechazó 4 registros por lógica de negocio local y detuvo 206 en normalización.
Rechazó 190 registros enviados devolviendo un código HTTP 409 debido a que las mediciones ya existían en el sistema.

5. Decisión de implementación más importante y por qué
La decisión de implementación más crítica fue la separación estricta entre la capa de normalización/validación local y la capa de comunicación con la API, acompañada de un sistema robusto de trazabilidad detallada por registro.
¿Por qué? Aislar la validación local permitió interceptar errores masivos de formato (como los 206 errores de normalización y los rechazos por rangos físicos) sin saturar la red ni generar llamadas inútiles al servidor. Asimismo, el registro exhaustivo de trazabilidad permitió identificar con precisión milimétrica el motivo exacto del fallo de cada ítem (por ejemplo, distinguiendo entre un error HTTP 409 de conflicto por duplicidad en el servidor y un error de rango local), facilitando la auditoría y depuración del pipeline de datos.

6. Evidencia resumida de una ejecución real del programa
A continuación se presenta el resumen consolidado de la ejecución (basado en el reporte reporte_3.json):
Cantidad total de registros procesados: 400
Cantidad normalizada (éxito sintáctico): 194
Cantidad con errores de normalización: 206
Cantidad rechazada localmente (reglas de negocio): 4
Cantidad válida enviada a la API: 190
Cantidad aceptada por la API: 0
Cantidad rechazada por la API: 190
Errores de comunicación de red: 0
Casos de Ejemplo de Error y Respuesta de la API
Caso de error de normalización o validación local (Ejemplo 1): Registro PROV_A_A-0015 con estado rechazado_localmente debido al motivo: "Humedad fuera de rango [0, 100]".
Caso de error de normalización (Ejemplo 2): Registro PROV_A_A-0174 con estado error_normalizacion debido al motivo: "Invalid isoformat string: '09-XX-2026 25:61'".
Respuesta recibida desde la API (Ejemplo de rechazo HTTP 409):
{
  "id": "PROV_A_A-0001",
  "estado": "rechazado_api",
  "codigo_http": 409,
  "respuesta": {
    "detail": "La medición ya existe"
  }
}


Resultado de la consulta final mediante GET: El sistema completó el barrido de los 400 registros de entrada, persistiendo la traza completa de auditoría en los reportes de salida sin caídas por excepciones no controladas gracias al manejo defensivo implementado.