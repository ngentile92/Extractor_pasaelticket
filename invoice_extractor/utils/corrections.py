# invoice_extractor/utils/corrections.py
"""
🔧 Módulo de Correcciones Post-Extracción

Este módulo aplica correcciones específicas a los datos extraídos
para mejorar la calidad y consistencia de la información.

Referencia: CORRECCIONES_POST_EXTRACCION.md - Sección de Correcciones
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date, datetime

from invoice_extractor.validators.afip_document_types import afip_catalog
from invoice_extractor.validators.cuit_validator import CUITValidator
from invoice_extractor.utils.normalization import (
    normalize_text, 
    normalize_monto, 
    normalize_cantidad,
    is_nullish
)

logger = logging.getLogger(__name__)


# =============================================================================
# 1. CORRECCIÓN DE CUITs
# =============================================================================

def apply_cuit_auto_correction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Auto-corrección de CUITs con dígito verificador incorrecto
    
    Si un CUIT tiene formato válido pero dígito verificador incorrecto,
    lo corrige automáticamente y agrega un warning para revisión.
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos corregidos con warnings agregados
    """
    if "partes" not in data:
        return data
    
    partes = data["partes"]
    warnings_added = []
    
    # Corregir CUIT de empresa
    if "empresa" in partes and partes["empresa"]:
        empresa_cuit = partes["empresa"].get("cuit")
        if empresa_cuit:
            validation = CUITValidator.validate_complete(empresa_cuit)
            
            # Si formato válido pero verificador incorrecto, auto-corregir
            if validation['format_valid'] and not validation['verifier_valid'] and validation['can_auto_fix']:
                cuit_original = validation['cuit_original']
                cuit_corregido = validation['suggested_cuit']
                
                partes["empresa"]["cuit"] = cuit_corregido
                warning_msg = f"⚠️ CUIT empresa auto-corregido: '{cuit_original}' → '{cuit_corregido}' (dígito verificador incorrecto - REVISAR en documento original)"
                warnings_added.append(warning_msg)
                logger.warning(warning_msg)
    
    # Corregir CUIT de cliente
    if "cliente" in partes and partes["cliente"]:
        cliente_cuit = partes["cliente"].get("cuit")
        if cliente_cuit:
            validation = CUITValidator.validate_complete(cliente_cuit)
            
            # Si formato válido pero verificador incorrecto, auto-corregir
            if validation['format_valid'] and not validation['verifier_valid'] and validation['can_auto_fix']:
                cuit_original = validation['cuit_original']
                cuit_corregido = validation['suggested_cuit']
                
                partes["cliente"]["cuit"] = cuit_corregido
                warning_msg = f"⚠️ CUIT cliente auto-corregido: '{cuit_original}' → '{cuit_corregido}' (dígito verificador incorrecto - REVISAR en documento original)"
                warnings_added.append(warning_msg)
                logger.warning(warning_msg)
    
    # Agregar warnings al metadata si existe
    if warnings_added:
        if "_correction_warnings" not in data:
            data["_correction_warnings"] = []
        data["_correction_warnings"].extend(warnings_added)
    
    return data


# =============================================================================
# 1.5. CORRECCIÓN DE FORMATO DE FECHAS
# =============================================================================

