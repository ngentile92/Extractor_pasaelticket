"""
🎯 Base Views - Lógica compartida para endpoints de extracción

Este módulo contiene la lógica común que se usa tanto en views.py (LlamaExtract)
como en views_gemini.py (Gemini). Evita duplicación de código.

Funcionalidades:
- Validación de archivos subidos
- Preprocesamiento de imágenes
- Post-procesamiento de datos
- Mapeo a modelo Django
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple

from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTES
# =============================================================================

ALLOWED_EXTENSIONS = {'.jpeg', '.jpg', '.png', '.pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# =============================================================================
# VALIDACIÓN DE ARCHIVOS
# =============================================================================

def validate_uploaded_file(request) -> Tuple[Optional[Any], Optional[Response]]:
    """
    Validar archivo subido en el request.
    
    Args:
        request: Request de Django REST Framework
    
    Returns:
        Tuple de (file, error_response)
        - Si es válido: (file, None)
        - Si hay error: (None, Response)
    """
    if 'file' not in request.FILES:
        return None, Response(
            {"error": "No se proporcionó archivo. Use el campo 'file'"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['file']
    
    # Validar extensión
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return None, Response(
            {"error": f"Tipo de archivo no soportado: {file_ext}. Formatos permitidos: {ALLOWED_EXTENSIONS}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar tamaño
    if uploaded_file.size > MAX_FILE_SIZE:
        return None, Response(
            {"error": f"Archivo demasiado grande. Máximo: {MAX_FILE_SIZE // 1024 // 1024}MB"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return uploaded_file, None


# =============================================================================
# PREPROCESAMIENTO DE IMÁGENES
# =============================================================================

def preprocess_image_if_needed(file_path: str, enable_preprocessing: bool = True) -> str:
    """
    Preprocesar imagen si está habilitado y es una imagen.
    
    Args:
        file_path: Ruta al archivo original
        enable_preprocessing: Si se debe preprocesar
    
    Returns:
        Ruta al archivo (preprocesado o original)
    """
    if not enable_preprocessing:
        return file_path
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Solo preprocesar imágenes, no PDFs
    if file_ext not in {'.jpeg', '.jpg', '.png'}:
        logger.info(f"📄 Archivo {file_ext} - sin preprocesamiento de imagen")
        return file_path
    
    try:
        from invoice_extractor.utils.image_preprocessor import preprocess_invoice_image
        
        processed_path = preprocess_invoice_image(file_path)
        if processed_path and processed_path != file_path:
            logger.info(f"✅ Imagen preprocesada: {os.path.basename(processed_path)}")
            return processed_path
    except Exception as e:
        logger.warning(f"⚠️ Error en preprocesamiento: {e}. Usando imagen original.")
    
    return file_path


# =============================================================================
# POST-PROCESAMIENTO DE DATOS
# =============================================================================

def apply_post_processing(
    extracted_data: Dict[str, Any],
    file_path: Optional[str] = None,
    enable_retry: bool = True,
    retry_score_threshold: float = 0.7
) -> Tuple[Dict[str, Any], float]:
    """
    Aplicar post-procesamiento completo a datos extraídos.
    
    Args:
        extracted_data: Datos extraídos del modelo
        file_path: Ruta al archivo original (para retry)
        enable_retry: Habilitar retry con Gemini si el score es bajo
        retry_score_threshold: Umbral de score para trigger retry
    
    Returns:
        Tuple de (processed_data, validation_score)
    """
    from invoice_extractor.utils.post_processor import InvoicePostProcessor
    
    # Crear procesador
    processor = InvoicePostProcessor(
        use_master_validator=True,
        enable_fiscal_inference=True
    )
    
    # Procesar con o sin retry según disponibilidad de file_path
    if file_path and enable_retry:
        result = processor.process_with_gemini_retry(
            extracted_data,
            file_path=file_path
        )
    else:
        result = processor.process(extracted_data)
    
    # Obtener score de validación
    validation_score = result.get('validation_score', 0.0)
    if 'validation' in result:
        validation_score = result['validation'].get('confidence_score', validation_score)
    
    return result, validation_score


# =============================================================================
# MAPEO A MODELO DJANGO
# =============================================================================

def map_to_invoice_model(
    extracted_data: Dict[str, Any],
    file_instance,
    validation_score: float = 0.0
) -> Dict[str, Any]:
    """
    Mapear datos extraídos al modelo Invoice de Django.
    
    Args:
        extracted_data: Datos procesados
        file_instance: Instancia del archivo guardado
        validation_score: Score de validación
    
    Returns:
        Diccionario con datos para crear Invoice
    """
    from invoice_extractor.models import Invoice
    
    # Obtener campos de manera segura
    items = extracted_data.get('items', [])
    partes = extracted_data.get('partes', {})
    documento = extracted_data.get('documento', {})
    fiscalidad = extracted_data.get('fiscalidad', {})
    
    # Empresa y cliente
    empresa = partes.get('empresa', {})
    cliente = partes.get('cliente', {})
    
    # Totales e impuestos
    totales = fiscalidad.get('totales', {})
    impuestos = fiscalidad.get('impuestos', {})
    iva_dict = impuestos.get('iva', {})
    
    # Construir datos del modelo
    invoice_data = {
        'file': file_instance,
        'validation_score': validation_score,
        'raw_extracted_data': extracted_data,
        
        # Documento
        'tipo_comprobante': documento.get('tipo_comprobante', ''),
        'codigo': documento.get('codigo', ''),
        'numero_comprobante': documento.get('numero_comprobante', ''),
        'punto_venta': documento.get('punto_venta', ''),
        'fecha_emision': _parse_date(documento.get('fecha_emision')),
        'cae': documento.get('cae'),
        'fecha_vencimiento_cae': _parse_date(documento.get('fecha_vencimiento_cae')),
        'moneda': documento.get('moneda', 'ARS'),
        'condicion_venta': documento.get('condicion_venta'),
        
        # Empresa
        'empresa_razon_social': empresa.get('razon_social', ''),
        'empresa_cuit': empresa.get('cuit', ''),
        'empresa_condicion_iva': empresa.get('condicion_iva', ''),
        'empresa_ingresos_brutos': empresa.get('ingresos_brutos'),
        'empresa_domicilio_comercial': empresa.get('domicilio_comercial'),
        
        # Cliente
        'cliente_nombre': cliente.get('apellido_nombre_razon_social', ''),
        'cliente_cuit': cliente.get('cuit'),
        'cliente_condicion_iva': cliente.get('condicion_iva'),
        'cliente_domicilio': cliente.get('domicilio'),
        
        # Items (JSON)
        'items': items,
        
        # Totales
        'subtotal_gravado': _parse_float(totales.get('subtotal_gravado', 0)),
        'descuentos': _parse_float(totales.get('descuentos', 0)),
        'importe_total': _parse_float(totales.get('importe_total', 0)),
        
        # IVA
        'iva_21': _parse_float(iva_dict.get('21', 0)),
        'iva_105': _parse_float(iva_dict.get('105', 0) or iva_dict.get('10.5', 0)),
        'iva_27': _parse_float(iva_dict.get('27', 0)),
        
        # Percepciones
        'percepcion_iva': _parse_float(impuestos.get('percepcion_iva', 0)),
        'percepcion_iibb': impuestos.get('percepcion_iibb', []),
        
        # Otros
        'impuestos_internos': _parse_float(impuestos.get('impuestos_internos', 0)),
    }
    
    return invoice_data


def _parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parsear fecha de varios formatos a YYYY-MM-DD."""
    if not date_str:
        return None
    
    from datetime import datetime
    
    # Intentar varios formatos
    formats = [
        '%d/%m/%Y',
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%Y/%m/%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    # Si no se puede parsear, devolver None
    logger.warning(f"⚠️ No se pudo parsear fecha: {date_str}")
    return None


def _parse_float(value) -> float:
    """Parsear valor a float de manera segura."""
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        # Limpiar y convertir
        cleaned = value.replace(',', '.').replace('$', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    return 0.0


# =============================================================================
# CONSTRUCCIÓN DE RESPUESTA
# =============================================================================

def build_extraction_response(
    extracted_data: Dict[str, Any],
    validation_score: float,
    extraction_time: float,
    extractor_name: str,
    additional_meta: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construir respuesta estandarizada para endpoints de extracción.
    
    Args:
        extracted_data: Datos extraídos y procesados
        validation_score: Score de validación (0-1)
        extraction_time: Tiempo de extracción en segundos
        extractor_name: Nombre del extractor usado
        additional_meta: Metadatos adicionales
    
    Returns:
        Diccionario con respuesta formateada
    """
    response = {
        'success': True,
        'data': extracted_data,
        'meta': {
            'extractor': extractor_name,
            'validation_score': round(validation_score, 4),
            'extraction_time_seconds': round(extraction_time, 2),
            'score_interpretation': _interpret_score(validation_score),
        }
    }
    
    if additional_meta:
        response['meta'].update(additional_meta)
    
    # Agregar alertas si existen
    if 'validation' in extracted_data:
        validation = extracted_data['validation']
        response['alerts'] = validation.get('alerts', [])
        response['errors'] = validation.get('validation_errors', [])
    
    return response


def _interpret_score(score: float) -> str:
    """Interpretar score de validación."""
    if score >= 0.9:
        return "excelente"
    elif score >= 0.8:
        return "bueno"
    elif score >= 0.7:
        return "aceptable"
    elif score >= 0.5:
        return "bajo"
    else:
        return "muy_bajo"

