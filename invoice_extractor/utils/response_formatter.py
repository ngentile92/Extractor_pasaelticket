"""
🎯 Formateador de respuesta final para facturas extraídas.

Genera una estructura limpia, ordenada y sin redundancia:
1. DATOS FINALES - Toda la información procesada
2. VALIDACIÓN - Score y nivel de confianza  
3. ALERTAS - Errores, warnings, correcciones
4. METADATA - Info técnica del proceso
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def format_invoice_response(
    processed_data: Dict[str, Any],
    validation_result: Dict[str, Any],
    processing_metadata: Dict[str, Any],
    extraction_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Formatea los datos de extracción en una estructura limpia y ordenada.
    
    Args:
        processed_data: Datos procesados y normalizados
        validation_result: Resultado de validaciones
        processing_metadata: Metadata del procesamiento
        extraction_metadata: Metadata de la extracción
    
    Returns:
        Diccionario con estructura limpia y ordenada
    """
    
    # =========================================================================
    # 1. DATOS FINALES DE LA FACTURA
    # =========================================================================
    factura = _build_factura_section(processed_data)
    
    # =========================================================================
    # 2. VALIDACIÓN
    # =========================================================================
    validacion = _build_validacion_section(validation_result)
    
    # =========================================================================
    # 3. ALERTAS (errores, warnings, correcciones)
    # =========================================================================
    alertas = _build_alertas_section(
        validation_result, 
        processed_data.get('_correction_warnings', [])
    )
    
    # =========================================================================
    # 4. METADATA TÉCNICA
    # =========================================================================
    metadata = _build_metadata_section(processing_metadata, extraction_metadata)
    
    return {
        "factura": factura,
        "validacion": validacion,
        "alertas": alertas,
        "metadata": metadata
    }


def _build_factura_section(data: Dict[str, Any]) -> Dict[str, Any]:
    """Construye la sección de datos finales de la factura."""
    
    documento = data.get('documento', {})
    partes = data.get('partes', {})
    fiscalidad = data.get('fiscalidad', {})
    items = data.get('items', [])
    
    # Documento
    doc_final = {
        "tipo": documento.get('tipo_comprobante'),
        "codigo": documento.get('codigo'),
        "numero": _format_numero_comprobante(
            documento.get('punto_venta'),
            documento.get('numero_comprobante')
        ),
        "punto_venta": documento.get('punto_venta'),
        "numero_comprobante": documento.get('numero_comprobante'),
        "fecha_emision": documento.get('fecha_emision'),
        "cae": documento.get('cae'),
        "fecha_vencimiento_cae": documento.get('fecha_vencimiento_cae'),
        "moneda": documento.get('moneda', 'ARS'),
        "condicion_venta": documento.get('condicion_venta')
    }
    
    # Emisor (empresa)
    empresa = partes.get('empresa', {})
    emisor_final = {
        "razon_social": empresa.get('razon_social'),
        "cuit": empresa.get('cuit'),
        "condicion_iva": empresa.get('condicion_iva'),
        "domicilio": _build_domicilio(empresa),
        "provincia": empresa.get('provincia'),
        "ingresos_brutos": empresa.get('ingresos_brutos'),
        "inicio_actividades": empresa.get('fecha_inicio_actividades')
    }
    
    # Receptor (cliente)
    cliente = partes.get('cliente', {})
    receptor_final = {
        "razon_social": cliente.get('apellido_nombre_razon_social'),
        "cuit": cliente.get('cuit'),
        "condicion_iva": cliente.get('condicion_iva'),
        "domicilio": _build_domicilio(cliente),
        "provincia": cliente.get('provincia')
    }
    
    # Items - simplificados
    items_final = []
    for item in items:
        items_final.append({
            "descripcion": item.get('descripcion'),
            "cantidad": item.get('cantidad'),
            "precio_unitario": item.get('precio_unitario'),
            "subtotal": item.get('subtotal'),
            "codigo": item.get('codigo'),
            "unidad": item.get('unidad_medida')
        })
    
    # Totales e impuestos
    totales = fiscalidad.get('totales', {})
    impuestos = fiscalidad.get('impuestos', {})
    calculos = fiscalidad.get('calculos', {})
    
    totales_final = {
        "subtotal_gravado": totales.get('subtotal_gravado'),
        "descuentos": totales.get('descuentos', 0),
        "iva": _format_iva(impuestos.get('iva', {})),
        "percepciones": _format_percepciones(impuestos),
        "retenciones": _format_retenciones(impuestos),
        "otros_impuestos": _format_otros_impuestos(impuestos),
        "importe_total": totales.get('importe_total')
    }
    
    return {
        "documento": doc_final,
        "emisor": emisor_final,
        "receptor": receptor_final,
        "items": items_final,
        "cantidad_items": len(items_final),
        "totales": totales_final
    }


