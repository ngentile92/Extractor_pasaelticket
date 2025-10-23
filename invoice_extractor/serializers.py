from rest_framework import serializers
from .models import Invoice, InvoiceItem


class InvoiceItemSerializer(serializers.ModelSerializer):
    """Serializer for invoice line items"""
    
    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'description', 'quantity', 'unit_price', 
            'total_price', 'tax_rate', 'product_code', 'unit_of_measure'
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for invoice model"""
    
    items = InvoiceItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'document', 'original_filename', 'status',
            'uploaded_at', 'processed_at', 
            'invoice_number', 'invoice_date',
            'vendor_name', 'vendor_cuit', 'vendor_address',
            'customer_name', 'customer_cuit', 'customer_address',
            'subtotal', 'tax_amount', 'total_amount', 'currency',
            'payment_terms', 'notes', 'raw_extraction',
            'error_message', 'items'
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
