from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.core.files.storage import default_storage
from django.conf import settings
import logging

from .models import Invoice, InvoiceItem
from .serializers import (
    InvoiceSerializer, 
    InvoiceUploadSerializer,
    InvoiceItemSerializer
)
from .services import InvoiceExtractionService
from .utils.post_processor import process_invoice

logger = logging.getLogger(__name__)


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoices
    
    Main endpoint for processing Argentine invoice documents
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'upload':
            return InvoiceUploadSerializer
        return InvoiceSerializer
    
    @action(detail=False, methods=['post'], url_path='process')
    def upload(self, request):
        """
        Main endpoint to upload and process invoice documents from Argentina
        
        This endpoint accepts an invoice document (PDF, JPG, PNG, or DOCX),
        stores it, and uses Llamaindex to extract relevant invoice data.
        
        MODULAR EXTRACTION:
        You can specify which segments to extract using the 'segments' parameter.
        Available segments:
        - 'items': Line items / productos
        - 'partes': Emisor y receptor y sus datos
        - 'documento': Datos del documento en sí
        - 'fiscalidad': Totales e impuestos
        - 'totales': Totales varios (solo si fiscalidad no está incluida)
        
        Request:
            POST /api/invoices/process/
            Content-Type: multipart/form-data
            Body: 
                - document (file): The invoice document
                - schema_type (string, optional): 'completo', 'simplificado', or 'modular' (default: 'completo')
                - segments (array, optional): List of segments to extract (only for schema_type='modular')
                  Example: ["items", "documento"] or ["partes", "fiscalidad"]
        
        Examples:
            # Extract everything (default)
            POST /api/invoices/process/
            Body: document=@invoice.pdf
            
            # Extract only items and documento
            POST /api/invoices/process/
            Body: document=@invoice.pdf&schema_type=modular&segments=["items","documento"]
            
            # Extract only partes and fiscalidad
            POST /api/invoices/process/
            Body: document=@invoice.pdf&schema_type=modular&segments=["partes","fiscalidad"]
        
        Response:
            {
                "id": 1,
                "status": "completed",
                "message": "Invoice processed successfully",
                "data": { ... }
            }
        """
        serializer = InvoiceUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document = serializer.validated_data['document']
        
        # Get optional parameters
        schema_type = request.data.get('schema_type', 'completo')
        segments = request.data.getlist('segments[]') or request.data.getlist('segments') or None
        use_gemini_only = request.data.get('use_gemini_only', 'false').lower() == 'true'  # Toggle para usar SOLO Gemini (sin LlamaExtract)
        
        # Parse segments if provided as JSON string
        if segments and isinstance(segments, list) and len(segments) == 1:
            try:
                import json
                segments = json.loads(segments[0])
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Create invoice record
        invoice = Invoice.objects.create(
            document=document,
            original_filename=document.name,
            status='processing'
        )
        
        try:
            file_path = invoice.document.path
            
            # OPCIÓN 1: Usar SOLO Gemini (sin LlamaExtract)
            if use_gemini_only:
                logger.warning("=" * 80)
                logger.warning("🔥 USE_GEMINI_ONLY ACTIVADO - Extrayendo directo con Gemini 2.5 Flash")
                logger.warning("=" * 80)
                
                from invoice_extractor.services_gemini_corrector import GeminiCorrector
                gemini = GeminiCorrector()
                
                # Extraer directo con Gemini (sin datos previos, sin errores de contexto)
                gemini_result = gemini.retry_extraction_with_gemini(
                    file_path=file_path,
                    original_data={},  # No hay datos previos
                    validation_result={"validation_errors": ["Extracción directa con Gemini solicitada"]}
                )
                
                if not gemini_result:
                    raise Exception("Gemini no pudo extraer datos")
                
                # Crear estructura compatible con el resto del código
                extracted = gemini_result
                metadata = {
                    'extraction_time': 0,
                    'schema_type': 'gemini_direct',
                    'extractor': 'gemini-2.5-flash'
                }
            
            # OPCIÓN 2: Usar LlamaExtract (flujo normal)
            else:
                # Process the document using LlamaExtract
                logger.info(f"Initializing extraction service with schema_type={schema_type}, segments={segments}")
                extraction_service = InvoiceExtractionService(schema_type=schema_type, segments=segments)
                
                result = extraction_service.extract_invoice_data(file_path)
                
                if not result['success']:
                    raise Exception(result.get('error', 'Unknown extraction error'))
                
                # Post-process extracted data
                extracted = result['data']
                metadata = result.get('metadata', {})
            
            # Continuar con post-procesamiento (común para ambos casos)
            if extracted:
                
                # 🎯 POST-PROCESAMIENTO: Normalización, correcciones y validaciones
                logger.warning("=" * 80)
                logger.warning("🎯 [VIEWS] Iniciando post-procesamiento...")
                logger.warning(f"   file_path: {file_path}")
                logger.warning(f"   use_gemini_only: {use_gemini_only}")
                logger.warning("=" * 80)
                
                from invoice_extractor.utils.post_processor import InvoicePostProcessor
                
                # Si usamos Gemini directo, no necesitamos retry (ya usamos Gemini)
                if use_gemini_only:
                    processor = InvoicePostProcessor(enable_gemini_retry=False)
                    post_processing_result = processor.process(extracted)
                else:
                    # Flujo normal: LlamaExtract + posible retry con Gemini
                    processor = InvoicePostProcessor(enable_gemini_retry=True)
                    logger.warning("🎯 [VIEWS] Llamando a process_with_gemini_retry...")
                    post_processing_result = processor.process_with_gemini_retry(
                        extracted_data=extracted,
                        file_path=file_path
                    )
                    logger.warning("🎯 [VIEWS] process_with_gemini_retry completado")
                
                # Usar datos procesados en lugar de crudos
                processed_data = post_processing_result['processed_data']
                validation_result = post_processing_result['validation_result']
                processing_metadata = post_processing_result['processing_metadata']
                
                # Construir respuesta en formato legacy (estructura nativa ya es correcta desde schemas)
                legacy_format = {
                    **processed_data,  # items, partes, documento, fiscalidad (ya en formato correcto)
                    'metadata': {
                        'validation': {
                            'validation_score': validation_result.get('validation_score', 0.0),
                            'confidence_level': validation_result.get('confidence_level', 'unknown'),
                            'has_validation_errors': validation_result.get('has_validation_errors', False),
                            'requires_review': validation_result.get('requires_review', False),
                            'errors_count': len(validation_result.get('validation_errors', [])),
                            'warnings_count': len(validation_result.get('validation_warnings', [])),
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
                            'extraction_method': metadata.get('extractor', 'llamaextract'),
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
                        'method_used': gemini_retry.get('method_used', 'llamaextract')
                    }
                
                # Store complete raw extraction AND processed data
                invoice.raw_extraction = {
                    'raw_data': extracted,  # Datos originales de LlamaExtract
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
                
                # Track extraction method and Gemini usage
                gemini_info = processing_metadata.get('gemini_retry', {})
                if use_gemini_only:
                    invoice.extraction_method = 'gemini'
                    invoice.gemini_retry_used = True
                elif gemini_info.get('used'):
                    invoice.extraction_method = 'both'
                    invoice.gemini_retry_used = True
                    invoice.gemini_improvement = gemini_info.get('improvement', 0)
                else:
                    invoice.extraction_method = 'llama'
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
                
                return Response(
                    {
                        'id': invoice.id,
                        'status': 'completed',
                        'message': 'Invoice processed successfully',
                        'data': legacy_format  # Retornar formato legacy (estructura original)
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                # Processing failed
                error_detail = result.get('error', 'Unknown error')
                invoice.status = 'failed'
                invoice.error_message = error_detail
                invoice.save()
                
                # Log the error for debugging
                logger.error(f"Invoice {invoice.id} processing failed: {error_detail}")
                
                # Don't expose internal error details in production
                error_response = {
                    'id': invoice.id,
                    'status': 'failed',
                    'message': 'Failed to process invoice'
                }
                
                # Only include error details in debug mode
                if settings.DEBUG:
                    error_response['error'] = error_detail
                
                return Response(
                    error_response,
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            # Handle unexpected errors
            error_detail = str(e)
            invoice.status = 'failed'
            invoice.error_message = error_detail
            invoice.save()
            
            # Log the error for debugging
            logger.exception(f"Unexpected error processing invoice {invoice.id}")
            
            # Don't expose internal error details in production
            error_response = {
                'id': invoice.id,
                'status': 'failed',
                'message': 'An error occurred during processing'
            }
            
            # Only include error details in debug mode
            if settings.DEBUG:
                error_response['error'] = error_detail
            
            return Response(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def reprocess(self, request, pk=None):
        """
        Reprocess an existing invoice document
        
        Request:
            GET /api/invoices/{id}/reprocess/
        """
        invoice = self.get_object()
        
        if not invoice.document:
            return Response(
                {'error': 'No document found for this invoice'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'processing'
        invoice.save()
        
        try:
            extraction_service = InvoiceExtractionService()
            result = extraction_service.extract_invoice_data(invoice.document.path)
            
            if result['success']:
                extracted = result['data']
                
                # Update fields similar to upload endpoint
                invoice.invoice_number = extracted.get('invoice_number')
                invoice.vendor_name = extracted.get('vendor_name')
                invoice.vendor_cuit = extracted.get('vendor_cuit')
                invoice.raw_extraction = extracted
                invoice.status = 'completed'
                invoice.processed_at = timezone.now()
                invoice.save()
                
                return Response(
                    {
                        'id': invoice.id,
                        'status': 'completed',
                        'message': 'Invoice reprocessed successfully',
                        'data': InvoiceSerializer(invoice).data
                    }
                )
            else:
                error_detail = result.get('error')
                invoice.status = 'failed'
                invoice.error_message = error_detail
                invoice.save()
                
                # Log the error for debugging
                logger.error(f"Invoice {invoice.id} reprocessing failed: {error_detail}")
                
                # Don't expose internal error details in production
                error_response = {
                    'error': 'Failed to reprocess invoice'
                }
                
                # Only include error details in debug mode
                if settings.DEBUG:
                    error_response['details'] = error_detail
                
                return Response(
                    error_response,
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            error_detail = str(e)
            invoice.status = 'failed'
            invoice.error_message = error_detail
            invoice.save()
            
            # Log the error for debugging
            logger.exception(f"Unexpected error reprocessing invoice {invoice.id}")
            
            # Don't expose internal error details in production
            error_response = {'error': 'An error occurred during reprocessing'}
            
            # Only include error details in debug mode
            if settings.DEBUG:
                error_response['details'] = error_detail
            
            return Response(
                error_response,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
