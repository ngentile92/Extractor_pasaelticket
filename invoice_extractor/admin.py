from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    """Inline admin for invoice items"""
    model = InvoiceItem
    extra = 0
    fields = ['description', 'quantity', 'unit_price', 'total_price', 'tax_rate']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for Invoice model"""
    list_display = [
        'id', 'invoice_number', 'vendor_name', 'total_amount', 
        'status', 'uploaded_at', 'processed_at'
    ]
    list_filter = ['status', 'uploaded_at', 'currency']
    search_fields = [
        'invoice_number', 'vendor_name', 'vendor_cuit',
        'customer_name', 'customer_cuit'
    ]
    readonly_fields = ['uploaded_at', 'processed_at', 'raw_extraction']
    
    fieldsets = (
        ('Document Information', {
            'fields': ('document', 'original_filename', 'status', 'uploaded_at', 'processed_at')
        }),
        ('Invoice Details', {
            'fields': ('invoice_number', 'invoice_date', 'currency')
        }),
        ('Vendor Information', {
            'fields': ('vendor_name', 'vendor_cuit', 'vendor_address')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_cuit', 'customer_address')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax_amount', 'total_amount', 'payment_terms')
        }),
        ('Additional Information', {
            'fields': ('notes', 'error_message', 'raw_extraction'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    """Admin interface for InvoiceItem model"""
    list_display = [
        'id', 'invoice', 'description', 'quantity', 
        'unit_price', 'total_price', 'tax_rate'
    ]
    list_filter = ['invoice__status']
    search_fields = ['description', 'product_code', 'invoice__invoice_number']
