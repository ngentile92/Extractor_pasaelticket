# invoice_extractor/utils/normalization.py
"""
🧹 Módulo de Normalización de Datos

Este módulo contiene todas las funciones de limpieza y normalización
de datos extraídos de comprobantes argentinos.

Referencia: CORRECCIONES_POST_EXTRACCION.md - Sección de Normalización
"""

import re
from typing import Any, Optional, Union, List, Dict
from decimal import Decimal, InvalidOperation
from datetime import datetime, date


# =============================================================================
# 1. CONVERSIÓN DE VALORES NULLISH
# =============================================================================

NULLISH_VALUES = [
    None, "", " ", ".", "-", "_", "N/A", "n/a", "null", "NULL", 
    "None", "none", "undefined", "NaN", "nan", "--", "..", "...",
    "___", "---", "/", "//", "\\", "\\\\", "*", "**", "***"
]


def is_nullish(value: Any) -> bool:
    """
    🔍 Verificar si un valor es considerado 'nullish'
    
    Args:
        value: Valor a verificar
    
    Returns:
        True si el valor es nullish, False en caso contrario
    
    Examples:
        >>> is_nullish(None)
        True
        >>> is_nullish(".")
        True
        >>> is_nullish("VALID TEXT")
        False
    """
    if value is None:
        return True
    
    if isinstance(value, str):
        # Eliminar espacios y verificar si está en lista nullish
        stripped = value.strip()
        return stripped == "" or stripped in NULLISH_VALUES
    
    return False


def convert_nullish_to_none(value: Any) -> Optional[Any]:
    """
    🔄 Convertir valores nullish a None
    
    Args:
        value: Valor a convertir
    
    Returns:
        None si es nullish, el valor original en caso contrario
    
    Examples:
        >>> convert_nullish_to_none(".")
        None
        >>> convert_nullish_to_none("Valid Text")
        'Valid Text'
    """
    return None if is_nullish(value) else value