def apply_date_format_correction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Convertir fechas a formato argentino DD/MM/YYYY
    
    Si las fechas están en formato ISO (YYYY-MM-DD), las convierte automáticamente
    al formato argentino DD/MM/YYYY que es el estándar en Argentina.
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos con fechas en formato DD/MM/YYYY
    """
    if "documento" not in data or not isinstance(data["documento"], dict):
        return data
    
    documento = data["documento"]
    campos_fecha = ["fecha_emision", "fecha_vencimiento_cae", "fecha_vencimiento_pago"]
    
    for campo in campos_fecha:
        fecha_valor = documento.get(campo)
        if fecha_valor:
            from invoice_extractor.utils.normalization import normalize_date
            
            # Intentar normalizar a formato DD/MM/YYYY argentino
            fecha_normalizada = normalize_date(fecha_valor, output_format="%d/%m/%Y")
            
            if fecha_normalizada and fecha_normalizada != fecha_valor:
                logger.info(f"📅 {campo}: '{fecha_valor}' → '{fecha_normalizada}' (convertido a formato argentino)")
                documento[campo] = fecha_normalizada
    
    return data


# =============================================================================
# 2. CORRECCIÓN DE ITEMS
# =============================================================================

def apply_items_correction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Corregir items del comprobante
    
    Correcciones:
    - Intercambio codigo/descripcion cuando están invertidos
    - Detección de precios en descripción
    - Normalización de unidades de medida
    - Cálculo de subtotales faltantes
    - Eliminación de items vacíos/inválidos
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos corregidos
    """
    if "items" not in data or not isinstance(data["items"], list):
        return data
    
    items_corregidos = []
    items_eliminados = 0
    
    for idx, item in enumerate(data["items"]):
        if not isinstance(item, dict):
            items_eliminados += 1
            continue
        
        # 1. DETECTAR SI DESCRIPCIÓN ES UN PRECIO
        descripcion = item.get("descripcion")
        if descripcion and isinstance(descripcion, str):
            # Si descripción parece un precio (tiene coma/punto decimal y números)
            desc_limpia = descripcion.replace('.', '').replace(',', '.')
            try:
                # Si se puede convertir a float Y tiene decimales, probablemente es un precio
                precio_probable = float(desc_limpia)
                if ',' in descripcion or ('.' in descripcion and len(descripcion) < 12):
                    # Esto es un precio, no una descripción
                    logger.warning(f"❌ Item {idx}: descripción '{descripcion}' parece un PRECIO - marcando para eliminar")
                    item["descripcion"] = None  # Marcarlo como inválido
            except ValueError:
                pass  # No es un número, está bien
        
        # 2. DETECTAR INTERCAMBIO CODIGO/DESCRIPCION
        codigo = item.get("codigo")
        descripcion = item.get("descripcion")
        
        if codigo and descripcion:
            len_codigo = len(str(codigo))
            len_desc = len(str(descripcion))
            
            # Caso 1: código muy largo (> 20 chars) y descripción existe
            if len_codigo > 20 and len_desc > 0:
                logger.info(f"🔄 Item {idx}: intercambiando codigo/descripcion (codigo muy largo: {len_codigo} chars)")
                item["codigo"], item["descripcion"] = item["descripcion"], item["codigo"]
            
            # Caso 2: código incluye descripción (tiene espacios o es muy largo)
            elif ' ' in str(codigo) and len_codigo > 15:
                logger.info(f"🔄 Item {idx}: código '{codigo}' parece incluir descripción - limpiando")
                # Intentar separar código y descripción
                partes = str(codigo).split(None, 1)  # Split en primer espacio
                if len(partes) == 2:
                    item["codigo"] = partes[0] if len(partes[0]) < 15 else None
                    item["descripcion"] = partes[1] if len(partes[1]) > len_desc else descripcion
        
        # 3. Si código es muy corto pero descripción está vacía o es None, intercambiar
        elif codigo and not descripcion:
            if len(str(codigo)) > 10:
                logger.info(f"🔄 Item {idx}: moviendo codigo '{codigo}' a descripcion (no hay descripcion)")
                item["descripcion"] = str(codigo)
                item["codigo"] = None
        
        # 2. NORMALIZACIÓN DE UNIDADES DE MEDIDA
        unidad = item.get("unidad_medida")
        if unidad and isinstance(unidad, str):
            unidad_norm = normalize_text(unidad)
            if unidad_norm:
                item["unidad_medida"] = unidad_norm
        
        # 3. CALCULAR SUBTOTAL SI FALTA PERO HAY CANTIDAD Y PRECIO
        if is_nullish(item.get("subtotal")):
            cantidad = normalize_cantidad(item.get("cantidad"))
            precio_unitario = normalize_monto(item.get("precio_unitario"))
            
            if cantidad is not None and precio_unitario is not None:
                subtotal_calculado = round(cantidad * precio_unitario, 2)
                item["subtotal"] = subtotal_calculado
                logger.info(f"✨ Item {idx}: subtotal calculado: {subtotal_calculado}")
        
        # 4. VALIDAR QUE EL ITEM TENGA AL MENOS DESCRIPCIÓN Y CANTIDAD
        if is_nullish(item.get("descripcion")) or is_nullish(item.get("cantidad")):
            items_eliminados += 1
            logger.warning(f"⚠️ Item {idx}: eliminado por falta de datos esenciales")
            continue
        
        items_corregidos.append(item)
    
    # Reemplazar items con la lista corregida
    data["items"] = items_corregidos
    
    if items_eliminados > 0:
        logger.info(f"🗑️ Eliminados {items_eliminados} items inválidos")
    
    # 5. NORMALIZAR UNIDADES DE MEDIDA (si todas son iguales menos una, corregir la diferente)
    if len(items_corregidos) > 2:
        unidades = [item.get("unidad_medida") for item in items_corregidos if item.get("unidad_medida")]
        if len(unidades) >= 3:
            from collections import Counter
            contador = Counter(unidades)
            
            # Si hay una unidad que aparece mucho más que las demás
            if len(contador) > 1:
                unidad_comun = contador.most_common(1)[0]
                unidad_comun_valor, unidad_comun_count = unidad_comun
                
                # Si la unidad más común representa al menos el 80% de los items
                if unidad_comun_count / len(unidades) >= 0.8:
                    # Corregir las que son diferentes
                    for idx, item in enumerate(items_corregidos):
                        unidad_actual = item.get("unidad_medida")
                        if unidad_actual and unidad_actual != unidad_comun_valor:
                            logger.warning(
                                f"📦 Item {idx}: unidad '{unidad_actual}' parece incorrecta - "
                                f"corrigiendo a '{unidad_comun_valor}' (unidad más común en {unidad_comun_count}/{len(unidades)} items)"
                            )
                            item["unidad_medida"] = unidad_comun_valor
    
    data["items"] = items_corregidos
    return data


