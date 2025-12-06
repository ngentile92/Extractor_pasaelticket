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
    """Serializer for invoice model - Estructura limpia y ordenada"""
    
    items = InvoiceItemSerializer(many=True, read_only=True)
    
    # Campos computados para la estructura limpia
    factura = serializers.SerializerMethodField()
    validacion = serializers.SerializerMethodField()
    alertas = serializers.SerializerMethodField()
    metadata_extraccion = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            # Identificadores básicos
            'id', 'status', 'original_filename', 'document',
            'uploaded_at', 'processed_at',
            
            # ESTRUCTURA LIMPIA - Datos de la factura
            'factura',
            
            # ESTRUCTURA LIMPIA - Validación
            'validacion',
            
            # ESTRUCTURA LIMPIA - Alertas
            'alertas',
            
            # ESTRUCTURA LIMPIA - Metadata
            'metadata_extraccion',
            
            # Items como lista separada
            'items',
            
            # Error si falló
            'error_message',
        ]
        read_only_fields = ['id', 'uploaded_at', 'processed_at', 'status']
    
    def get_factura(self, obj):
        """Retorna datos de la factura desde raw_extraction limpio."""
        if obj.raw_extraction and 'factura' in obj.raw_extraction:
            return obj.raw_extraction['factura']
        # Fallback para datos legacy
        return self._build_legacy_factura(obj)
    
    def get_validacion(self, obj):
        """Retorna datos de validación."""
        if obj.raw_extraction and 'validacion' in obj.raw_extraction:
            return obj.raw_extraction['validacion']
        # Fallback
        return {
            'score': float(obj.validation_score or 0) * 100,
            'score_decimal': float(obj.validation_score or 0),
            'nivel_confianza': 'desconocido',
            'indicador': '⚪',
            'requiere_revision': True,
            'tiene_errores': False
        }
    
    def get_alertas(self, obj):
        """Retorna alertas (errores, warnings, correcciones)."""
        if obj.raw_extraction and 'alertas' in obj.raw_extraction:
            return obj.raw_extraction['alertas']
        # Fallback
        return {
            'errores': [],
            'errores_count': 0,
            'warnings': [],
            'warnings_count': 0,
            'alertas_criticas': [],
            'alertas_info': [],
            'correcciones_aplicadas': [],
            'recomendaciones': []
        }
    
    def get_metadata_extraccion(self, obj):
        """Retorna metadata técnica."""
        if obj.raw_extraction and 'metadata' in obj.raw_extraction:
            return obj.raw_extraction['metadata']
        # Fallback
        return {
            'tiempo_extraccion_seg': float(obj.extraction_time or 0),
            'metodo_extraccion': obj.extraction_method or 'desconocido',
            'schema_utilizado': obj.schema_type or 'completo'
        }
    
    def _build_legacy_factura(self, obj):
        """Construye estructura de factura desde campos del modelo (fallback)."""
        return {
            'documento': {
                'tipo': obj.tipo_comprobante,
                'codigo': obj.codigo_comprobante,
                'numero': f"{obj.punto_venta or ''}-{obj.numero_comprobante or ''}".strip('-'),
                'punto_venta': obj.punto_venta,
                'numero_comprobante': obj.numero_comprobante,
                'fecha_emision': str(obj.fecha_emision) if obj.fecha_emision else None,
                'cae': obj.cae,
                'fecha_vencimiento_cae': str(obj.fecha_vencimiento_cae) if obj.fecha_vencimiento_cae else None,
                'moneda': obj.moneda,
                'condicion_venta': obj.condicion_venta
            },
            'emisor': {
                'razon_social': obj.empresa_razon_social,
                'cuit': obj.empresa_cuit,
                'condicion_iva': obj.empresa_condicion_iva,
                'domicilio': obj.empresa_domicilio,
                'provincia': obj.empresa_provincia,
                'ingresos_brutos': obj.empresa_ingresos_brutos
            },
            'receptor': {
                'razon_social': obj.cliente_nombre,
                'cuit': obj.cliente_cuit,
                'condicion_iva': obj.cliente_condicion_iva,
                'domicilio': obj.cliente_domicilio,
                'provincia': obj.cliente_provincia
            },
            'items': [],  # Se llenará desde la relación
            'cantidad_items': obj.items_count or obj.items.count(),
            'totales': {
                'subtotal_gravado': float(obj.subtotal_gravado or 0),
                'descuentos': float(obj.descuentos or 0),
                'iva': {'total_iva': float(obj.total_iva or 0)},
                'percepciones': {'total_percepciones': float(obj.total_percepciones or 0)},
                'retenciones': {'total_retenciones': float(obj.total_retenciones or 0)},
                'otros_impuestos': {},
                'importe_total': float(obj.importe_total or 0)
            }
        }


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
