from django.db import models
from django.core.validators import FileExtensionValidator


class Invoice(models.Model):
    """Model to store invoice documents and extracted data"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # File information
    document = models.FileField(
        upload_to='invoices/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'docx'])],
        help_text='Invoice document (PDF, JPG, PNG, or DOCX)'
    )
    original_filename = models.CharField(max_length=255)
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Extracted data (Argentine invoice fields)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)
    invoice_date = models.DateField(null=True, blank=True)
    
    # Vendor information
    vendor_name = models.CharField(max_length=255, blank=True, null=True)
    vendor_cuit = models.CharField(max_length=20, blank=True, null=True, help_text='CUIT (Tax ID)')
    vendor_address = models.TextField(blank=True, null=True)
    
    # Customer information
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_cuit = models.CharField(max_length=20, blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    
    # Financial data
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text='IVA (VAT)')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, default='ARS', help_text='Currency (default ARS)')
    
    # Additional fields
    payment_terms = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Raw extracted data (JSON format)
    raw_extraction = models.JSONField(null=True, blank=True, help_text='Raw extraction data from Llamaindex')
    
    # Error handling
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
    
    def __str__(self):
        return f"Invoice {self.invoice_number or self.id} - {self.status}"


class InvoiceItem(models.Model):
    """Model to store individual line items from an invoice"""
    
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    
    # Item details
    description = models.TextField()
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Tax information
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Tax rate (e.g., 21 for 21%)')
    
    # Additional info
    product_code = models.CharField(max_length=100, blank=True, null=True)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        ordering = ['id']
        verbose_name = 'Invoice Item'
        verbose_name_plural = 'Invoice Items'
    
    def __str__(self):
        return f"{self.description[:50]} - {self.quantity} x {self.unit_price}"