# =============================================================================
# 2. CORRECCIÓN DE TIPO DE DOCUMENTO
# =============================================================================

def apply_document_type_correction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Validar y corregir tipo de documento usando catálogo AFIP
    
    Proceso:
    1. Extraer código y denominación de documento.tipo_comprobante
    2. Validar contra catálogo AFIP
    3. Si hay inconsistencias, usar denominación oficial
    4. Agregar log de corrección
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos corregidos
    """
    if "documento" not in data or not isinstance(data["documento"], dict):
        return data
    
    documento = data["documento"]
    codigo = documento.get("codigo")
    tipo_comprobante = documento.get("tipo_comprobante")
    
    if not codigo and not tipo_comprobante:
        return data  # No hay datos para validar
    
    # Validar contra catálogo AFIP
    validation = afip_catalog.validate_match(codigo, tipo_comprobante)
    
    # Si hay corrección sugerida, aplicarla
    if validation["match_score"] < 1.0 and validation.get("codigo_encontrado"):
        old_tipo = tipo_comprobante
        old_codigo = codigo
        
        # Usar denominación y código oficiales
        documento["tipo_comprobante"] = validation["denominacion_encontrada"]
        documento["codigo"] = validation["codigo_encontrado"]
        
        # Log de corrección
        logger.info(f"🔧 Tipo de documento corregido:")
        logger.info(f"   Antes: codigo={old_codigo}, tipo={old_tipo}")
        logger.info(f"   Después: codigo={validation['codigo_encontrado']}, tipo={validation['denominacion_encontrada']}")
        logger.info(f"   Score: {validation['match_score']}")
        
        # Guardar información de validación
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["document_type_validation"] = {
            "original_code": old_codigo,
            "original_type": old_tipo,
            "corrected_code": validation['codigo_encontrado'],
            "corrected_type": validation['denominacion_encontrada'],
            "validation_score": validation['match_score'],
            "inconsistencias": validation.get("inconsistencias", []),
            "sugerencias": validation.get("sugerencias", [])
        }
    
    return data


# =============================================================================
# 3. CORRECCIÓN DE DOMICILIOS
# =============================================================================

def apply_address_consolidation(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Consolidar domicilios fragmentados
    
    Problema: A veces el OCR extrae domicilios en campos separados:
    - domicilio_calle
    - domicilio_localidad
    - domicilio_codigo_postal
    
    Solución: Consolidar en un solo campo "domicilio" cuando sea necesario
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos corregidos
    """
    if "partes" not in data or not isinstance(data["partes"], dict):
        return data
    
    partes = data["partes"]
    
    # Consolidar domicilio de empresa
    if "empresa" in partes and isinstance(partes["empresa"], dict):
        empresa = partes["empresa"]
        empresa_updated = _consolidate_address_fields(empresa, "empresa")
        if empresa_updated:
            partes["empresa"] = empresa_updated
    
    # Consolidar domicilio de cliente
    if "cliente" in partes and isinstance(partes["cliente"], dict):
        cliente = partes["cliente"]
        cliente_updated = _consolidate_address_fields(cliente, "cliente")
        if cliente_updated:
            partes["cliente"] = cliente_updated
    
    return data