def _build_validacion_section(validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """Construye la sección de validación."""
    
    score = validation_result.get('validation_score', 0)
    
    # Determinar nivel de confianza
    if score >= 0.9:
        nivel = "alto"
        emoji = "🟢"
    elif score >= 0.7:
        nivel = "medio"
        emoji = "🟡"
    else:
        nivel = "bajo"
        emoji = "🔴"
    
    return {
        "score": round(score * 100, 1),  # Porcentaje
        "score_decimal": round(score, 4),
        "nivel_confianza": nivel,
        "indicador": emoji,
        "requiere_revision": validation_result.get('requires_review', score < 0.7),
        "tiene_errores": validation_result.get('has_validation_errors', False)
    }


def _build_alertas_section(
    validation_result: Dict[str, Any],
    correction_warnings: List[str]
) -> Dict[str, Any]:
    """Construye la sección de alertas (errores, warnings, correcciones)."""
    
    # Extraer errores
    errores = validation_result.get('validation_errors', [])
    if not errores:
        errores = validation_result.get('errors', [])
    
    # Extraer warnings
    warnings = validation_result.get('validation_warnings', [])
    if not warnings:
        warnings = validation_result.get('warnings', [])
    
    # Agregar correction_warnings
    warnings = list(warnings) + list(correction_warnings)
    
    # Extraer alertas estructuradas
    alertas_raw = validation_result.get('alerts', [])
    alertas_criticas = []
    alertas_info = []
    
    for alerta in alertas_raw:
        if isinstance(alerta, dict):
            nivel = alerta.get('level', 'info')
            mensaje = alerta.get('message', '')
            sugerencia = alerta.get('suggestion')
            
            alerta_simple = {
                "mensaje": mensaje,
                "campo": alerta.get('field'),
                "sugerencia": sugerencia
            }
            
            if nivel in ['critical', 'error']:
                alertas_criticas.append(alerta_simple)
            else:
                alertas_info.append(alerta_simple)
    
    # Correcciones aplicadas
    correcciones = validation_result.get('corrections_applied', [])
    
    # Recomendaciones
    recomendaciones = validation_result.get('recommendations', [])
    
    return {
        "errores": errores,
        "errores_count": len(errores),
        "warnings": warnings,
        "warnings_count": len(warnings),
        "alertas_criticas": alertas_criticas,
        "alertas_info": alertas_info,
        "correcciones_aplicadas": correcciones,
        "recomendaciones": recomendaciones
    }


def _build_metadata_section(
    processing_metadata: Dict[str, Any],
    extraction_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Construye la sección de metadata técnica."""
    
    gemini_retry = processing_metadata.get('gemini_retry', {})
    
    metadata = {
        "tiempo_extraccion_seg": extraction_metadata.get('extraction_time'),
        "tiempo_procesamiento_seg": processing_metadata.get('processing_time'),
        "metodo_extraccion": extraction_metadata.get('extractor', 'unknown'),
        "schema_utilizado": extraction_metadata.get('schema_type', 'completo'),
        "version_pipeline": processing_metadata.get('pipeline_version'),
        "timestamp": processing_metadata.get('processing_timestamp')
    }
    
    # Info de retry con Gemini
    if gemini_retry.get('was_retried'):
        metadata["gemini_retry"] = {
            "utilizado": True,
            "score_inicial": round(gemini_retry.get('first_score', 0) * 100, 1),
            "score_final": round(gemini_retry.get('second_score', 0) * 100, 1),
            "mejora_pp": round(gemini_retry.get('improvement', 0), 1)
        }
    
    # Info de orquestación
    orchestration = extraction_metadata.get('orchestration', {})
    if orchestration:
        metadata["orquestacion"] = {
            "estrategia": orchestration.get('strategy_used'),
            "decision_log": orchestration.get('decision_log', [])[:3]  # Solo primeras 3
        }
    
    return metadata


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _format_numero_comprobante(punto_venta: Optional[str], numero: Optional[str]) -> Optional[str]:
    """Formatea número de comprobante completo."""
    if punto_venta and numero:
        return f"{punto_venta}-{numero}"
    return numero


def _build_domicilio(entidad: Dict[str, Any]) -> Optional[str]:
    """Construye domicilio consolidado."""
    # Primero intentar domicilio consolidado
    if entidad.get('domicilio_comercial'):
        return entidad['domicilio_comercial']
    if entidad.get('domicilio'):
        return entidad['domicilio']
    
    # Sino, construir desde partes
    partes = []
    if entidad.get('domicilio_calle'):
        partes.append(entidad['domicilio_calle'])
    if entidad.get('domicilio_localidad'):
        partes.append(entidad['domicilio_localidad'])
    if entidad.get('domicilio_codigo_postal'):
        partes.append(f"CP {entidad['domicilio_codigo_postal']}")
    
    return ', '.join(partes) if partes else None


def _format_iva(iva_dict: Dict[str, float]) -> Dict[str, float]:
    """Formatea IVA por alícuota."""
    result = {}
    total = 0.0
    
    for alicuota, monto in iva_dict.items():
        if monto and float(monto) > 0:
            key = f"iva_{alicuota}%"
            result[key] = float(monto)
            total += float(monto)
    
    if total > 0:
        result["total_iva"] = round(total, 2)
    
    return result if result else {"total_iva": 0}


def _format_percepciones(impuestos: Dict[str, Any]) -> Dict[str, Any]:
    """Formatea percepciones."""
    result = {}
    total = 0.0
    
    # Percepción IVA
    perc_iva = impuestos.get('percepcion_iva', 0) or 0
    if perc_iva > 0:
        result["iva"] = perc_iva
        total += perc_iva
    
    # Percepción Ganancias
    perc_gan = impuestos.get('percepcion_ganancias', 0) or 0
    if perc_gan > 0:
        result["ganancias"] = perc_gan
        total += perc_gan
    
    # Percepciones IIBB
    perc_iibb = impuestos.get('percepcion_iibb', [])
    if perc_iibb:
        iibb_list = []
        for p in perc_iibb:
            if isinstance(p, dict):
                monto = p.get('monto', 0) or 0
                if monto > 0:
                    iibb_list.append({
                        "provincia": p.get('provincia'),
                        "monto": monto
                    })
                    total += monto
        if iibb_list:
            result["iibb"] = iibb_list
    
    result["total_percepciones"] = round(total, 2)
    return result


def _format_retenciones(impuestos: Dict[str, Any]) -> Dict[str, Any]:
    """Formatea retenciones."""
    result = {}
    total = 0.0
    
    # Retención IVA
    ret_iva = impuestos.get('retencion_iva', 0) or 0
    if ret_iva > 0:
        result["iva"] = ret_iva
        total += ret_iva
    
    # Retención Ganancias
    ret_gan = impuestos.get('retencion_ganancias', 0) or 0
    if ret_gan > 0:
        result["ganancias"] = ret_gan
        total += ret_gan
    
    # Retención SUSS
    ret_suss = impuestos.get('retencion_suss', 0) or 0
    if ret_suss > 0:
        result["suss"] = ret_suss
        total += ret_suss
    
    # Retenciones IIBB
    ret_iibb = impuestos.get('retenciones_iibb', [])
    if ret_iibb:
        iibb_list = []
        for r in ret_iibb:
            if isinstance(r, dict):
                monto = r.get('monto', 0) or 0
                if monto > 0:
                    iibb_list.append({
                        "provincia": r.get('provincia'),
                        "monto": monto
                    })
                    total += monto
        if iibb_list:
            result["iibb"] = iibb_list
    
    # Otras retenciones
    otras = impuestos.get('otras_retenciones', 0) or 0
    if otras > 0:
        result["otras"] = otras
        total += otras
    
    result["total_retenciones"] = round(total, 2)
    return result


def _format_otros_impuestos(impuestos: Dict[str, Any]) -> Dict[str, Any]:
    """Formatea otros impuestos."""
    result = {}
    
    internos = impuestos.get('impuestos_internos', 0) or 0
    if internos > 0:
        result["impuestos_internos"] = internos
    
    icl_idc = impuestos.get('icl_idc', 0) or 0
    if icl_idc > 0:
        result["icl_idc"] = icl_idc
    
    return result


# =============================================================================
# FUNCIÓN PRINCIPAL DE CONVERSIÓN PARA MODELO
# =============================================================================

def build_clean_raw_extraction(
    raw_data: Dict[str, Any],
    processed_data: Dict[str, Any],
    validation_result: Dict[str, Any],
    processing_metadata: Dict[str, Any],
    extraction_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Construye el raw_extraction limpio para guardar en el modelo.
    
    Esta es la función principal que se debe usar al guardar en la DB.
    """
    
    # Estructura limpia formateada
    formatted = format_invoice_response(
        processed_data=processed_data,
        validation_result=validation_result,
        processing_metadata=processing_metadata,
        extraction_metadata=extraction_metadata
    )
    
    return {
        # Datos formateados (lo que el usuario quiere ver)
        "factura": formatted["factura"],
        "validacion": formatted["validacion"],
        "alertas": formatted["alertas"],
        "metadata": formatted["metadata"],
        
        # Datos crudos para debugging (opcional, se puede omitir en producción)
        "_debug": {
            "raw_gemini": raw_data,
            "processed": processed_data
        }
    }

