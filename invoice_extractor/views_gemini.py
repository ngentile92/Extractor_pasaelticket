"""
🤖 ViewSet para procesamiento 100% Gemini

Este endpoint realiza extracción usando exclusivamente Gemini 2.5 Flash,
sin usar LlamaExtract. Usa el orchestrator inteligente por defecto.

Endpoint: POST /api/invoices-gemini/upload-gemini/

🔐 Autenticación:
    - Header: Authorization: Bearer <API_KEY>
    - O: X-API-Key: <API_KEY>
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.conf import settings
import logging
import json
import time

from .models import Invoice, InvoiceItem
from .serializers import InvoiceUploadSerializer
from .services_gemini_extractor import GeminiExtractor
from .authentication import APIKeyAuthentication, HasValidAPIKey
from .views_base import (
    preprocess_image_if_needed,
    build_extraction_response,
    _parse_date,
    _parse_float,
)

logger = logging.getLogger(__name__)


class InvoiceGeminiViewSet(viewsets.ViewSet):
    """
    ViewSet para procesamiento de facturas con Gemini 2.5 Flash exclusivamente.
    
    Usa el orchestrator inteligente para decidir la mejor estrategia de extracción.
    
    🔐 Requiere API Key en producción.
    """
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = [APIKeyAuthentication]
    permission_classes = [HasValidAPIKey]
    
    @action(detail=False, methods=['post'], url_path='upload-gemini')
    def upload_gemini(self, request):
        """
        Procesar factura con Gemini 2.5 Flash.
        
        Request:
            POST /api/invoices-gemini/upload-gemini/
            Content-Type: multipart/form-data
            Body:
                - document (file): Factura (PDF, JPG, PNG)
                - schema_type (string, optional): 'completo', 'simplificado', 'modular'
                - segments (array, optional): Segmentos a extraer (solo para 'modular')
                - enable_retry (bool, optional): Habilitar retry si score <= 0.7
        
        Response:
            {
                "id": 1,
                "status": "completed",
                "message": "Invoice processed successfully with Gemini",
                "data": {...}
            }
        """
        start_time = time.time()
        
        # 1. Validar request
        serializer = InvoiceUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        document = serializer.validated_data['document']
        
        # 2. Obtener parámetros
        schema_type = request.data.get('schema_type', 'completo')
        segments = self._parse_segments(request)
        enable_retry = request.data.get('enable_retry', 'true').lower() == 'true'
        
        # 3. Crear registro Invoice
        invoice = Invoice.objects.create(
            document=document,
            original_filename=document.name,
            status='processing'
        )
        
        try:
            file_path = invoice.document.path
            
            # 4. Preprocesar imagen
            file_path = preprocess_image_if_needed(file_path)
            
            logger.info("=" * 60)
            logger.info(f"🤖 GEMINI EXTRACTION - Invoice #{invoice.id}")
            logger.info(f"   Archivo: {document.name} | Schema: {schema_type}")
            logger.info("=" * 60)
            
            # 5. Extraer con orchestrator inteligente
            extracted, metadata = self._extract_with_orchestrator(
                file_path, schema_type, segments
            )
            
            # 6. Post-procesar
            processed_data, validation_result = self._post_process(extracted)
            validation_score = validation_result.get('validation_score', 0.0)
            
            logger.info(f"📊 Score inicial: {validation_score:.1%}")
            
            # 7. Retry si es necesario
            retry_metadata = {}
            if enable_retry and validation_score <= 0.7:
                processed_data, validation_result, retry_metadata = self._retry_extraction(
                    file_path, extracted, validation_result,
                    schema_type, segments, validation_score
                )
            
            # 8. Construir respuesta
            extraction_time = time.time() - start_time
            response_data = self._build_response(
                processed_data, validation_result, metadata,
                retry_metadata, extraction_time
            )
            
            # 9. Guardar en BD
            self._save_to_database(
                invoice, extracted, processed_data, validation_result,
                metadata, retry_metadata
            )
            
            logger.info(f"✅ Completado en {extraction_time:.1f}s | Score: {validation_result.get('validation_score', 0):.1%}")
            
            return Response({
                'id': invoice.id,
                'status': 'completed',
                'message': 'Invoice processed successfully with Gemini',
                'data': response_data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return self._handle_error(invoice, e)
    
    def _parse_segments(self, request) -> list:
        """Parsear segmentos del request."""
        segments = request.data.getlist('segments[]') or request.data.getlist('segments') or None
        
        if segments and isinstance(segments, list) and len(segments) == 1:
            try:
                segments = json.loads(segments[0])
            except (json.JSONDecodeError, ValueError):
                pass
        
        return segments
    
    def _extract_with_orchestrator(self, file_path: str, schema_type: str, segments: list) -> tuple:
        """Extraer usando el orchestrator inteligente."""
        from .orchestration.intelligent_orchestrator import IntelligentExtractionOrchestrator
        
        extractor = GeminiExtractor()
        orchestrator = IntelligentExtractionOrchestrator(
            gemini_extractor=extractor,
            enable_progressive=True,
            enable_selective_retry=True
        )
        
        result = orchestrator.extract_with_strategy(
            file_path=file_path,
            schema_type=schema_type,
            segments=segments
        )
        
        if not result.get('success', True):
            raise Exception(result.get('error', 'Extraction failed'))
        
        extracted = result.get('data', result)
        metadata = result.get('metadata', {})
        
        return extracted, metadata
    
    def _post_process(self, extracted: dict) -> tuple:
        """Aplicar post-procesamiento."""
        from .utils.post_processor import InvoicePostProcessor
        
        processor = InvoicePostProcessor(
            use_master_validator=True
        )
        
        result = processor.process(extracted)
        
        return result['processed_data'], result['validation_result']
    
    def _retry_extraction(
        self, file_path: str, original_data: dict,
        validation_result: dict, schema_type: str,
        segments: list, original_score: float
    ) -> tuple:
        """Ejecutar retry con contexto si es necesario."""
        logger.info(f"🔄 RETRY: Score bajo ({original_score:.1%})")
        
        extractor = GeminiExtractor()
        retry_data = extractor.retry_with_context(
            file_path=file_path,
            original_data=original_data,
            validation_result=validation_result,
            schema_type=schema_type,
            segments=segments
        )
        
        retry_metadata = {'was_retried': True, 'first_score': original_score}
        
        if retry_data:
            processed_retry, validation_retry = self._post_process(retry_data)
            retry_score = validation_retry.get('validation_score', 0.0)
            
            retry_metadata['second_score'] = retry_score
            retry_metadata['improvement'] = (retry_score - original_score) * 100
            
            if retry_score > original_score:
                logger.info(f"✅ Retry mejoró: {original_score:.1%} → {retry_score:.1%}")
                return processed_retry, validation_retry, retry_metadata
            else:
                logger.info(f"ℹ️ Retry no mejoró ({retry_score:.1%})")
        
        # Devolver datos originales si retry no mejoró
        from .utils.post_processor import InvoicePostProcessor
        processor = InvoicePostProcessor(use_master_validator=True)
        result = processor.process(original_data)
        return result['processed_data'], result['validation_result'], retry_metadata
    
    def _build_response(
        self, processed_data: dict, validation_result: dict,
        extraction_metadata: dict, retry_metadata: dict,
        extraction_time: float
    ) -> dict:
        """Construir respuesta en formato legacy."""
        response = {
            **processed_data,
            'metadata': {
                'validation': {
                    'validation_score': validation_result.get('validation_score', 0.0),
                    'confidence_level': validation_result.get('confidence_level', 'unknown'),
                    'has_validation_errors': validation_result.get('has_validation_errors', False),
                    'requires_review': validation_result.get('requires_review', False),
                    'errors_count': len(validation_result.get('errors', [])),
                    'warnings_count': len(validation_result.get('warnings', [])),
                },
                'extraction': {
                    'extraction_time': extraction_time,
                    'extraction_method': 'gemini-2.5-flash',
                    'schema_type': extraction_metadata.get('schema_type', 'completo'),
                }
            }
        }
        
        if retry_metadata.get('was_retried'):
            response['metadata']['gemini_retry'] = retry_metadata
        
        if 'orchestration' in extraction_metadata:
            response['metadata']['orchestration'] = extraction_metadata['orchestration']
        
        return response
    
    def _save_to_database(
        self, invoice, extracted: dict, processed_data: dict,
        validation_result: dict, metadata: dict, retry_metadata: dict
    ):
        """Guardar datos en la base de datos."""
        from invoice_extractor.utils.response_formatter import build_clean_raw_extraction
        
        # Raw data - ESTRUCTURA LIMPIA
        processing_metadata = {'gemini_retry': retry_metadata}
        invoice.raw_extraction = build_clean_raw_extraction(
            raw_data=extracted,
            processed_data=processed_data,
            validation_result=validation_result,
            processing_metadata=processing_metadata,
            extraction_metadata=metadata
        )
        invoice.extraction_time = metadata.get('extraction_time')
        invoice.schema_type = metadata.get('schema_type', 'completo')
        invoice.validation_score = validation_result.get('validation_score', 0.0)
        invoice.extraction_method = 'gemini'
        invoice.gemini_retry_used = retry_metadata.get('was_retried', False)
        invoice.gemini_improvement = retry_metadata.get('improvement', 0)
        
        # Documento
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
        
        # Partes
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
        
        # Fiscalidad
        if 'fiscalidad' in processed_data:
            fiscalidad = processed_data['fiscalidad']
            totales = fiscalidad.get('totales', {})
            invoice.subtotal_gravado = totales.get('subtotal_gravado')
            invoice.importe_total = totales.get('importe_total')
            invoice.descuentos = totales.get('descuentos', 0)
            
            impuestos = fiscalidad.get('impuestos', {})
            iva_dict = impuestos.get('iva', {})
            invoice.total_iva = sum(float(v or 0) for v in iva_dict.values())
        
        invoice.status = 'completed'
        invoice.processed_at = timezone.now()
        invoice.save()
        
        # Items
        if 'items' in processed_data:
            for idx, item in enumerate(processed_data.get('items', [])):
                if isinstance(item, dict):
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        codigo=item.get('codigo'),
                        descripcion=item.get('descripcion', ''),
                        cantidad=item.get('cantidad', 0),
                        unidad_medida=item.get('unidad_medida'),
                        precio_unitario=item.get('precio_unitario', 0),
                        subtotal=item.get('subtotal', 0),
                        order=idx
                    )
    
    def _handle_error(self, invoice, error: Exception) -> Response:
        """Manejar errores de extracción."""
        invoice.status = 'failed'
        invoice.error_message = str(error)
        invoice.save()
        
        logger.exception(f"❌ Error procesando invoice {invoice.id}")
        
        response = {
            'id': invoice.id,
            'status': 'failed',
            'message': 'Error during Gemini extraction'
        }
        
        if settings.DEBUG:
            response['error'] = str(error)
        
        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
