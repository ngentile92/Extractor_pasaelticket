# invoice_extractor/views_batch.py
"""
Batch processing endpoint for multiple invoices in parallel using Gemini
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
from .services_gemini_extractor import GeminiExtractor
from .authentication import APIKeyAuthentication, HasValidAPIKey
from .views_base import _parse_date, preprocess_image_if_needed

logger = logging.getLogger(__name__)


class InvoiceBatchViewSet(viewsets.ViewSet):
    """
    ViewSet for batch processing of multiple invoices using Gemini.
    
    🔐 Requiere API Key en producción.
    """
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasValidAPIKey]
    
    @action(detail=False, methods=['post'], url_path='process-batch')
    def upload_batch(self, request):
        """
        Endpoint para procesar múltiples facturas en paralelo (hasta 8 simultáneas)
        
        Request:
            POST /api/invoices/process-batch/
            Content-Type: multipart/form-data
            Body:
                - documents (files[]): Lista de documentos (hasta 8)
                - schema_type (string, optional): 'completo' or 'simplificado' (default: 'completo')
        
        Response:
            {
                "total": 3,
                "successful": 2,
                "failed": 1,
                "results": [...],
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
        
        # Get optional parameters
        schema_type = request.data.get('schema_type', 'completo')
        
        logger.info(f"📦 Batch processing {len(documents)} documents with Gemini...")
        
        def process_single_document(document):
            """Process a single document using Gemini"""
            try:
                # Create invoice record
                invoice = Invoice.objects.create(
                    document=document,
                    original_filename=document.name,
                    status='processing'
                )
                
                file_path = invoice.document.path
                
                # Preprocess image if needed
                file_path = preprocess_image_if_needed(file_path)
                
                # Extract with Gemini
                extractor = GeminiExtractor()
                result = extractor.extract_invoice_data(file_path)
                
                if not result.get('success', False):
                    raise Exception(result.get('error', 'Extraction failed'))
                
                extracted = result['data']
                metadata = result.get('metadata', {})
                
                # Post-process
                from invoice_extractor.utils.post_processor import InvoicePostProcessor
                processor = InvoicePostProcessor()
                post_result = processor.process(extracted)
                
                processed_data = post_result['processed_data']
                validation_result = post_result['validation_result']
                processing_metadata = post_result['processing_metadata']
                
                # Build response
                response_data = {
                    **processed_data,
                    'metadata': {
                        'validation': {
                            'validation_score': validation_result.get('validation_score', 0.0),
                            'confidence_level': validation_result.get('confidence_level', 'unknown'),
                            'has_validation_errors': validation_result.get('has_validation_errors', False),
                            'requires_review': validation_result.get('requires_review', False),
                            'errors_count': len(validation_result.get('validation_errors', [])),
                            'warnings_count': len(validation_result.get('validation_warnings', [])),
                        },
                        'extraction': {
                            'extraction_time': metadata.get('extraction_time', 0),
                            'extraction_method': 'gemini-2.5-flash',
                            'schema_type': schema_type
                        }
                    }
                }
                
                # Store data
                invoice.raw_extraction = {
                    'raw_data': extracted,
                    'processed_data': processed_data,
                    'validation_result': validation_result,
                    'extraction_metadata': metadata
                }
                invoice.extraction_time = metadata.get('extraction_time')
                invoice.schema_type = schema_type
                invoice.validation_score = validation_result.get('validation_score', 0.0)
                invoice.extraction_method = 'gemini'
                
                # Map documento fields
                if 'documento' in processed_data:
                    doc = processed_data['documento']
                    invoice.tipo_comprobante = doc.get('tipo_comprobante')
                    invoice.codigo_comprobante = doc.get('codigo')
                    invoice.numero_comprobante = doc.get('numero_comprobante')
                    invoice.punto_venta = doc.get('punto_venta')
                    invoice.cae = doc.get('cae')
                    invoice.moneda = doc.get('moneda') or 'ARS'
                    invoice.condicion_venta = doc.get('condicion_venta')
                    
                    if doc.get('fecha_emision'):
                        invoice.fecha_emision = _parse_date(doc['fecha_emision'])
                    if doc.get('fecha_vencimiento_cae'):
                        invoice.fecha_vencimiento_cae = _parse_date(doc['fecha_vencimiento_cae'])
                
                # Map partes fields
                if 'partes' in processed_data:
                    partes = processed_data['partes']
                    empresa = partes.get('empresa', {})
                    invoice.empresa_razon_social = empresa.get('razon_social')
                    invoice.empresa_cuit = empresa.get('cuit')
                    invoice.empresa_condicion_iva = empresa.get('condicion_iva')
                    
                    cliente = partes.get('cliente', {})
                    invoice.cliente_nombre = cliente.get('apellido_nombre_razon_social')
                    invoice.cliente_cuit = cliente.get('cuit')
                    invoice.cliente_condicion_iva = cliente.get('condicion_iva')
                
                # Map fiscalidad fields
                if 'fiscalidad' in processed_data:
                    fiscalidad = processed_data['fiscalidad']
                    totales = fiscalidad.get('totales', {})
                    invoice.subtotal_gravado = totales.get('subtotal_gravado')
                    invoice.importe_total = totales.get('importe_total')
                    invoice.descuentos = totales.get('descuentos', 0)
                    
                    impuestos = fiscalidad.get('impuestos', {})
                    iva_dict = impuestos.get('iva', {})
                    if isinstance(iva_dict, dict):
                        invoice.total_iva = sum(float(v or 0) for v in iva_dict.values())
                
                invoice.status = 'completed'
                invoice.processed_at = timezone.now()
                invoice.save()
                
                # Create line items
                if 'items' in processed_data:
                    for idx, item_data in enumerate(processed_data['items']):
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
                    'data': response_data
                }
                
            except Exception as e:
                logger.exception(f"Error processing document {document.name}")
                
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
        
        # Process documents in parallel
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
