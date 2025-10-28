from django.db import models
from django.core.validators import FileExtensionValidator


class Invoice(models.Model):
    """
    Model to store Argentine invoice/voucher documents and extracted data.
    
    This model stores the complete extraction from LlamaExtract including:
    - Document information (type, number, dates, CAE)
    - Party information (customer and vendor details)
    - Line items (products/services)
    - Complete fiscal breakdown (taxes, perceptions, withholdings)
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    # ========================================================================
    # File Information
    # ========================================================================
    document = models.FileField(
        upload_to='invoices/%Y/%m/%d/',
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'docx']
        )],
        help_text='Invoice document (PDF, JPG, PNG, or DOCX)'
    )
    original_filename = models.CharField(max_length=255)
    
    # ========================================================================
    # Processing Status
    # ========================================================================
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    extraction_time = models.FloatField(
        null=True, 
        blank=True,
        help_text='Time taken for extraction in seconds'
    )
    schema_type = models.CharField(
        max_length=50,
        default='completo',
        help_text='Schema type used: completo or simplificado'
    )
    
    # ========================================================================
    # Document Information (Documento)
    # ========================================================================
    tipo_comprobante = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text='Document type (e.g., FACTURAS A, TIQUE FACTURA A)'
    )
    codigo_comprobante = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        help_text='AFIP document code (e.g., 001, 006, 081)'
    )
    numero_comprobante = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text='Invoice number (e.g., 0029-00271813)'
    )
    punto_venta = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text='Point of sale number'
    )
    fecha_emision = models.DateField(
        null=True, 
        blank=True,
        help_text='Issue date'
    )
    cae = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='CAE - Electronic Authorization Code'
    )
    fecha_vencimiento_cae = models.DateField(
        null=True,
        blank=True,
        help_text='CAE expiration date'
    )
    moneda = models.CharField(
        max_length=10, 
        default='ARS',
        help_text='Currency code'
    )
    condicion_venta = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Payment terms'
    )
    
    # ========================================================================
    # Vendor/Empresa Information
    # ========================================================================
    empresa_razon_social = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text='Vendor business name'
    )
    empresa_cuit = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        help_text='Vendor CUIT (Tax ID)'
    )
    empresa_condicion_iva = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Vendor VAT status'
    )
    empresa_domicilio = models.TextField(
        blank=True, 
        null=True,
        help_text='Vendor address'
    )
    empresa_ingresos_brutos = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Vendor gross income tax number'
    )
    empresa_provincia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Vendor province'
    )
    
    # ========================================================================
    # Customer/Cliente Information
    # ========================================================================
    cliente_nombre = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text='Customer name or business name'
    )
    cliente_cuit = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text='Customer CUIT (Tax ID)'
    )
    cliente_condicion_iva = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Customer VAT status'
    )
    cliente_domicilio = models.TextField(
        blank=True, 
        null=True,
        help_text='Customer address'
    )
    cliente_provincia = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Customer province'
    )
    
    # ========================================================================
    # Financial Totals
    # ========================================================================
    subtotal_gravado = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text='Taxable subtotal before taxes'
    )
    total_iva = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text='Total VAT/IVA amount'
    )
    total_percepciones = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Total perceptions'
    )
    total_retenciones = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Total withholdings'
    )
    importe_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text='Total invoice amount'
    )
    descuentos = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        help_text='Total discounts'
    )
    
    # ========================================================================
    # Calculations and Validation
    # ========================================================================
    items_count = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of line items'
    )
    diferencia_matematica = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        help_text='Arithmetic difference in calculations'
    )
    validation_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Validation score from post-processing (0.0000 - 1.0000)'
    )
    
    # ========================================================================
    # Complete Extraction Data (JSON)
    # ========================================================================
    raw_extraction = models.JSONField(
        null=True, 
        blank=True, 
        help_text='Complete extraction data from LlamaExtract in JSON format'
    )
    
    # This field stores the complete structured data including:
    # - items: list of line items
    # - partes: customer and vendor complete info
    # - documento: all document details
    # - fiscalidad: complete tax breakdown (totales, calculos, impuestos)
    
    # ========================================================================
    # Error Handling
    # ========================================================================
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Comprobante'
        verbose_name_plural = 'Comprobantes'
        indexes = [
            models.Index(fields=['-uploaded_at']),
            models.Index(fields=['status']),
            models.Index(fields=['empresa_cuit']),
            models.Index(fields=['cliente_cuit']),
            models.Index(fields=['numero_comprobante']),
        ]
    
    def __str__(self):
        return f"{self.tipo_comprobante or 'Comprobante'} {self.numero_comprobante or self.id} - {self.status}"
    
    @property
    def has_complete_extraction(self) -> bool:
        """Check if complete extraction data is available."""
        return bool(self.raw_extraction and 'items' in self.raw_extraction)


class InvoiceItem(models.Model):
    """
    Model to store individual line items from an invoice.
    
    Represents products/services with quantity, pricing, and unit information
    as extracted from Argentine invoices.
    """
    
    invoice = models.ForeignKey(
        Invoice, 
        on_delete=models.CASCADE, 
        related_name='items'
    )
    
    # Item identification
    codigo = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text='Product code or SKU (e.g., YPF-78005)'
    )
    
    # Item description
    descripcion = models.TextField(
        help_text='Product or service description'
    )
    
    # Quantity and unit
    cantidad = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        help_text='Quantity (can be fractional, e.g., 43.0202)'
    )
    unidad_medida = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text='Unit of measure (CJ=box, UN=unit, KG, LT, etc.)'
    )
    
    # Pricing
    precio_unitario = models.DecimalField(
        max_digits=15, 
        decimal_places=4,
        help_text='Unit price per item before taxes'
    )
    subtotal = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text='Line item subtotal (cantidad × precio_unitario)'
    )
    
    # Order within invoice
    order = models.IntegerField(
        default=0,
        help_text='Order/position of item in the invoice'
    )
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Item de Comprobante'
        verbose_name_plural = 'Items de Comprobantes'
    
    def __str__(self):
        return f"{self.descripcion[:50]} - {self.cantidad} x ${self.precio_unitario}"
    
    @property
    def total_calculado(self) -> float:
        """Calculate total: quantity × unit_price."""
        return float(self.cantidad) * float(self.precio_unitario)
