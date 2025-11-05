# invoice_extractor/views_batch.py
"""
Batch processing endpoint for multiple invoices in parallel
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.conf import settings
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from .models import Invoice, InvoiceItem
from .services import InvoiceExtractionService

logger = logging.getLogger(__name__)


class InvoiceBatchViewSet(viewsets.ViewSet):
    """
    ViewSet for batch processing of multiple invoices
    """
    parser_classes = (MultiPartParser, FormParser)
    
    @action(detail=False, methods=['post'], url_path='process-batch')
    def upload_batch(self, request):
        """
        Endpoint para procesar múltiples facturas en paralelo (hasta 8 simultáneas)
        
        Este endpoint acepta múltiples documentos de facturas y los procesa en paralelo
        para mayor eficiencia.
        
        Request:
            POST /api/invoices/process-batch/
            Content-Type: multipart/form-data
            Body:
                - documents (files[]): Lista de documentos (hasta 8)
                - schema_type (string, optional): 'completo', 'simplificado', or 'modular' (default: 'completo')
                - segments (array, optional): List of segments to extract (only for schema_type='modular')
                - use_gemini_only (bool, optional): Usar solo Gemini sin LlamaExtract
        
        Examples:
            # Procesar 3 facturas simultáneamente
            curl -X POST http://localhost:8000/api/invoices/process-batch/ \
              -F "documents=@factura1.pdf" \
              -F "documents=@factura2.jpg" \
              -F "documents=@factura3.png"
        
        Response:
            {
                "total": 3,
                "successful": 2,
                "failed": 1,
                "results": [
                    {
                        "id": 1,
                        "status": "completed",
                        "filename": "factura1.pdf",
                        "data": {...}
                    },
                    {
                        "id": 2,
                        "status": "completed",
                        "filename": "factura2.jpg",
                        "data": {...}
                    },
                    {
                        "id": 3,
                        "status": "failed",
                        "filename": "factura3.png",
                        "error": "Extraction failed"
                    }
                ],
                "processing_time": 15.3
            }
        """
        start_time = time.time()
        
        # Get uploaded files
        documents = request.FILES.getlist('documents')
        
        if not documents:
            return Response(
                {'error': 'No documents provided. Use "documents" field for file uploads.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(documents) > 8:
            return Response(
                {'error': f'Maximum 8 documents allowed, got {len(documents)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get optional parameters (same for all documents)
        schema_type = request.data.get('schema_type', 'completo')
        segments = request.data.getlist('segments[]') or request.data.getlist('segments') or None
        use_gemini_only = request.data.get('use_gemini_only', 'false').lower() == 'true'
        
        # Parse segments if provided as JSON string
        if segments and isinstance(segments, list) and len(segments) == 1:
            try:
                import json
                segments = json.loads(segments[0])
            except (json.JSONDecodeError, ValueError):
                pass
        
        logger.info(f"📦 Batch processing {len(documents)} documents...")
        
        # Function to process a single document
        def process_single_document(document):
            """Process a single document and return result"""
            try:
                # Create invoice record
                invoice = Invoice.objects.create(
                    document=document,
                    original_filename=document.name,
                    status='processing'
                )
                
                file_path = invoice.document.path
                
                # Extract data (same logic as upload endpoint)
                if use_gemini_only:
                    from invoice_extractor.services_gemini_corrector import GeminiCorrector
                    gemini = GeminiCorrector()
                    gemini_result = gemini.retry_extraction_with_gemini(
                        file_path=file_path,
                        original_data={},
                        validation_result={"validation_errors": ["Extracción directa con Gemini solicitada"]}
                    )
                    
                    if not gemini_result:
                        raise Exception("Gemini no pudo extraer datos")
                    
                    extracted = gemini_result
                    metadata = {
                        'extraction_time': 0,
                        'schema_type': 'gemini_direct',
                        'extractor': 'gemini-2.5-flash'
                    }
                else:
                    extraction_service = InvoiceExtractionService(schema_type=schema_type, segments=segments)
                    result = extraction_service.extract_invoice_data(file_path)
                    
                    if not result['success']:
                        raise Exception(result.get('error', 'Unknown extraction error'))
                    
                    extracted = result['data']
                    metadata = result.get('metadata', {})
                
                # Post-process
                from invoice_extractor.utils.post_processor import InvoicePostProcessor
                
                if use_gemini_only:
                    processor = InvoicePostProcessor(enable_gemini_retry=False)
                    post_processing_result = processor.process(extracted)
                else:
                    processor = InvoicePostProcessor(enable_gemini_retry=True)
                    post_processing_result = processor.process_with_gemini_retry(
                        extracted_data=extracted,
                        file_path=file_path
                    )
                
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
                
                # Store data
                invoice.raw_extraction = {
                    'raw_data': extracted,
                    'processed_data': processed_data,
                    'validation_result': validation_result,
                    'processing_metadata': processing_metadata,
                    'extraction_metadata': metadata
                }
                invoice.extraction_time = metadata.get('extraction_time')
                
                # Store schema type
                if metadata.get('schema_type') == 'modular' and 'segments' in metadata:
                    invoice.schema_type = f"modular_{'-'.join(metadata['segments'])}"
                else:
                    invoice.schema_type = metadata.get('schema_type', 'completo')
                
                # Store validation score
                invoice.validation_score = validation_result.get('validation_score', 0.0)
                
                # Track extraction method
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
                
                # Map fields (same as upload endpoint)
                if 'documento' in processed_data:
                    documento = processed_data.get('documento', {})
                    invoice.tipo_comprobante = documento.get('tipo_comprobante')
                    invoice.codigo_comprobante = documento.get('codigo')
                    invoice.numero_comprobante = documento.get('numero_comprobante')
                    invoice.punto_venta = documento.get('punto_venta')
                    invoice.cae = documento.get('cae')
                    invoice.moneda = documento.get('moneda') or 'ARS'
                    invoice.condicion_venta = documento.get('condicion_venta')
                    
                    if documento.get('fecha_emision'):
                        invoice.fecha_emision = extraction_service.parse_date(documento['fecha_emision'])
                    if documento.get('fecha_vencimiento_cae'):
                        invoice.fecha_vencimiento_cae = extraction_service.parse_date(documento['fecha_vencimiento_cae'])
                
                if 'partes' in processed_data:
                    partes = processed_data.get('partes', {})
                    empresa = partes.get('empresa', {})
                    invoice.empresa_razon_social = empresa.get('razon_social')
                    invoice.empresa_cuit = empresa.get('cuit')
                    invoice.empresa_condicion_iva = empresa.get('condicion_iva')
                    invoice.empresa_ingresos_brutos = empresa.get('ingresos_brutos')
                    invoice.empresa_provincia = empresa.get('provincia')
                    
                    domicilio_parts = []
                    if empresa.get('domicilio_comercial'):
                        domicilio_parts.append(empresa['domicilio_comercial'])
                    if empresa.get('domicilio_calle'):
                        domicilio_parts.append(empresa['domicilio_calle'])
                    if empresa.get('domicilio_localidad'):
                        domicilio_parts.append(empresa['domicilio_localidad'])
                    invoice.empresa_domicilio = ' - '.join(domicilio_parts) if domicilio_parts else None
                    
                    cliente = partes.get('cliente', {})
                    invoice.cliente_nombre = cliente.get('apellido_nombre_razon_social')
                    invoice.cliente_cuit = cliente.get('cuit')
                    invoice.cliente_condicion_iva = cliente.get('condicion_iva')
                    invoice.cliente_provincia = cliente.get('provincia')
                    
                    cliente_domicilio_parts = []
                    if cliente.get('domicilio'):
                        cliente_domicilio_parts.append(cliente['domicilio'])
                    if cliente.get('domicilio_calle'):
                        cliente_domicilio_parts.append(cliente['domicilio_calle'])
                    if cliente.get('domicilio_localidad'):
                        cliente_domicilio_parts.append(cliente['domicilio_localidad'])
                    invoice.cliente_domicilio = ' - '.join(cliente_domicilio_parts) if cliente_domicilio_parts else None
                
                if 'fiscalidad' in processed_data or 'totales' in processed_data:
                    if 'fiscalidad' in processed_data:
                        fiscalidad = processed_data.get('fiscalidad', {})
                        totales = fiscalidad.get('totales', {})
                        invoice.subtotal_gravado = totales.get('subtotal_gravado')
                        invoice.importe_total = totales.get('importe_total')
                        invoice.descuentos = totales.get('descuentos', 0)
                        
                        calculos = fiscalidad.get('calculos', {})
                        invoice.items_count = calculos.get('items_count')
                        invoice.diferencia_matematica = calculos.get('diferencia_matematica', 0)
                        
                        impuestos = fiscalidad.get('impuestos', {})
                        iva_dict = impuestos.get('iva', {})
                        invoice.total_iva = sum(float(v) for v in iva_dict.values() if v)
                        
                        percepcion_iva = impuestos.get('percepcion_iva', 0)
                        percepcion_ganancias = impuestos.get('percepcion_ganancias', 0)
                        percepcion_iibb_list = impuestos.get('percepcion_iibb', [])
                        percepcion_iibb_total = sum(p.get('monto', 0) for p in percepcion_iibb_list if isinstance(p, dict))
                        invoice.total_percepciones = percepcion_iva + percepcion_ganancias + percepcion_iibb_total
                        
                        retencion_iva = impuestos.get('retencion_iva', 0) or 0
                        retencion_ganancias = impuestos.get('retencion_ganancias', 0) or 0
                        retencion_suss = impuestos.get('retencion_suss', 0) or 0
                        invoice.total_retenciones = retencion_iva + retencion_ganancias + retencion_suss
                    elif 'totales' in processed_data:
                        totales = processed_data.get('totales', {})
                        invoice.subtotal_gravado = totales.get('subtotal_gravado')
                        invoice.importe_total = totales.get('importe_total')
                        invoice.descuentos = totales.get('descuentos', 0)
                
                invoice.status = 'completed'
                invoice.processed_at = timezone.now()
                invoice.save()
                
                # Create line items
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
                
                return {
                    'success': True,
                    'id': invoice.id,
                    'status': 'completed',
                    'filename': document.name,
                    'data': legacy_format
                }
                
            except Exception as e:
                logger.exception(f"Error processing document {document.name}")
                
                # Try to mark invoice as failed if it was created
                try:
                    if 'invoice' in locals():
                        invoice.status = 'failed'
                        invoice.error_message = str(e)
                        invoice.save()
                        invoice_id = invoice.id
                    else:
                        invoice_id = None
                except:
                    invoice_id = None
                
                return {
                    'success': False,
                    'id': invoice_id,
                    'status': 'failed',
                    'filename': document.name,
                    'error': str(e) if settings.DEBUG else 'Processing failed'
                }
        
        # Process documents in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(documents), 8)) as executor:
            results = list(executor.map(process_single_document, documents))
        
        # Calculate statistics
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        processing_time = time.time() - start_time
        
        logger.info(f"✅ Batch processing completed: {successful}/{len(documents)} successful in {processing_time:.2f}s")
        
        return Response(
            {
                'total': len(documents),
                'successful': successful,
                'failed': failed,
                'results': results,
                'processing_time': round(processing_time, 2)
            },
            status=status.HTTP_200_OK
        )

