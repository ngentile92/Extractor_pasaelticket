from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
from .models import Invoice, InvoiceItem
from .views_base import _parse_date, _parse_float


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
        # Usar endpoint de Gemini
        response = self.client.get('/api/invoices-gemini/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_upload_invoice_without_file(self):
        """Test uploading invoice without file"""
        response = self.client.post('/api/invoices-gemini/upload-gemini/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_retrieve_invoice(self):
        """Test retrieving a specific invoice"""
        invoice = Invoice.objects.create(
            original_filename='test_invoice.pdf',
            status='completed',
            invoice_number='0001-00001234'
        )
        
        response = self.client.get(f'/api/invoices-gemini/{invoice.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ParsingUtilsTest(TestCase):
    """Test cases for parsing utilities"""
    
    def test_parse_date(self):
        """Test date parsing"""
        self.assertEqual(_parse_date('15/01/2024'), '2024-01-15')
        self.assertEqual(_parse_date('15-01-2024'), '2024-01-15')
        self.assertEqual(_parse_date('2024-01-15'), '2024-01-15')
        self.assertIsNone(_parse_date('invalid'))
        self.assertIsNone(_parse_date(None))
    
    def test_parse_float(self):
        """Test float parsing"""
        self.assertEqual(_parse_float(100), 100.0)
        self.assertEqual(_parse_float('100.50'), 100.50)
        self.assertEqual(_parse_float(None), 0.0)
        self.assertEqual(_parse_float('invalid'), 0.0)
