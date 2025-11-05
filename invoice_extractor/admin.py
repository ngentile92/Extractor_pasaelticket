from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg, Sum, Q
from django.urls import reverse
from .models import Invoice, InvoiceItem
import json


class InvoiceItemInline(admin.TabularInline):
    """Inline admin for invoice items"""
    model = InvoiceItem
    extra = 0
    fields = ['codigo', 'descripcion', 'cantidad', 'unidad_medida', 'precio_unitario', 'subtotal', 'order']
    readonly_fields = ['order']
    
    def has_add_permission(self, request, obj=None):
        # Items son extraídos automáticamente, no se agregan manualmente
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for Invoice model (Comprobantes)"""
    list_display = [
        'id', 'colored_status', 'numero_comprobante', 'tipo_comprobante', 
        'empresa_razon_social', 'formatted_total', 'score_badge',
        'extraction_method_badge', 'uploaded_at'
    ]
    list_filter = ['status', 'uploaded_at', 'tipo_comprobante', 'schema_type']
    search_fields = [
        'numero_comprobante', 'empresa_razon_social', 'empresa_cuit',
        'cliente_nombre', 'cliente_cuit', 'cae'
    ]
    readonly_fields = [
        'uploaded_at', 'processed_at', 'extraction_time', 
        'has_complete_extraction', 'formatted_documento', 'formatted_partes',
        'formatted_items_table', 'formatted_fiscalidad', 'formatted_metadata',
        'formatted_validation_errors', 'formatted_raw_json'
    ]
    
    fieldsets = (
        ('📄 Estado del Documento', {
            'fields': (
                'document', 'original_filename', 'status', 
                'uploaded_at', 'processed_at', 'extraction_time', 'schema_type'
            )
        }),
        ('📋 Datos del Documento', {
            'fields': ('formatted_documento',),
            'description': 'Información extraída del documento'
        }),
        ('👥 Partes (Empresa y Cliente)', {
            'fields': ('formatted_partes',),
            'description': 'Información del emisor y receptor'
        }),
        ('📦 Items del Comprobante', {
            'fields': ('formatted_items_table',),
            'description': 'Productos/servicios detallados'
        }),
        ('💰 Información Fiscal', {
            'fields': ('formatted_fiscalidad',),
            'description': 'Totales, impuestos, percepciones y retenciones'
        }),
        ('📊 Metadata de Procesamiento', {
            'fields': ('formatted_metadata',),
            'description': 'Información sobre el proceso de extracción'
        }),
        ('⚠️ Validaciones y Errores', {
            'fields': ('formatted_validation_errors',),
            'description': 'Errores y advertencias detectadas',
            'classes': ('collapse',)
        }),
        ('🔍 Raw JSON', {
            'fields': ('formatted_raw_json',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [InvoiceItemInline]
    
    def colored_status(self, obj):
        """Display status with color coding"""
        colors = {
            'completed': '#28a745',
            'processing': '#ffc107',
            'failed': '#dc3545',
            'pending': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    colored_status.short_description = 'Estado'
    
    def formatted_total(self, obj):
        """Format total with currency"""
        if obj.importe_total is not None:
            # Format the number first, then pass to format_html
            formatted_value = f'${float(obj.importe_total):,.2f}'
            return format_html(
                '<strong style="font-size: 14px; color: #28a745;">{}</strong>',
                formatted_value
            )
        return '-'
    formatted_total.short_description = 'Total'
    
    def score_badge(self, obj):
        """Display validation score as a badge"""
        if obj.validation_score is None:
            return '-'
        
        score_percent = float(obj.validation_score) * 100
        
        if score_percent >= 80:
            color = '#28a745'
            icon = '✅'
        elif score_percent >= 60:
            color = '#ffc107'
            icon = '⚠️'
        else:
            color = '#dc3545'
            icon = '❌'
        
        # Format the percentage first
        score_text = f'{icon} {score_percent:.0f}%'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, score_text
        )
    score_badge.short_description = 'Score'
    
    def extraction_method_badge(self, obj):
        """Show which extraction method was used"""
        if not obj.raw_extraction:
            return '-'
        
        metadata = obj.raw_extraction.get('processing_metadata', {})
        gemini_info = metadata.get('gemini_retry', {})
        
        if gemini_info.get('used'):
            improvement = float(gemini_info.get('improvement', 0))
            title_text = f'Mejorado con Gemini (+{improvement:.0f}pp)'
            return format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;" title="{}">🤖 Gemini</span>',
                title_text
            )
        else:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">🦙 Llama</span>'
            )
    extraction_method_badge.short_description = 'Método'
    
    def formatted_documento(self, obj):
        """Display documento section in a formatted table"""
        if not obj.raw_extraction or 'documento' not in obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay datos de documento disponibles</p>')
        
        doc = obj.raw_extraction['documento']
        
        html = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
        html += '<tr style="background-color: #f8f9fa;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">📋 DOCUMENTO</th></tr>'
        
        fields = [
            ('Tipo de Comprobante', doc.get('tipo_comprobante')),
            ('Código AFIP', doc.get('codigo')),
            ('Número', doc.get('numero_comprobante')),
            ('Punto de Venta', doc.get('punto_venta')),
            ('Fecha de Emisión', doc.get('fecha_emision')),
            ('CAE', doc.get('cae')),
            ('Vencimiento CAE', doc.get('fecha_vencimiento_cae')),
            ('Moneda', doc.get('moneda')),
            ('Condición de Venta', doc.get('condicion_venta')),
        ]
        
        for label, value in fields:
            if value:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold; width: 200px;">{label}</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{value}</td></tr>'
        
        html += '</table>'
        return mark_safe(html)
    formatted_documento.short_description = 'Documento'
    
    def formatted_partes(self, obj):
        """Display partes (empresa y cliente) in formatted tables"""
        if not obj.raw_extraction or 'partes' not in obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay datos de partes disponibles</p>')
        
        partes = obj.raw_extraction['partes']
        empresa = partes.get('empresa', {})
        cliente = partes.get('cliente', {})
        
        html = '<div style="display: flex; gap: 20px;">'
        
        # Empresa
        html += '<div style="flex: 1;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e3f2fd;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #90caf9;">🏢 EMPRESA (Emisor)</th></tr>'
        
        empresa_fields = [
            ('Razón Social', empresa.get('razon_social')),
            ('CUIT', empresa.get('cuit')),
            ('Condición IVA', empresa.get('condicion_iva')),
            ('Domicilio', empresa.get('domicilio')),
            ('Provincia', empresa.get('provincia')),
            ('Ingresos Brutos', empresa.get('ingresos_brutos')),
        ]
        
        for label, value in empresa_fields:
            if value:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">{label}</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{value}</td></tr>'
        
        html += '</table></div>'
        
        # Cliente
        html += '<div style="flex: 1;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #fff3e0;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #ffb74d;">👤 CLIENTE (Receptor)</th></tr>'
        
        cliente_fields = [
            ('Nombre/Razón Social', cliente.get('apellido_nombre_razon_social')),
            ('CUIT', cliente.get('cuit')),
            ('Condición IVA', cliente.get('condicion_iva')),
            ('Domicilio', cliente.get('domicilio')),
            ('Provincia', cliente.get('provincia')),
        ]
        
        for label, value in cliente_fields:
            if value:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">{label}</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{value}</td></tr>'
        
        html += '</table></div></div>'
        
        return mark_safe(html)
    formatted_partes.short_description = 'Partes'
    
    def formatted_items_table(self, obj):
        """Display items in a beautiful table"""
        if not obj.raw_extraction or 'items' not in obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay items disponibles</p>')
        
        items = obj.raw_extraction['items']
        
        if not items:
            return format_html('<p style="color: #999;">Sin items</p>')
        
        html = '<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">'
        html += '<tr style="background-color: #e8f5e9;">'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: left;">#</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: left;">Código</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: left;">Descripción</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: right;">Cantidad</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: left;">U.M.</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: right;">Precio Unit.</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: right;">Subtotal</th>'
        html += '</tr>'
        
        for idx, item in enumerate(items, 1):
            html += f'<tr style="{"background-color: #f5f5f5;" if idx % 2 == 0 else ""}">'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{idx}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{item.get("codigo", "-")}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{item.get("descripcion", "-")}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">{item.get("cantidad", 0)}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{item.get("unidad_medida", "-")}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${item.get("precio_unitario", 0):,.2f}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right; font-weight: bold;">${item.get("subtotal", 0):,.2f}</td>'
            html += '</tr>'
        
        # Total
        total_items = sum(item.get('subtotal', 0) for item in items)
        html += '<tr style="background-color: #c8e6c9; font-weight: bold;">'
        html += '<td colspan="6" style="padding: 10px; text-align: right;">TOTAL ITEMS:</td>'
        html += f'<td style="padding: 10px; text-align: right;">${total_items:,.2f}</td>'
        html += '</tr>'
        
        html += '</table>'
        return mark_safe(html)
    formatted_items_table.short_description = 'Items'
    
    def formatted_fiscalidad(self, obj):
        """Display fiscal information in formatted tables"""
        if not obj.raw_extraction or 'fiscalidad' not in obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay datos fiscales disponibles</p>')
        
        fiscal = obj.raw_extraction['fiscalidad']
        totales = fiscal.get('totales', {})
        calculos = fiscal.get('calculos', {})
        impuestos = fiscal.get('impuestos', {})
        
        html = '<div>'
        
        # Totales
        html += '<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">'
        html += '<tr style="background-color: #fff9c4;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #fbc02d;">💰 TOTALES</th></tr>'
        
        totales_fields = [
            ('Subtotal Gravado', totales.get('subtotal_gravado')),
            ('Subtotal Exento', totales.get('subtotal_exento')),
            ('Subtotal No Gravado', totales.get('subtotal_no_gravado')),
            ('Descuentos', totales.get('descuentos')),
            ('Importe Total', totales.get('importe_total')),
        ]
        
        for label, value in totales_fields:
            if value is not None:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold; width: 250px;">{label}</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right; font-size: 16px;">${value:,.2f}</td></tr>'
        
        html += '</table>'
        
        # Impuestos
        if impuestos:
            html += '<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">'
            html += '<tr style="background-color: #f3e5f5;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #ab47bc;">📊 IMPUESTOS</th></tr>'
            
            iva_items = impuestos.get('iva', [])
            if iva_items:
                html += '<tr><td colspan="2" style="padding: 8px; font-weight: bold; background-color: #fafafa;">IVA</td></tr>'
                for iva in iva_items:
                    html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Alícuota {iva.get("alicuota", 0)}%</td>'
                    html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${iva.get("importe", 0):,.2f}</td></tr>'
            
            percepciones = impuestos.get('percepciones', [])
            if percepciones:
                html += '<tr><td colspan="2" style="padding: 8px; font-weight: bold; background-color: #fafafa;">Percepciones</td></tr>'
                for perc in percepciones:
                    html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">{perc.get("descripcion", "Percepción")}</td>'
                    html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${perc.get("importe", 0):,.2f}</td></tr>'
            
            retenciones = impuestos.get('retenciones', [])
            if retenciones:
                html += '<tr><td colspan="2" style="padding: 8px; font-weight: bold; background-color: #fafafa;">Retenciones</td></tr>'
                for ret in retenciones:
                    html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">{ret.get("descripcion", "Retención")}</td>'
                    html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${ret.get("importe", 0):,.2f}</td></tr>'
            
            html += '</table>'
        
        html += '</div>'
        return mark_safe(html)
    formatted_fiscalidad.short_description = 'Fiscalidad'
    
    def formatted_metadata(self, obj):
        """Display processing metadata"""
        if not obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay metadata disponible</p>')
        
        metadata = obj.raw_extraction.get('processing_metadata', {})
        gemini_info = metadata.get('gemini_retry', {})
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e1f5fe;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #4fc3f7;">🔧 METADATA DE PROCESAMIENTO</th></tr>'
        
        # Tiempo de extracción
        if obj.extraction_time:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold; width: 250px;">Tiempo de Extracción</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{obj.extraction_time:.2f} segundos</td></tr>'
        
        # Schema type
        html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Schema Utilizado</td>'
        html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{obj.schema_type}</td></tr>'
        
        # Gemini retry info
        if gemini_info.get('used'):
            html += '<tr><td colspan="2" style="padding: 8px; background-color: #e3f2fd; font-weight: bold;">🤖 Re-extracción con Gemini</td></tr>'
            html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Score inicial (Llama)</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{gemini_info.get("first_score", 0)*100:.1f}%</td></tr>'
            html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Score final (Gemini)</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{gemini_info.get("second_score", 0)*100:.1f}%</td></tr>'
            html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Mejora</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: #28a745; font-weight: bold;">+{gemini_info.get("improvement", 0):.1f}pp</td></tr>'
            html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Método usado</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{gemini_info.get("method_used", "N/A")}</td></tr>'
        else:
            reason = gemini_info.get('reason', 'No fue necesario')
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Re-extracción Gemini</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">No utilizada - {reason}</td></tr>'
        
        # Validation score
        if obj.validation_score:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Score de Validación</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{float(obj.validation_score)*100:.2f}%</td></tr>'
        
        html += '</table>'
        return mark_safe(html)
    formatted_metadata.short_description = 'Metadata'
    
    def formatted_validation_errors(self, obj):
        """Display validation errors and warnings"""
        if not obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay información de validación disponible</p>')
        
        validation = obj.raw_extraction.get('validation', {})
        errors = validation.get('errors', [])
        warnings = validation.get('warnings', [])
        alerts = validation.get('alerts', [])
        
        if not errors and not warnings and not alerts:
            return format_html('<p style="color: #28a745; font-weight: bold;">✅ Sin errores ni advertencias</p>')
        
        html = '<div>'
        
        # Errors
        if errors:
            html += '<div style="margin-bottom: 15px;">'
            html += '<h4 style="color: #dc3545; margin-bottom: 10px;">❌ ERRORES</h4>'
            html += '<ul style="margin: 0; padding-left: 20px;">'
            for error in errors:
                html += f'<li style="color: #dc3545; margin-bottom: 5px;">{error}</li>'
            html += '</ul></div>'
        
        # Warnings
        if warnings:
            html += '<div style="margin-bottom: 15px;">'
            html += '<h4 style="color: #ffc107; margin-bottom: 10px;">⚠️ ADVERTENCIAS</h4>'
            html += '<ul style="margin: 0; padding-left: 20px;">'
            for warning in warnings:
                html += f'<li style="color: #856404; margin-bottom: 5px;">{warning}</li>'
            html += '</ul></div>'
        
        # Alerts
        if alerts:
            html += '<div>'
            html += '<h4 style="color: #17a2b8; margin-bottom: 10px;">🔔 ALERTAS</h4>'
            html += '<ul style="margin: 0; padding-left: 20px;">'
            for alert in alerts:
                html += f'<li style="color: #0c5460; margin-bottom: 5px;">{alert}</li>'
            html += '</ul></div>'
        
        html += '</div>'
        return mark_safe(html)
    formatted_validation_errors.short_description = 'Validaciones'
    
    def formatted_raw_json(self, obj):
        """Display raw JSON in a formatted way"""
        if not obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay raw JSON disponible</p>')
        
        try:
            formatted_json = json.dumps(obj.raw_extraction, indent=2, ensure_ascii=False)
            html = f'<pre style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; max-height: 500px;">{formatted_json}</pre>'
            return mark_safe(html)
        except Exception as e:
            return format_html('<p style="color: #dc3545;">Error al formatear JSON: {}</p>', str(e))
    formatted_raw_json.short_description = 'Raw JSON'
    
    def changelist_view(self, request, extra_context=None):
        """Add statistics to the change list view"""
        extra_context = extra_context or {}
        
        # Get statistics
        stats = Invoice.objects.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            avg_extraction_time=Avg('extraction_time'),
            avg_score=Avg('validation_score'),
            total_amount=Sum('importe_total')
        )
        
        # Count Gemini retries
        gemini_used = 0
        if Invoice.objects.filter(status='completed').exists():
            for invoice in Invoice.objects.filter(status='completed'):
                if invoice.raw_extraction and invoice.raw_extraction.get('processing_metadata', {}).get('gemini_retry', {}).get('used'):
                    gemini_used += 1
        
        extra_context['stats'] = {
            'total': stats['total'] or 0,
            'completed': stats['completed'] or 0,
            'avg_time': stats['avg_extraction_time'] or 0,
            'avg_score': (stats['avg_score'] or 0) * 100,
            'total_amount': stats['total_amount'] or 0,
            'gemini_used': gemini_used,
            'gemini_percentage': (gemini_used / stats['completed'] * 100) if stats['completed'] else 0
        }
        
        return super().changelist_view(request, extra_context)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    """Admin interface for InvoiceItem model"""
    list_display = [
        'id', 'invoice_link', 'codigo', 'descripcion_truncated', 'cantidad', 
        'unidad_medida', 'formatted_price', 'formatted_subtotal', 'order'
    ]
    list_filter = ['invoice__status', 'unidad_medida']
    search_fields = ['descripcion', 'codigo', 'invoice__numero_comprobante']
    ordering = ['invoice', 'order']
    readonly_fields = ['invoice', 'order']
    
    def invoice_link(self, obj):
        """Link to parent invoice"""
        url = reverse('admin:invoice_extractor_invoice_change', args=[obj.invoice.id])
        return format_html('<a href="{}">{}</a>', url, obj.invoice.numero_comprobante or f'Invoice #{obj.invoice.id}')
    invoice_link.short_description = 'Comprobante'
    
    def descripcion_truncated(self, obj):
        """Truncate description for list view"""
        if len(obj.descripcion) > 50:
            return obj.descripcion[:50] + '...'
        return obj.descripcion
    descripcion_truncated.short_description = 'Descripción'
    
    def formatted_price(self, obj):
        """Format price with currency"""
        formatted_value = f'${float(obj.precio_unitario):,.2f}'
        return format_html('{}', formatted_value)
    formatted_price.short_description = 'Precio Unit.'
    
    def formatted_subtotal(self, obj):
        """Format subtotal with currency"""
        formatted_value = f'${float(obj.subtotal):,.2f}'
        return format_html('<strong>{}</strong>', formatted_value)
    formatted_subtotal.short_description = 'Subtotal'
