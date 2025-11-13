"""
ViewSet para procesamiento 100% Gemini

Este endpoint realiza extracción usando exclusivamente Gemini 2.5 Flash,
sin usar LlamaExtract. Mantiene la misma estructura de respuesta y
post-procesamiento que el endpoint principal.

Endpoint: POST /api/invoices-gemini/upload-gemini/
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.conf import settings
import logging
import json

from .models import Invoice, InvoiceItem
from .serializers import InvoiceUploadSerializer
from .services_gemini_extractor import GeminiExtractor
from .services import InvoiceExtractionService  # Para parse_date

logger = logging.getLogger(__name__)


class InvoiceGeminiViewSet(viewsets.ViewSet):
    """
    ViewSet para procesamiento de facturas con Gemini 2.5 Flash exclusivamente.
    
    Diferencias con InvoiceViewSet (endpoint principal):
    - Usa GeminiExtractor en lugar de LlamaExtract
    - Retry con Gemini (no con LlamaExtract + Gemini)
    - Mismo post-procesamiento y validaciones
    - Misma estructura de respuesta (legacy_format)
    """
    parser_classes = (MultiPartParser, FormParser)
    
    @action(detail=False, methods=['post'], url_path='upload-gemini')
    def upload_gemini(self, request):
        """
        Procesar factura con Gemini 2.5 Flash exclusivamente.
        
        Request:
            POST /api/invoices-gemini/upload-gemini/
            Content-Type: multipart/form-data
            Body:
                - document (file): The invoice document (PDF, JPG, PNG)
                - schema_type (string, optional): 'completo', 'simplificado', or 'modular' (default: 'completo')
                - segments (array, optional): List of segments to extract (only for schema_type='modular')
                  Example: ["items", "documento"] or ["partes", "fiscalidad"]
                - enable_retry (bool, optional): Enable retry with context if validation score <= 0.8 (default: true)
        
        Examples:
            # Extract everything (default)
            POST /api/invoices/process-gemini/
            Body: document=@invoice.pdf
            
            # Extract only items and documento
            POST /api/invoices/process-gemini/
            Body: document=@invoice.pdf&schema_type=modular&segments=["items","documento"]
            
            # Disable retry
            POST /api/invoices/process-gemini/
            Body: document=@invoice.pdf&enable_retry=false
        
        Response:
            {
                "id": 1,
                "status": "completed",
                "message": "Invoice processed successfully with Gemini",
                "data": {
                    "items": [...],
                    "partes": {...},
                    "documento": {...},
                    "fiscalidad": {...},
                    "metadata": {
                        "validation": {...},
                        "processing": {...},
                        "extraction": {
                            "extraction_time": 12.5,
                            "extraction_method": "gemini-2.5-flash",
                            "schema_type": "completo"
                        },
                        "gemini_retry": {...}  // Si se usó retry
                    }
                }
            }
        """
        # Validar request
        serializer = InvoiceUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document = serializer.validated_data['document']
        
        # Obtener parámetros opcionales
        schema_type = request.data.get('schema_type', 'completo')
        segments = request.data.getlist('segments[]') or request.data.getlist('segments') or None
        enable_retry = request.data.get('enable_retry', 'true').lower() == 'true'
        
        # Parse segments if provided as JSON string
        if segments and isinstance(segments, list) and len(segments) == 1:
            try:
                segments = json.loads(segments[0])
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Crear registro Invoice
        invoice = Invoice.objects.create(
            document=document,
            original_filename=document.name,
            status='processing'
        )
        
        try:
            file_path = invoice.document.path
            
            logger.info("=" * 80)
            logger.info("🤖 [GEMINI ENDPOINT] PROCESAMIENTO CON GEMINI 2.5 FLASH")
            logger.info(f"   Invoice ID: {invoice.id}")
            logger.info(f"   Archivo: {document.name}")
            logger.info(f"   Schema: {schema_type}")
            if segments:
                logger.info(f"   Segmentos: {segments}")
            logger.info(f"   Retry habilitado: {enable_retry}")
            logger.info("=" * 80)
            
            # ================================================================
            # PASO 1: EXTRAER CON GEMINI
            # ================================================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("📤 PASO 1/4: EXTRACCIÓN CON GEMINI 2.5 FLASH")
            logger.info("=" * 80)
            
            gemini_extractor = GeminiExtractor()
            result = gemini_extractor.extract_complete(
                file_path=file_path,
                schema_type=schema_type,
                segments=segments
            )
            
            if not result['success']:
                raise Exception(result.get('error', 'Gemini extraction failed'))
            
            extracted = result['data']
            metadata = result['metadata']
            
            logger.info(f"✅ Extracción completada en {metadata.get('extraction_time', 0):.2f}s")
            
            # ================================================================
            # PASO 2: POST-PROCESAMIENTO
            # ================================================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("🎯 PASO 2/4: POST-PROCESAMIENTO (Normalización + Correcciones + Validaciones)")
            logger.info("=" * 80)
            
            from invoice_extractor.utils.post_processor import InvoicePostProcessor
            
            # Usar post-procesador SIN retry de Gemini (ya usamos Gemini)
            processor = InvoicePostProcessor(
                use_master_validator=True,
                enable_gemini_retry=False  # ❌ NO usar retry porque YA es Gemini
            )
            
            post_processing_result = processor.process(extracted)
            
            processed_data = post_processing_result['processed_data']
            validation_result = post_processing_result['validation_result']
            processing_metadata = post_processing_result['processing_metadata']
            
            validation_score = validation_result.get('validation_score', 0.0)
            logger.info(f"📊 Score inicial: {validation_score:.2%}")
            
            # ================================================================
            # PASO 3: RETRY CON CONTEXTO (SI ES NECESARIO Y ESTÁ HABILITADO)
            # ================================================================
            if enable_retry and validation_score <= 0.8:
                logger.info("")
                logger.info("=" * 80)
                logger.info(f"🔄 PASO 3/4: RETRY CON CONTEXTO (Score bajo: {validation_score:.2%})")
                logger.info("=" * 80)
                
                retry_extracted = gemini_extractor.retry_with_context(
                    file_path=file_path,
                    original_data=extracted,
                    validation_result=validation_result,
                    schema_type=schema_type,
                    segments=segments
                )
                
                if retry_extracted:
                    # Procesar segunda extracción
                    logger.info("🎯 Procesando segunda extracción...")
                    retry_result = processor.process(retry_extracted)
                    retry_score = retry_result['validation_result']['validation_score']
                    
                    logger.info(f"📊 Score con retry: {retry_score:.2%}")
                    
                    # Comparar y elegir mejor
                    if retry_score > validation_score:
                        improvement = (retry_score - validation_score) * 100
                        logger.info(f"✅ RETRY MEJORÓ EL SCORE: {validation_score:.2%} → {retry_score:.2%} (+{improvement:.1f}pp)")
                        
                        # Usar resultado del retry
                        post_processing_result = retry_result
                        processed_data = retry_result['processed_data']
                        validation_result = retry_result['validation_result']
                        processing_metadata = retry_result['processing_metadata']
                        
                        # Agregar metadata de retry
                        processing_metadata['gemini_retry'] = {
                            'was_retried': True,
                            'first_score': validation_score,
                            'second_score': retry_score,
                            'improvement': improvement,
                            'method_used': 'gemini'
                        }
                    else:
                        logger.info(f"ℹ️ Retry no mejoró el score, usando extracción original")
                        # Agregar metadata indicando que se intentó pero no mejoró
                        processing_metadata['gemini_retry'] = {
                            'was_retried': True,
                            'first_score': validation_score,
                            'second_score': retry_score,
                            'improvement': 0,
                            'method_used': 'gemini'
                        }
                else:
                    logger.warning("⚠️ Retry falló, usando resultado original")
            else:
                logger.info("")
                logger.info("=" * 80)
                if not enable_retry:
                    logger.info("ℹ️ PASO 3/4: RETRY DESHABILITADO por parámetro")
                else:
                    logger.info(f"✅ PASO 3/4: RETRY NO NECESARIO (Score aceptable: {validation_score:.2%})")
                logger.info("=" * 80)
            
            # ================================================================
            # PASO 4: CONSTRUIR RESPUESTA EN FORMATO LEGACY
            # ================================================================
            logger.info("")
            logger.info("=" * 80)
            logger.info("📦 PASO 4/4: CONSTRUYENDO RESPUESTA")
            logger.info("=" * 80)
            
            # Construir respuesta en formato legacy (idéntica al endpoint actual)
            legacy_format = {
                **processed_data,  # items, partes, documento, fiscalidad (ya en formato correcto)
                'metadata': {
                    'validation': {
                        'validation_score': validation_result.get('validation_score', 0.0),
                        'confidence_level': validation_result.get('confidence_level', 'unknown'),
                        'has_validation_errors': validation_result.get('has_validation_errors', False),
                        'requires_review': validation_result.get('requires_review', False),
                        'errors_count': len(validation_result.get('errors', [])),
                        'warnings_count': len(validation_result.get('warnings', [])),
                        'alerts_count': len(validation_result.get('alerts', []))
                    },
                    'processing': {
                        'processing_time': processing_metadata.get('processing_time', 0),
                        'processing_timestamp': processing_metadata.get('processing_timestamp'),
                        'pipeline_version': processing_metadata.get('pipeline_version'),
                        'phases_executed': processing_metadata.get('phases_executed', [])
                    },
                    'extraction': {
                        'extraction_time': metadata.get('extraction_time', 0),
                        'extraction_method': metadata.get('extractor', 'gemini-2.5-flash'),
                        'schema_type': metadata.get('schema_type', 'completo')
                    }
                }
            }
            
            # Agregar información de Gemini retry si está disponible
            gemini_retry = processing_metadata.get('gemini_retry', {})
            if gemini_retry.get('was_retried'):
                legacy_format['metadata']['gemini_retry'] = {
                    'used': True,
                    'first_score': gemini_retry.get('first_score', 0),
                    'second_score': gemini_retry.get('second_score', 0),
                    'improvement': gemini_retry.get('improvement', 0),
                    'method_used': gemini_retry.get('method_used', 'gemini')
                }
            
            # ================================================================
            # GUARDAR EN BASE DE DATOS
            # ================================================================
            logger.info("💾 Guardando en base de datos...")
            
            # Store complete raw extraction AND processed data
            invoice.raw_extraction = {
                'raw_data': extracted,  # Datos originales de Gemini
                'processed_data': processed_data,  # Datos después de post-procesamiento
                'validation_result': validation_result,  # Resultado de validaciones
                'processing_metadata': processing_metadata,  # Metadata del procesamiento
                'extraction_metadata': metadata  # Metadata de la extracción (incluye segments si es modular)
            }
            invoice.extraction_time = metadata.get('extraction_time')
            
            # Store schema type with segment information
            if metadata.get('schema_type') == 'modular' and 'segments' in metadata:
                invoice.schema_type = f"modular_{'-'.join(metadata['segments'])}"
            else:
                invoice.schema_type = metadata.get('schema_type', 'completo')
            
            # Guardar validation_score
            invoice.validation_score = validation_result.get('validation_score', 0.0)
            
            # Track extraction method
            invoice.extraction_method = 'gemini'
            gemini_info = processing_metadata.get('gemini_retry', {})
            if gemini_info.get('was_retried'):
                invoice.gemini_retry_used = True
                invoice.gemini_improvement = gemini_info.get('improvement', 0)
            else:
                invoice.gemini_retry_used = False
            
            # Map documento fields (usar datos procesados) - solo si el segmento está presente
            if 'documento' in processed_data:
                documento = processed_data.get('documento', {})
                invoice.tipo_comprobante = documento.get('tipo_comprobante')
                invoice.codigo_comprobante = documento.get('codigo')
                invoice.numero_comprobante = documento.get('numero_comprobante')
                invoice.punto_venta = documento.get('punto_venta')
                invoice.cae = documento.get('cae')
                invoice.moneda = documento.get('moneda') or 'ARS'
                invoice.condicion_venta = documento.get('condicion_venta')
                
                # Parse dates
                extraction_service = InvoiceExtractionService()
                if documento.get('fecha_emision'):
                    invoice.fecha_emision = extraction_service.parse_date(
                        documento['fecha_emision']
                    )
                if documento.get('fecha_vencimiento_cae'):
                    invoice.fecha_vencimiento_cae = extraction_service.parse_date(
                        documento['fecha_vencimiento_cae']
                    )
            
            # Map partes (parties) fields - solo si el segmento está presente
            if 'partes' in processed_data:
                partes = processed_data.get('partes', {})
                
                # Empresa (vendor)
                empresa = partes.get('empresa', {})
                invoice.empresa_razon_social = empresa.get('razon_social')
                invoice.empresa_cuit = empresa.get('cuit')
                invoice.empresa_condicion_iva = empresa.get('condicion_iva')
                invoice.empresa_ingresos_brutos = empresa.get('ingresos_brutos')
                invoice.empresa_provincia = empresa.get('provincia')
                
                # Combine address fields for empresa
                domicilio_parts = []
                if empresa.get('domicilio_comercial'):
                    domicilio_parts.append(empresa['domicilio_comercial'])
                if empresa.get('domicilio_calle'):
                    domicilio_parts.append(empresa['domicilio_calle'])
                if empresa.get('domicilio_localidad'):
                    domicilio_parts.append(empresa['domicilio_localidad'])
                invoice.empresa_domicilio = ' - '.join(domicilio_parts) if domicilio_parts else None
                
                # Cliente (customer)
                cliente = partes.get('cliente', {})
                invoice.cliente_nombre = cliente.get('apellido_nombre_razon_social')
                invoice.cliente_cuit = cliente.get('cuit')
                invoice.cliente_condicion_iva = cliente.get('condicion_iva')
                invoice.cliente_provincia = cliente.get('provincia')
                
                # Combine address fields for cliente
                cliente_domicilio_parts = []
                if cliente.get('domicilio'):
                    cliente_domicilio_parts.append(cliente['domicilio'])
                if cliente.get('domicilio_calle'):
                    cliente_domicilio_parts.append(cliente['domicilio_calle'])
                if cliente.get('domicilio_localidad'):
                    cliente_domicilio_parts.append(cliente['domicilio_localidad'])
                invoice.cliente_domicilio = ' - '.join(cliente_domicilio_parts) if cliente_domicilio_parts else None
            
            # Map fiscalidad (fiscal) fields - solo si el segmento está presente
            if 'fiscalidad' in processed_data or 'totales' in processed_data:
                # Si 'fiscalidad' está presente, úsalo
                if 'fiscalidad' in processed_data:
                    fiscalidad = processed_data.get('fiscalidad', {})
                    
                    # Totales
                    totales = fiscalidad.get('totales', {})
                    invoice.subtotal_gravado = totales.get('subtotal_gravado')
                    invoice.importe_total = totales.get('importe_total')
                    invoice.descuentos = totales.get('descuentos', 0)
                    
                    # Calculos
                    calculos = fiscalidad.get('calculos', {})
                    invoice.items_count = calculos.get('items_count')
                    invoice.diferencia_matematica = calculos.get('diferencia_matematica', 0)
                    
                    # Impuestos
                    impuestos = fiscalidad.get('impuestos', {})
                    
                    # Calculate total IVA
                    iva_dict = impuestos.get('iva', {})
                    invoice.total_iva = sum(float(v) for v in iva_dict.values() if v)
                    
                    # Calculate total percepciones
                    percepcion_iva = impuestos.get('percepcion_iva', 0)
                    percepcion_ganancias = impuestos.get('percepcion_ganancias', 0)
                    percepcion_iibb_list = impuestos.get('percepcion_iibb', [])
                    percepcion_iibb_total = sum(p.get('monto', 0) for p in percepcion_iibb_list if isinstance(p, dict))
                    invoice.total_percepciones = percepcion_iva + percepcion_ganancias + percepcion_iibb_total
                    
                    # Calculate total retenciones
                    retencion_iva = impuestos.get('retencion_iva', 0) or 0
                    retencion_ganancias = impuestos.get('retencion_ganancias', 0) or 0
                    retencion_suss = impuestos.get('retencion_suss', 0) or 0
                    invoice.total_retenciones = retencion_iva + retencion_ganancias + retencion_suss
                
                # Si solo 'totales' está presente (sin fiscalidad completa)
                elif 'totales' in processed_data:
                    totales = processed_data.get('totales', {})
                    invoice.subtotal_gravado = totales.get('subtotal_gravado')
                    invoice.importe_total = totales.get('importe_total')
                    invoice.descuentos = totales.get('descuentos', 0)
            
            invoice.status = 'completed'
            invoice.processed_at = timezone.now()
            invoice.save()
            
            # Create line items - solo si el segmento 'items' está presente
            if 'items' in processed_data:
                items_data = processed_data.get('items', [])
                for idx, item_data in enumerate(items_data):
                    if isinstance(item_data, dict):
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            codigo=item_data.get('codigo'),
                            descripcion=item_data.get('descripcion', ''),
                            cantidad=item_data.get('cantidad', 0),
                            unidad_medida=item_data.get('unidad_medida'),
                            precio_unitario=item_data.get('precio_unitario', 0),
                            subtotal=item_data.get('subtotal', 0),
                            order=idx
                        )
            
            logger.info("=" * 80)
            logger.info("✅ PROCESAMIENTO COMPLETADO CON GEMINI")
            logger.info(f"   Invoice ID: {invoice.id}")
            logger.info(f"   Validation Score: {validation_result.get('validation_score', 0):.2%}")
            logger.info(f"   Extraction Method: gemini-2.5-flash")
            logger.info(f"   Retry Used: {invoice.gemini_retry_used}")
            logger.info("=" * 80)
            
            return Response(
                {
                    'id': invoice.id,
                    'status': 'completed',
                    'message': 'Invoice processed successfully with Gemini',
                    'data': legacy_format
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            # Handle unexpected errors
            error_detail = str(e)
            invoice.status = 'failed'
            invoice.error_message = error_detail
            invoice.save()
            
            # Log the error for debugging
            logger.exception(f"Unexpected error processing invoice {invoice.id} with Gemini")
            
            # Don't expose internal error details in production
            error_response = {
                'id': invoice.id,
                'status': 'failed',
                'message': 'An error occurred during processing with Gemini'
            }
            
            # Only include error details in debug mode
            if settings.DEBUG:
                error_response['error'] = error_detail
            
            return Response(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