def _consolidate_address_fields(parte: Dict[str, Any], parte_name: str) -> Optional[Dict[str, Any]]:
    """
    Consolidar campos de domicilio de una parte (empresa/cliente)
    """
    calle = parte.get("domicilio_calle")
    localidad = parte.get("domicilio_localidad")
    codigo_postal = parte.get("domicilio_codigo_postal")
    domicilio_completo = parte.get("domicilio") or parte.get("domicilio_comercial")
    
    # Si ya hay un domicilio completo y no está vacío, no hacer nada
    if domicilio_completo and not is_nullish(domicilio_completo):
        return parte
    
    # Construir domicilio desde partes
    parts = []
    if calle and not is_nullish(calle):
        parts.append(str(calle))
    if localidad and not is_nullish(localidad):
        parts.append(str(localidad))
    if codigo_postal and not is_nullish(codigo_postal):
        parts.append(f"(CP: {codigo_postal})")
    
    if parts:
        domicilio_consolidado = ", ".join(parts)
        
        # Guardar en el campo apropiado
        if parte_name == "empresa":
            parte["domicilio_comercial"] = domicilio_consolidado
        else:
            parte["domicilio"] = domicilio_consolidado
        
        logger.info(f"🏠 Domicilio {parte_name} consolidado: {domicilio_consolidado}")
    
    return parte


# =============================================================================
# 4. CORRECCIÓN DE CÁLCULOS FISCALES
# =============================================================================

