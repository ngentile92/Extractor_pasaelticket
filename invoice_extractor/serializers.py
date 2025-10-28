from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    """Serializer for invoice line items"""
    
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'codigo', 'descripcion', 'cantidad', 'precio_unitario', 
            'subtotal', 'unidad_medida', 'order'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for invoice model"""
    
    items = InvoiceItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'document', 'original_filename', 'status',
            'uploaded_at', 'processed_at', 'extraction_time', 'schema_type',
            'tipo_comprobante', 'codigo_comprobante', 'numero_comprobante', 
            'punto_venta', 'fecha_emision', 'cae', 'fecha_vencimiento_cae',
            'moneda', 'condicion_venta',
            'empresa_razon_social', 'empresa_cuit', 'empresa_condicion_iva',
            'empresa_domicilio', 'empresa_ingresos_brutos', 'empresa_provincia',
            'cliente_nombre', 'cliente_cuit', 'cliente_condicion_iva',
            'cliente_domicilio', 'cliente_provincia',
            'subtotal_gravado', 'total_iva', 'total_percepciones', 
            'total_retenciones', 'importe_total', 'descuentos',
            'items_count', 'diferencia_matematica', 'validation_score',
            'raw_extraction', 'error_message', 'items'
        ]
        read_only_fields = ['id', 'uploaded_at', 'processed_at', 'status']


class InvoiceUploadSerializer(serializers.Serializer):
    """Serializer for uploading invoice documents"""
    
    document = serializers.FileField(
        help_text='Invoice document (PDF, JPG, PNG, or DOCX)'
    )
    
    def validate_document(self, value):
        """Validate file extension and size"""
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'docx']
        ext = value.name.split('.')[-1].lower()
        
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Limit file size to 10MB
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must not exceed 10MB")
        
        return value
