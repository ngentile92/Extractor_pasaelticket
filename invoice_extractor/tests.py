from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Invoice, InvoiceItem
from .services import InvoiceExtractionService


class InvoiceModelTest(TestCase):
    """Test cases for Invoice model"""
    
    def test_create_invoice(self):
        """Test creating an invoice"""
        invoice = Invoice.objects.create(
            original_filename='test_invoice.pdf',
            status='pending',
            invoice_number='0001-00001234',
            vendor_name='Test Vendor S.A.',
            vendor_cuit='30-12345678-9',
            total_amount=Decimal('12100.00'),
            currency='ARS'
        )
        self.assertEqual(invoice.status, 'pending')
        self.assertEqual(invoice.invoice_number, '0001-00001234')
        self.assertEqual(str(invoice), 'Invoice 0001-00001234 - pending')
    
    def test_create_invoice_item(self):
        """Test creating an invoice item"""
        invoice = Invoice.objects.create(
            original_filename='test_invoice.pdf',
            status='pending'
        )
        
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description='Test Product',
            quantity=Decimal('10.00'),
            unit_price=Decimal('100.00'),
            total_price=Decimal('1000.00')
        )
        
        self.assertEqual(item.invoice, invoice)
        self.assertEqual(item.quantity, Decimal('10.00'))
        self.assertEqual(invoice.items.count(), 1)


class InvoiceAPITest(APITestCase):
    """Test cases for Invoice API endpoints"""
    
    def test_list_invoices(self):
        """Test listing invoices"""
        response = self.client.get('/api/invoices/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_upload_invoice_without_file(self):
        """Test uploading invoice without file"""
        response = self.client.post('/api/invoices/process/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_upload_invoice_with_invalid_extension(self):
        """Test uploading invoice with invalid file extension"""
        file_content = b'test content'
        test_file = SimpleUploadedFile(
            'test.txt', 
            file_content, 
            content_type='text/plain'
        )
        
        response = self.client.post(
            '/api/invoices/process/', 
            {'document': test_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_retrieve_invoice(self):
        """Test retrieving a specific invoice"""
        invoice = Invoice.objects.create(
            original_filename='test_invoice.pdf',
            status='completed',
            invoice_number='0001-00001234'
        )
        
        response = self.client.get(f'/api/invoices/{invoice.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['invoice_number'], '0001-00001234')


class InvoiceExtractionServiceTest(TestCase):
    """Test cases for InvoiceExtractionService"""
    
    def test_parse_currency(self):
        """Test currency parsing for Argentine format"""
        service = InvoiceExtractionService()
        
        # Argentine format: uses . for thousands and , for decimals
        # Service converts . to nothing and , to .
        self.assertEqual(service.parse_currency('$1.234,56'), 1234.56)
        self.assertEqual(service.parse_currency('1234,56'), 1234.56)
        # With just period (thousands separator), it's removed
        self.assertEqual(service.parse_currency('12.345'), 12345.0)
        self.assertIsNone(service.parse_currency('invalid'))
        self.assertIsNone(service.parse_currency(None))
    
    def test_parse_date(self):
        """Test date parsing"""
        service = InvoiceExtractionService()
        
        self.assertEqual(service.parse_date('15/01/2024'), '2024-01-15')
        self.assertEqual(service.parse_date('15-01-2024'), '2024-01-15')
        self.assertEqual(service.parse_date('2024-01-15'), '2024-01-15')
        self.assertIsNone(service.parse_date('invalid'))
        self.assertIsNone(service.parse_date(None))