def apply_fiscal_calculations_correction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Corregir y recalcular totales fiscales
    
    Correcciones:
    1. Recalcular IVA total desde alícuotas
    2. Recalcular percepciones totales
    3. Recalcular retenciones totales
    4. Verificar diferencias matemáticas
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos corregidos
    """
    if "fiscalidad" not in data or not isinstance(data["fiscalidad"], dict):
        return data
    
    fiscalidad = data["fiscalidad"]
    impuestos = fiscalidad.get("impuestos", {})
    calculos = fiscalidad.get("calculos", {})
    
    if not isinstance(impuestos, dict):
        return data
    
    # 1. RECALCULAR IVA TOTAL
    iva_total_calculado = 0.0
    
    # IVA puede venir como dict {21: xxx, 10.5: yyy} o como campos iva_21, iva_105
    if "iva" in impuestos:
        iva_data = impuestos["iva"]
        if isinstance(iva_data, dict):
            for alicuota, monto in iva_data.items():
                if monto is not None and not is_nullish(monto):
                    iva_total_calculado += float(monto)
    
    # Campos individuales (formato del schema simplificado)
    for field in ["iva_21", "iva_105", "iva_27", "iva_5", "iva_25"]:
        if field in impuestos and impuestos[field] is not None:
            iva_total_calculado += float(impuestos[field])
    
    # Actualizar calculos
    if not isinstance(calculos, dict):
        calculos = {}
    
    calculos["total_iva_calculado"] = round(iva_total_calculado, 2)
    
    # 2. RECALCULAR PERCEPCIONES TOTALES
    percepciones_total = 0.0
    
    # Percepción IVA
    if "percepcion_iva" in impuestos and impuestos["percepcion_iva"] is not None:
        percepciones_total += float(impuestos["percepcion_iva"])
    
    # Percepción Ganancias
    if "percepcion_ganancias" in impuestos and impuestos["percepcion_ganancias"] is not None:
        percepciones_total += float(impuestos["percepcion_ganancias"])
    
    # Percepciones IIBB
    if "percepcion_iibb" in impuestos:
        iibb_data = impuestos["percepcion_iibb"]
        if isinstance(iibb_data, list):
            for p in iibb_data:
                if isinstance(p, dict) and "monto" in p:
                    percepciones_total += float(p["monto"])
    
    calculos["total_percepciones_calculado"] = round(percepciones_total, 2)
    
    # 3. RECALCULAR RETENCIONES TOTALES
    retenciones_total = 0.0
    
    # Retención IVA
    if "retencion_iva" in impuestos and impuestos["retencion_iva"] is not None:
        retenciones_total += float(impuestos["retencion_iva"])
    
    # Retención Ganancias
    if "retencion_ganancias" in impuestos and impuestos["retencion_ganancias"] is not None:
        retenciones_total += float(impuestos["retencion_ganancias"])
    
    # Retención SUSS
    if "retencion_suss" in impuestos and impuestos["retencion_suss"] is not None:
        retenciones_total += float(impuestos["retencion_suss"])
    
    # Retenciones IIBB
    if "retenciones_iibb" in impuestos:
        iibb_ret_data = impuestos["retenciones_iibb"]
        if isinstance(iibb_ret_data, list):
            for r in iibb_ret_data:
                if isinstance(r, dict) and "monto" in r:
                    retenciones_total += float(r["monto"])
    
    calculos["total_retenciones_calculado"] = round(retenciones_total, 2)
    
    # 4. VERIFICAR DIFERENCIA MATEMÁTICA
    totales = fiscalidad.get("totales", {})
    if isinstance(totales, dict):
        try:
            subtotal_gravado = float(totales.get("subtotal_gravado", 0))
        except (ValueError, TypeError):
            subtotal_gravado = 0.0
        
        try:
            descuentos = float(totales.get("descuentos", 0))
        except (ValueError, TypeError):
            descuentos = 0.0
        
        try:
            importe_total = float(totales.get("importe_total", 0))
        except (ValueError, TypeError):
            importe_total = 0.0
        
        if subtotal_gravado > 0 and importe_total > 0:
            total_calculado = subtotal_gravado + iva_total_calculado + percepciones_total - retenciones_total - descuentos
            diferencia = round(importe_total - total_calculado, 2)
            
            calculos["diferencia_matematica"] = diferencia
            
            if abs(diferencia) > 0.10:  # Tolerancia de 10 centavos
                logger.warning(f"⚠️ Diferencia matemática significativa: ${diferencia}")
    
    # Guardar calculos actualizados
    fiscalidad["calculos"] = calculos
    data["fiscalidad"] = fiscalidad
    
    logger.info(f"💰 Cálculos fiscales actualizados: IVA={iva_total_calculado:.2f}, Percepciones={percepciones_total:.2f}, Retenciones={retenciones_total:.2f}")
    
    return data


# =============================================================================
# 5. CORRECCIÓN DE FECHAS INCONSISTENTES
# =============================================================================

def apply_date_consistency_correction(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔧 Verificar y corregir inconsistencias en fechas
    
    Verificaciones:
    1. fecha_emision debe ser <= fecha_vencimiento_cae
    2. fecha_emision debe ser <= fecha_vencimiento_pago
    3. fecha_vencimiento_cae debe estar dentro de los próximos 180 días de fecha_emision
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos corregidos
    """
    if "documento" not in data or not isinstance(data["documento"], dict):
        return data
    
    documento = data["documento"]
    
    fecha_emision = documento.get("fecha_emision")
    fecha_venc_cae = documento.get("fecha_vencimiento_cae")
    fecha_venc_pago = documento.get("fecha_vencimiento_pago")
    
    # Convertir a objetos date si son strings
    def parse_date_safe(date_value):
        if isinstance(date_value, str):
            try:
                return datetime.strptime(date_value, "%Y-%m-%d").date()
            except:
                return None
        elif isinstance(date_value, date):
            return date_value
        return None
    
    fecha_emision_obj = parse_date_safe(fecha_emision)
    fecha_venc_cae_obj = parse_date_safe(fecha_venc_cae)
    fecha_venc_pago_obj = parse_date_safe(fecha_venc_pago)
    
    warnings = []
    
    # Verificación 1: fecha_emision <= fecha_vencimiento_cae
    if fecha_emision_obj and fecha_venc_cae_obj:
        if fecha_emision_obj > fecha_venc_cae_obj:
            warnings.append(f"Fecha emisión ({fecha_emision}) posterior a vencimiento CAE ({fecha_venc_cae})")
    
    # Verificación 2: fecha_emision <= fecha_vencimiento_pago
    if fecha_emision_obj and fecha_venc_pago_obj:
        if fecha_emision_obj > fecha_venc_pago_obj:
            warnings.append(f"Fecha emisión ({fecha_emision}) posterior a vencimiento pago ({fecha_venc_pago})")
    
    # Verificación 3: CAE válido por máximo 180 días
    if fecha_emision_obj and fecha_venc_cae_obj:
        dias_diferencia = (fecha_venc_cae_obj - fecha_emision_obj).days
        if dias_diferencia > 180:
            warnings.append(f"CAE válido por {dias_diferencia} días (máximo esperado: 180)")
        elif dias_diferencia < 0:
            warnings.append(f"CAE vencido antes de emisión")
    
    if warnings:
        logger.warning(f"📅 Inconsistencias en fechas detectadas:")
        for warning in warnings:
            logger.warning(f"   - {warning}")
        
        # Guardar warnings en metadata
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["date_warnings"] = warnings
    
    return data