def clean_nullish_recursive(data: Any) -> Any:
    """
    🧹 Limpiar valores nullish recursivamente en diccionarios y listas
    
    Args:
        data: Diccionario, lista o valor a limpiar
    
    Returns:
        Datos con valores nullish convertidos a None
    
    Examples:
        >>> clean_nullish_recursive({"name": ".", "age": 25})
        {'name': None, 'age': 25}
    """
    if isinstance(data, dict):
        return {k: clean_nullish_recursive(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nullish_recursive(item) for item in data]
    else:
        return convert_nullish_to_none(data)


# =============================================================================
# 2. NORMALIZACIÓN DE TEXTO
# =============================================================================

def normalize_text(text: Optional[str], to_upper: bool = True) -> Optional[str]:
    """
    🔠 Normalizar texto: trim, mayúsculas, espacios múltiples
    
    Args:
        text: Texto a normalizar
        to_upper: Si True, convierte a mayúsculas
    
    Returns:
        Texto normalizado o None si es nullish
    
    Examples:
        >>> normalize_text("  hola  mundo  ")
        'HOLA MUNDO'
        >>> normalize_text("  hola  ", to_upper=False)
        'hola'
    """
    if is_nullish(text):
        return None
    
    if not isinstance(text, str):
        text = str(text)
    
    # Eliminar espacios al inicio/final
    normalized = text.strip()
    
    # Reemplazar múltiples espacios por uno solo
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Convertir a mayúsculas si se solicita
    if to_upper:
        normalized = normalized.upper()
    
    # Verificar nuevamente si después de limpiar quedó nullish
    return None if is_nullish(normalized) else normalized


def normalize_cuit(cuit: Optional[str]) -> Optional[str]:
    """
    🔢 Normalizar CUIT al formato XX-XXXXXXXX-X
    
    Args:
        cuit: CUIT a normalizar (puede incluir guiones o no)
    
    Returns:
        CUIT formateado o None si es inválido
    
    Examples:
        >>> normalize_cuit("30525390085")
        '30-52539008-5'
        >>> normalize_cuit("30-52539008-5")
        '30-52539008-5'
        >>> normalize_cuit("invalid")
        None
    """
    if is_nullish(cuit):
        return None
    
    # Eliminar todo excepto números
    cuit_clean = re.sub(r'\D', '', str(cuit))
    
    # Verificar que tenga 11 dígitos
    if len(cuit_clean) != 11:
        return None
    
    # Formatear: XX-XXXXXXXX-X
    return f"{cuit_clean[:2]}-{cuit_clean[2:10]}-{cuit_clean[10]}"


def normalize_provincia(provincia: Optional[str]) -> Optional[str]:
    """
    🗺️ Normalizar nombre de provincia
    
    Args:
        provincia: Nombre de provincia a normalizar
    
    Returns:
        Nombre de provincia normalizado
    
    Examples:
        >>> normalize_provincia("cap fed")
        'CIUDAD AUTÓNOMA DE BUENOS AIRES'
        >>> normalize_provincia("buenos aires")
        'BUENOS AIRES'
    """
    if is_nullish(provincia):
        return None
    
    provincia_norm = normalize_text(provincia, to_upper=True)
    if not provincia_norm:
        return None
    
    # Mapeos de nombres comunes
    PROVINCIA_MAPPINGS = {
        "CABA": "CIUDAD AUTÓNOMA DE BUENOS AIRES",
        "C.A.B.A.": "CIUDAD AUTÓNOMA DE BUENOS AIRES",
        "CAP FED": "CIUDAD AUTÓNOMA DE BUENOS AIRES",
        "CAPITAL FEDERAL": "CIUDAD AUTÓNOMA DE BUENOS AIRES",
        "BUENOS AIRES": "BUENOS AIRES",
        "BA": "BUENOS AIRES",
        "CORDOBA": "CÓRDOBA",
        "SANTA FE": "SANTA FE",
        "MENDOZA": "MENDOZA",
        "TUCUMAN": "TUCUMÁN",
        "ENTRE RIOS": "ENTRE RÍOS",
        "SALTA": "SALTA",
        "CORRIENTES": "CORRIENTES",
        "MISIONES": "MISIONES",
        "SAN JUAN": "SAN JUAN",
        "JUJUY": "JUJUY",
        "RIO NEGRO": "RÍO NEGRO",
        "CHUBUT": "CHUBUT",
        "FORMOSA": "FORMOSA",
        "NEUQUEN": "NEUQUÉN",
        "CHACO": "CHACO",
        "SAN LUIS": "SAN LUIS",
        "CATAMARCA": "CATAMARCA",
        "LA RIOJA": "LA RIOJA",
        "LA PAMPA": "LA PAMPA",
        "SANTIAGO DEL ESTERO": "SANTIAGO DEL ESTERO",
        "TIERRA DEL FUEGO": "TIERRA DEL FUEGO",
        "SANTA CRUZ": "SANTA CRUZ"
    }
    
    return PROVINCIA_MAPPINGS.get(provincia_norm, provincia_norm)


def normalize_condicion_iva(condicion: Optional[str]) -> Optional[str]:
    """
    📋 Normalizar condición frente al IVA
    
    Args:
        condicion: Condición IVA a normalizar
    
    Returns:
        Condición IVA normalizada
    
    Examples:
        >>> normalize_condicion_iva("resp insc")
        'RESPONSABLE INSCRIPTO'
        >>> normalize_condicion_iva("monotributo")
        'MONOTRIBUTO'
    """
    if is_nullish(condicion):
        return None
    
    condicion_norm = normalize_text(condicion, to_upper=True)
    if not condicion_norm:
        return None
    
    # Mapeos de condiciones IVA
    CONDICION_IVA_MAPPINGS = {
        "RESP INSC": "RESPONSABLE INSCRIPTO",
        "RESP. INSC": "RESPONSABLE INSCRIPTO",
        "RESP INSCRIPTO": "RESPONSABLE INSCRIPTO",
        "RESP. INSCRIPTO": "RESPONSABLE INSCRIPTO",
        "RESPONSABLE INSCRIPTO": "RESPONSABLE INSCRIPTO",
        "IVA RESPONSABLE INSCRIPTO": "RESPONSABLE INSCRIPTO",
        "IVA RESP INSC": "RESPONSABLE INSCRIPTO",
        "MONOTRIBUTO": "MONOTRIBUTO",
        "MONO": "MONOTRIBUTO",
        "CONSUMIDOR FINAL": "CONSUMIDOR FINAL",
        "CONS FINAL": "CONSUMIDOR FINAL",
        "CF": "CONSUMIDOR FINAL",
        "EXENTO": "EXENTO",
        "NO RESPONSABLE": "NO RESPONSABLE",
        "NO RESP": "NO RESPONSABLE"
    }
    
    return CONDICION_IVA_MAPPINGS.get(condicion_norm, condicion_norm)


# =============================================================================
# 3. NORMALIZACIÓN DE FECHAS
# =============================================================================

def normalize_date(date_value: Any, output_format: str = "%Y-%m-%d") -> Optional[str]:
    """
    📅 Normalizar fecha al formato especificado
    
    Args:
        date_value: Fecha en cualquier formato (str, date, datetime)
        output_format: Formato de salida (default: "%Y-%m-%d" para ISO)
                      Usar "%d/%m/%Y" para formato argentino DD/MM/YYYY
    
    Returns:
        Fecha en formato especificado o None si es inválida
    
    Examples:
        >>> normalize_date("16/10/2023")
        '2023-10-16'
        >>> normalize_date("2023-10-16", "%d/%m/%Y")
        '16/10/2023'
    """
    if is_nullish(date_value):
        return None
    
    # Si ya es un objeto date/datetime
    if isinstance(date_value, datetime):
        return date_value.strftime(output_format)
    if isinstance(date_value, date):
        return date_value.strftime(output_format)
    
    # Si es string, intentar parsear
    if isinstance(date_value, str):
        date_str = date_value.strip()
        
        # Intentar múltiples formatos
        date_formats = [
            "%Y-%m-%d",      # 2023-10-16
            "%d/%m/%Y",      # 16/10/2023
            "%d-%m-%Y",      # 16-10-2023
            "%Y/%m/%d",      # 2023/10/16
            "%d/%m/%y",      # 16/10/23
            "%d-%m-%y",      # 16-10-23
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.strftime(output_format)
            except ValueError:
                continue
    
    return None


# =============================================================================
# 4. NORMALIZACIÓN DE NÚMEROS
# =============================================================================

def normalize_number(
    value: Any, 
    decimal_places: Optional[int] = None,
    force_positive: bool = False
) -> Optional[float]:
    """
    🔢 Normalizar valor numérico (decimal, entero, string)
    
    Args:
        value: Valor a normalizar
        decimal_places: Cantidad de decimales a redondear (None = sin redondeo)
        force_positive: Si True, convierte valores negativos a positivos
    
    Returns:
        Número normalizado como float o None si es inválido
    
    Examples:
        >>> normalize_number("1.234,56")
        1234.56
        >>> normalize_number("1,234.56")
        1234.56
        >>> normalize_number(-100, force_positive=True)
        100.0
    """
    if is_nullish(value):
        return None
    
    # Si ya es número
    if isinstance(value, (int, float)):
        result = float(value)
        if force_positive:
            result = abs(result)
        if decimal_places is not None:
            result = round(result, decimal_places)
        return result
    
    # Si es Decimal
    if isinstance(value, Decimal):
        result = float(value)
        if force_positive:
            result = abs(result)
        if decimal_places is not None:
            result = round(result, decimal_places)
        return result
    
    # Si es string
    if isinstance(value, str):
        # Limpiar string
        cleaned = value.strip()
        
        # Eliminar símbolos de moneda y espacios
        cleaned = re.sub(r'[$\s]', '', cleaned)
        
        # Detectar formato de número
        # Formato argentino: 1.234,56 (punto miles, coma decimal)
        # Formato inglés: 1,234.56 (coma miles, punto decimal)
        
        # Contar puntos y comas
        punto_count = cleaned.count('.')
        coma_count = cleaned.count(',')
        
        # Determinar formato
        if coma_count > 0 and punto_count > 0:
            # Ambos presentes: el último es decimal
            last_punto = cleaned.rfind('.')
            last_coma = cleaned.rfind(',')
            
            if last_coma > last_punto:
                # Formato argentino: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # Formato inglés: 1,234.56
                cleaned = cleaned.replace(',', '')
        elif coma_count > 0:
            # Solo comas: podría ser miles o decimal
            if coma_count == 1 and cleaned.index(',') > len(cleaned) - 4:
                # Es decimal: 1234,56
                cleaned = cleaned.replace(',', '.')
            else:
                # Son miles: 1,234,567
                cleaned = cleaned.replace(',', '')
        elif punto_count > 0:
            # Solo puntos: podría ser miles o decimal
            if punto_count == 1 and cleaned.index('.') > len(cleaned) - 4:
                # Es decimal (ya está bien)
                pass
            else:
                # Son miles: 1.234.567
                cleaned = cleaned.replace('.', '')
        
        # Intentar convertir
        try:
            result = float(cleaned)
            if force_positive:
                result = abs(result)
            if decimal_places is not None:
                result = round(result, decimal_places)
            return result
        except (ValueError, InvalidOperation):
            return None
    
    return None


def normalize_cantidad(cantidad: Any) -> Optional[float]:
    """
    📦 Normalizar cantidad (siempre positiva, 4 decimales)
    
    Args:
        cantidad: Cantidad a normalizar
    
    Returns:
        Cantidad normalizada o None
    """
    return normalize_number(cantidad, decimal_places=4, force_positive=True)


def normalize_precio(precio: Any) -> Optional[float]:
    """
    💰 Normalizar precio (siempre positivo, 2 decimales)
    
    Args:
        precio: Precio a normalizar
    
    Returns:
        Precio normalizado o None
    """
    return normalize_number(precio, decimal_places=2, force_positive=True)


def normalize_monto(monto: Any) -> Optional[float]:
    """
    💵 Normalizar monto monetario (puede ser negativo, 2 decimales)
    
    Args:
        monto: Monto a normalizar
    
    Returns:
        Monto normalizado o None
    """
    return normalize_number(monto, decimal_places=2, force_positive=False)


# =============================================================================
# 5. NORMALIZACIÓN DE ESTRUCTURAS COMPLETAS
# =============================================================================

def normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    📦 Normalizar lista de items
    
    Args:
        items: Lista de items a normalizar
    
    Returns:
        Lista de items normalizados
    """
    if not items or not isinstance(items, list):
        return []
    
    normalized_items = []
    
    for item in items:
        if not isinstance(item, dict):
            continue
        
        normalized_item = {
            "codigo": normalize_text(item.get("codigo")),
            "descripcion": normalize_text(item.get("descripcion")),
            "cantidad": normalize_cantidad(item.get("cantidad")),
            "unidad_medida": normalize_text(item.get("unidad_medida")),
            "precio_unitario": normalize_precio(item.get("precio_unitario")),
            "subtotal": normalize_monto(item.get("subtotal"))
        }
        
        normalized_items.append(normalized_item)
    
    return normalized_items


def normalize_documento(documento: Dict[str, Any]) -> Dict[str, Any]:
    """
    📄 Normalizar sección de documento
    
    Args:
        documento: Diccionario con datos del documento
    
    Returns:
        Documento normalizado
    """
    if not documento or not isinstance(documento, dict):
        return {}
    
    return {
        "tipo_comprobante": normalize_text(documento.get("tipo_comprobante")),
        "codigo": normalize_text(documento.get("codigo")),
        "numero_comprobante": normalize_text(documento.get("numero_comprobante")),
        "punto_venta": normalize_text(documento.get("punto_venta")),
        "fecha_emision": normalize_date(documento.get("fecha_emision")),
        "cae": normalize_text(documento.get("cae")),
        "fecha_vencimiento_cae": normalize_date(documento.get("fecha_vencimiento_cae")),
        "moneda": normalize_text(documento.get("moneda")) or "ARS",
        "condicion_venta": normalize_text(documento.get("condicion_venta")),
        "numero_remito": normalize_text(documento.get("numero_remito")),
        "observaciones": normalize_text(documento.get("observaciones"), to_upper=False),
        "numero_orden_compra": normalize_text(documento.get("numero_orden_compra")),
        "fecha_vencimiento_pago": normalize_date(documento.get("fecha_vencimiento_pago"))
    }


def normalize_parte(parte: Dict[str, Any], is_empresa: bool = False) -> Dict[str, Any]:
    """
    👤 Normalizar datos de una parte (empresa o cliente)
    
    Args:
        parte: Diccionario con datos de la parte
        is_empresa: True si es empresa, False si es cliente
    
    Returns:
        Parte normalizada
    """
    if not parte or not isinstance(parte, dict):
        return {}
    
    normalized = {
        "cuit": normalize_cuit(parte.get("cuit")),
        "provincia": normalize_provincia(parte.get("provincia")),
        "condicion_iva": normalize_condicion_iva(parte.get("condicion_iva")),
        "domicilio_calle": normalize_text(parte.get("domicilio_calle")),
        "domicilio_localidad": normalize_text(parte.get("domicilio_localidad")),
        "domicilio_codigo_postal": normalize_text(parte.get("domicilio_codigo_postal"))
    }
    
    if is_empresa:
        normalized.update({
            "razon_social": normalize_text(parte.get("razon_social")),
            "ingresos_brutos": normalize_text(parte.get("ingresos_brutos")),
            "domicilio_comercial": normalize_text(parte.get("domicilio_comercial")),
            "fecha_inicio_actividades": normalize_date(parte.get("fecha_inicio_actividades"))
        })
    else:
        normalized.update({
            "apellido_nombre_razon_social": normalize_text(parte.get("apellido_nombre_razon_social")),
            "domicilio": normalize_text(parte.get("domicilio"))
        })
    
    return normalized


def normalize_fiscalidad(fiscalidad: Dict[str, Any]) -> Dict[str, Any]:
    """
    🧮 Normalizar estructura de fiscalidad
    
    Convierte formato plano de IVA (iva_21, iva_105, etc.) al formato
    nativo legacy (iva: {"21": valor, "105": valor}).
    
    Args:
        fiscalidad: Diccionario de fiscalidad
    
    Returns:
        Fiscalidad normalizada con estructura IVA nativa
    """
    if not fiscalidad or not isinstance(fiscalidad, dict):
        return fiscalidad
    
    normalized = fiscalidad.copy()
    
    # Normalizar impuestos IVA
    if "impuestos" in normalized and isinstance(normalized["impuestos"], dict):
        impuestos = normalized["impuestos"].copy()
        
        # Convertir formato plano a formato dict anidado
        iva_dict = {}
        
        # Mapeo de campos planos a keys del dict
        iva_mappings = {
            "iva_21": "21",
            "iva_105": "105",
            "iva_27": "27",
            "iva_5": "5",
            "iva_25": "25"
        }
        
        # Si ya existe formato dict, usarlo
        if "iva" in impuestos and isinstance(impuestos["iva"], dict):
            iva_dict = impuestos["iva"].copy()
        else:
            # Convertir desde formato plano
            for flat_key, rate_key in iva_mappings.items():
                if flat_key in impuestos:
                    value = impuestos.pop(flat_key)
                    try:
                        float_value = float(value) if value is not None else 0.0
                        if float_value > 0:
                            iva_dict[rate_key] = float_value
                    except (ValueError, TypeError):
                        # Si no se puede convertir, ignorar
                        pass
        
        # Reemplazar con formato dict
        if iva_dict:
            impuestos["iva"] = iva_dict
        elif "iva" not in impuestos:
            # Asegurar que existe aunque esté vacío
            impuestos["iva"] = {}
        
        # Asegurar que TODOS los campos de impuestos existen (estructura legacy completa)
        campos_impuestos_legacy = {
            "icl_idc": 0,
            "retencion_iva": None,
            "percepcion_iva": 0,
            "retencion_suss": None,
            "percepcion_iibb": [],
            "retenciones_iibb": [],
            "otras_retenciones": None,
            "impuestos_internos": 0,
            "retencion_ganancias": None,
            "percepcion_ganancias": 0
        }
        
        # Agregar campos faltantes con valores por defecto
        for campo, valor_default in campos_impuestos_legacy.items():
            if campo not in impuestos:
                impuestos[campo] = valor_default
        
        normalized["impuestos"] = impuestos
        
        # Asegurar que totales tiene 'descuentos'
        if "totales" in normalized and isinstance(normalized["totales"], dict):
            if "descuentos" not in normalized["totales"]:
                normalized["totales"]["descuentos"] = 0
        
        # Nota: items_count e items_subtotal_total se calcularán en normalize_all()
        # si están disponibles los items
    
    return normalized


def normalize_all(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 Normalizar estructura completa de comprobante
    
    Args:
        data: Diccionario completo del comprobante extraído
    
    Returns:
        Comprobante completamente normalizado
    
    Esta es la función principal que se llama desde el post-procesador.
    """
    if not data or not isinstance(data, dict):
        return data
    
    # Paso 1: Limpiar valores nullish recursivamente
    data = clean_nullish_recursive(data)
    
    # Paso 2: Normalizar secciones específicas
    normalized = {}
    
    # Items
    if "items" in data:
        normalized["items"] = normalize_items(data["items"])
    
    # Documento
    if "documento" in data:
        normalized["documento"] = normalize_documento(data["documento"])
    
    # Partes
    if "partes" in data and isinstance(data["partes"], dict):
        normalized["partes"] = {}
        if "empresa" in data["partes"]:
            normalized["partes"]["empresa"] = normalize_parte(
                data["partes"]["empresa"], 
                is_empresa=True
            )
        if "cliente" in data["partes"]:
            normalized["partes"]["cliente"] = normalize_parte(
                data["partes"]["cliente"], 
                is_empresa=False
            )
    
    # Fiscalidad (se normaliza pero no se valida aquí)
    if "fiscalidad" in data:
        normalized["fiscalidad"] = normalize_fiscalidad(data["fiscalidad"])
        
        # Calcular items_count y items_subtotal_total si tenemos items
        if "items" in normalized:
            # Asegurar que calculos existe
            if "calculos" not in normalized["fiscalidad"]:
                normalized["fiscalidad"]["calculos"] = {}
            
            calculos = normalized["fiscalidad"]["calculos"]
            items = normalized["items"]
            
            # Asegurar que calculos es un dict
            if not isinstance(calculos, dict):
                calculos = {}
                normalized["fiscalidad"]["calculos"] = calculos
            
            # SIEMPRE recalcular items_count desde items (más confiable)
            calculos["items_count"] = len(items)
            
            # SIEMPRE recalcular items_subtotal_total desde items (más confiable)
            items_subtotal_total = sum(
                float(item.get("subtotal", 0)) 
                for item in items 
                if isinstance(item, dict)
            )
            calculos["items_subtotal_total"] = items_subtotal_total
    
    # Metadata
    if "metadata" in data:
        normalized["metadata"] = data["metadata"]
    
    return normalized

