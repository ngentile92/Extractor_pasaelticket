from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.core.files.storage import default_storage

from .models import Invoice, InvoiceItem
from .serializers import (
    InvoiceSerializer, 
    InvoiceUploadSerializer,
    InvoiceItemSerializer
)
from .services import InvoiceExtractionService


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
        
        Request:
            POST /api/invoices/process/
            Content-Type: multipart/form-data
            Body: document (file)
        
        Response:
            {
                "id": 1,
                "status": "processing",
                "message": "Invoice uploaded successfully. Processing..."
            }
        """
        serializer = InvoiceUploadSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )
        
        document = serializer.validated_data['document']
        
        # Create invoice record
        invoice = Invoice.objects.create(
            document=document,
            original_filename=document.name,
            status='processing'
        )
        
        try:
            # Process the document using Llamaindex
            extraction_service = InvoiceExtractionService()
            file_path = invoice.document.path
            
            result = extraction_service.extract_invoice_data(file_path)
            
            if result['success']:
                # Update invoice with extracted data
                extracted = result['data']
                
                invoice.invoice_number = extracted.get('invoice_number')
                invoice.vendor_name = extracted.get('vendor_name')
                invoice.vendor_cuit = extracted.get('vendor_cuit')
                invoice.vendor_address = extracted.get('vendor_address')
                invoice.customer_name = extracted.get('customer_name')
                invoice.customer_cuit = extracted.get('customer_cuit')
                invoice.customer_address = extracted.get('customer_address')
                invoice.payment_terms = extracted.get('payment_terms')
                invoice.currency = extracted.get('currency', 'ARS')
                invoice.raw_extraction = extracted
                
                # Parse and set financial data
                if extracted.get('subtotal'):
                    invoice.subtotal = extraction_service.parse_currency(
                        extracted['subtotal']
                    )
                if extracted.get('tax_amount'):
                    invoice.tax_amount = extraction_service.parse_currency(
                        extracted['tax_amount']
                    )
                if extracted.get('total_amount'):
                    invoice.total_amount = extraction_service.parse_currency(
                        extracted['total_amount']
                    )
                
                # Parse and set date
                if extracted.get('invoice_date'):
                    parsed_date = extraction_service.parse_date(
                        extracted['invoice_date']
                    )
                    if parsed_date:
                        invoice.invoice_date = parsed_date
                
                invoice.status = 'completed'
                invoice.processed_at = timezone.now()
                invoice.save()
                
                # Create line items if extracted
                items_data = extracted.get('items', [])
                for item_data in items_data:
                    if isinstance(item_data, dict):
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            description=item_data.get('description', ''),
                            quantity=item_data.get('quantity', 0),
                            unit_price=item_data.get('unit_price', 0),
                            total_price=item_data.get('total_price', 0),
                        )
                
                return Response(
                    {
                        'id': invoice.id,
                        'status': 'completed',
                        'message': 'Invoice processed successfully',
                        'data': InvoiceSerializer(invoice).data
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                # Processing failed
                invoice.status = 'failed'
                invoice.error_message = result.get('error', 'Unknown error')
                invoice.save()
                
                return Response(
                    {
                        'id': invoice.id,
                        'status': 'failed',
                        'message': 'Failed to process invoice',
                        'error': result.get('error')
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            # Handle unexpected errors
            invoice.status = 'failed'
            invoice.error_message = str(e)
            invoice.save()
            
            return Response(
                {
                    'id': invoice.id,
                    'status': 'failed',
                    'message': 'An error occurred during processing',
                    'error': str(e)
                },
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
                invoice.status = 'failed'
                invoice.error_message = result.get('error')
                invoice.save()
                
                return Response(
                    {
                        'error': 'Failed to reprocess invoice',
                        'details': result.get('error')
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            invoice.status = 'failed'
            invoice.error_message = str(e)
            invoice.save()
            
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