# =============================================================================
# 6. APLICAR TODAS LAS CORRECCIONES
# =============================================================================

def apply_all_corrections(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🎯 Aplicar todas las correcciones en orden
    
    Orden de ejecución:
    1. Corrección de items (intercambios, cálculos)
    2. Corrección de tipo de documento (validación AFIP)
    3. Consolidación de domicilios
    4. Corrección de cálculos fiscales
    5. Verificación de fechas
    
    Args:
        data: Diccionario con datos del comprobante
    
    Returns:
        Datos completamente corregidos
    """
    logger.info("🔧 Iniciando correcciones post-extracción...")
    
    # FASE 1: CUITs (auto-corrección con warning)
    data = apply_cuit_auto_correction(data)
    
    # FASE 1.5: Fechas (convertir a formato DD/MM/YYYY argentino)
    data = apply_date_format_correction(data)
    
    # FASE 2: Items
    data = apply_items_correction(data)
    
    # FASE 3: Tipo de documento
    data = apply_document_type_correction(data)
    
    # FASE 3: Domicilios
    data = apply_address_consolidation(data)
    
    # FASE 4: Cálculos fiscales
    data = apply_fiscal_calculations_correction(data)
    
    # FASE 5: Fechas
    data = apply_date_consistency_correction(data)
    
    logger.info("✅ Correcciones completadas")
    
    return data

