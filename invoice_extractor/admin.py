from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    """Inline admin for invoice items"""
    model = InvoiceItem
    extra = 0
    fields = ['codigo', 'descripcion', 'cantidad', 'unidad_medida', 'precio_unitario', 'subtotal', 'order']
    readonly_fields = ['order']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for Invoice model (Comprobantes)"""
    list_display = [
        'id', 'numero_comprobante', 'tipo_comprobante', 'empresa_razon_social', 
        'importe_total', 'status', 'uploaded_at', 'processed_at'
    ]
    list_filter = ['status', 'uploaded_at', 'tipo_comprobante', 'schema_type']
    search_fields = [
        'numero_comprobante', 'empresa_razon_social', 'empresa_cuit',
        'cliente_nombre', 'cliente_cuit', 'cae'
    ]
    readonly_fields = [
        'uploaded_at', 'processed_at', 'extraction_time', 
        'raw_extraction', 'has_complete_extraction'
    ]
    
    fieldsets = (
        ('Document Information', {
            'fields': (
                'document', 'original_filename', 'status', 
                'uploaded_at', 'processed_at', 'extraction_time', 'schema_type'
            )
        }),
        ('Comprobante Details', {
            'fields': (
                'tipo_comprobante', 'codigo_comprobante', 'numero_comprobante', 
                'punto_venta', 'fecha_emision', 'cae', 'fecha_vencimiento_cae',
                'moneda', 'condicion_venta'
            )
        }),
        ('Empresa/Vendor Information', {
            'fields': (
                'empresa_razon_social', 'empresa_cuit', 'empresa_condicion_iva',
                'empresa_domicilio', 'empresa_provincia', 'empresa_ingresos_brutos'
            )
        }),
        ('Cliente/Customer Information', {
            'fields': (
                'cliente_nombre', 'cliente_cuit', 'cliente_condicion_iva',
                'cliente_domicilio', 'cliente_provincia'
            )
        }),
        ('Financial Information', {
            'fields': (
                'subtotal_gravado', 'total_iva', 'total_percepciones', 
                'total_retenciones', 'descuentos', 'importe_total'
            )
        }),
        ('Calculations & Validation', {
            'fields': ('items_count', 'diferencia_matematica', 'validation_score'),
            'classes': ('collapse',)
        }),
        ('Raw Data', {
            'fields': ('error_message', 'raw_extraction', 'has_complete_extraction'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    """Admin interface for InvoiceItem model"""
    list_display = [
        'id', 'invoice', 'codigo', 'descripcion', 'cantidad', 
        'unidad_medida', 'precio_unitario', 'subtotal', 'order'
    ]
    list_filter = ['invoice__status', 'unidad_medida']
    search_fields = ['descripcion', 'codigo', 'invoice__numero_comprobante']
    ordering = ['invoice', 'order']
