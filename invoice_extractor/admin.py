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
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for Invoice model - Estructura limpia"""
    list_display = [
        'id', 'colored_status', 'numero_comprobante', 'tipo_comprobante', 
        'empresa_razon_social', 'formatted_total', 'score_badge',
        'extraction_method_badge', 'uploaded_at'
    ]
    list_filter = ['status', 'uploaded_at', 'tipo_comprobante', 'extraction_method']
    search_fields = [
        'numero_comprobante', 'empresa_razon_social', 'empresa_cuit',
        'cliente_nombre', 'cliente_cuit', 'cae'
    ]
    readonly_fields = [
        'uploaded_at', 'processed_at', 'extraction_time', 
        'formatted_documento', 'formatted_partes',
        'formatted_items_table', 'formatted_totales', 'formatted_validacion',
        'formatted_alertas', 'formatted_metadata', 'formatted_raw_json'
    ]
    
    fieldsets = (
        ('📄 Estado del Documento', {
            'fields': (
                'document', 'original_filename', 'status', 
                'uploaded_at', 'processed_at', 'extraction_time'
            )
        }),
        ('📋 Documento', {
            'fields': ('formatted_documento',),
        }),
        ('👥 Partes (Emisor y Receptor)', {
            'fields': ('formatted_partes',),
        }),
        ('📦 Items', {
            'fields': ('formatted_items_table',),
        }),
        ('💰 Totales e Impuestos', {
            'fields': ('formatted_totales',),
        }),
        ('📊 Validación', {
            'fields': ('formatted_validacion',),
        }),
        ('⚠️ Alertas y Errores', {
            'fields': ('formatted_alertas',),
            'classes': ('collapse',)
        }),
        ('🔧 Metadata Técnica', {
            'fields': ('formatted_metadata',),
            'classes': ('collapse',)
        }),
        ('🔍 Raw JSON', {
            'fields': ('formatted_raw_json',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [InvoiceItemInline]
    
    # =========================================================================
    # HELPERS PARA OBTENER DATOS (soporta nueva estructura y legacy)
    # =========================================================================
    
    def _get_factura_data(self, obj):
        """Obtiene datos de factura (nueva estructura o legacy)."""
        if not obj.raw_extraction:
            return None
        
        # Nueva estructura
        if 'factura' in obj.raw_extraction:
            return obj.raw_extraction['factura']
        
        # Legacy: buscar en processed_data o raw_data
        if 'processed_data' in obj.raw_extraction:
            return obj.raw_extraction['processed_data']
        if 'raw_data' in obj.raw_extraction:
            return obj.raw_extraction['raw_data']
        
        return obj.raw_extraction
    
    def _get_validacion_data(self, obj):
        """Obtiene datos de validación (nueva estructura o legacy)."""
        if not obj.raw_extraction:
            return None
        
        # Nueva estructura
        if 'validacion' in obj.raw_extraction:
            return obj.raw_extraction['validacion']
        
        # Legacy
        return obj.raw_extraction.get('validation_result', {})
    
    def _get_alertas_data(self, obj):
        """Obtiene alertas (nueva estructura o legacy)."""
        if not obj.raw_extraction:
            return None
        
        # Nueva estructura
        if 'alertas' in obj.raw_extraction:
            return obj.raw_extraction['alertas']
        
        # Legacy
        validation = obj.raw_extraction.get('validation_result', {})
        return {
            'errores': validation.get('validation_errors', []),
            'warnings': validation.get('validation_warnings', []),
            'correcciones_aplicadas': validation.get('corrections_applied', []),
            'recomendaciones': validation.get('recommendations', [])
        }
    
    def _get_metadata_data(self, obj):
        """Obtiene metadata (nueva estructura o legacy)."""
        if not obj.raw_extraction:
            return None
        
        # Nueva estructura
        if 'metadata' in obj.raw_extraction:
            return obj.raw_extraction['metadata']
        
        # Legacy
        return obj.raw_extraction.get('processing_metadata', {})
    
    # =========================================================================
    # LIST DISPLAY METHODS
    # =========================================================================
    
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
        
        score_text = f'{icon} {score_percent:.0f}%'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, score_text
        )
    score_badge.short_description = 'Score'
    
    def extraction_method_badge(self, obj):
        """Show which extraction method was used"""
        method = obj.extraction_method or 'llama'
        
        if method == 'gemini' or obj.gemini_retry_used:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">🤖 Gemini</span>'
            )
        
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">🦙 Llama</span>'
        )
    extraction_method_badge.short_description = 'Método'
    
    # =========================================================================
    # DETAIL VIEW METHODS
    # =========================================================================
    
    def formatted_documento(self, obj):
        """Display documento section"""
        factura = self._get_factura_data(obj)
        if not factura:
            return format_html('<p style="color: #999;">No hay datos disponibles</p>')
        
        # Nueva estructura: factura.documento
        # Legacy: documento directamente
        doc = factura.get('documento', factura)
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f8f9fa;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #dee2e6;">📋 DOCUMENTO</th></tr>'
        
        fields = [
            ('Tipo', doc.get('tipo') or doc.get('tipo_comprobante')),
            ('Código AFIP', doc.get('codigo')),
            ('Número Completo', doc.get('numero')),
            ('Punto de Venta', doc.get('punto_venta')),
            ('Número', doc.get('numero_comprobante')),
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
        """Display partes (emisor y receptor)"""
        factura = self._get_factura_data(obj)
        if not factura:
            return format_html('<p style="color: #999;">No hay datos disponibles</p>')
        
        # Nueva estructura: emisor/receptor
        # Legacy: partes.empresa/partes.cliente
        emisor = factura.get('emisor') or factura.get('partes', {}).get('empresa', {})
        receptor = factura.get('receptor') or factura.get('partes', {}).get('cliente', {})
        
        html = '<div style="display: flex; gap: 20px; flex-wrap: wrap;">'
        
        # Emisor
        html += '<div style="flex: 1; min-width: 300px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e3f2fd;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #90caf9;">🏢 EMISOR</th></tr>'
        
        emisor_fields = [
            ('Razón Social', emisor.get('razon_social')),
            ('CUIT', emisor.get('cuit')),
            ('Condición IVA', emisor.get('condicion_iva')),
            ('Domicilio', emisor.get('domicilio')),
            ('Provincia', emisor.get('provincia')),
            ('Ingresos Brutos', emisor.get('ingresos_brutos')),
            ('Inicio Actividades', emisor.get('inicio_actividades') or emisor.get('fecha_inicio_actividades')),
        ]
        
        for label, value in emisor_fields:
            if value:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">{label}</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{value}</td></tr>'
        
        html += '</table></div>'
        
        # Receptor
        html += '<div style="flex: 1; min-width: 300px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #fff3e0;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #ffb74d;">👤 RECEPTOR</th></tr>'
        
        receptor_fields = [
            ('Razón Social', receptor.get('razon_social') or receptor.get('apellido_nombre_razon_social')),
            ('CUIT', receptor.get('cuit')),
            ('Condición IVA', receptor.get('condicion_iva')),
            ('Domicilio', receptor.get('domicilio')),
            ('Provincia', receptor.get('provincia')),
        ]
        
        for label, value in receptor_fields:
            if value:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">{label}</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{value}</td></tr>'
        
        html += '</table></div></div>'
        
        return mark_safe(html)
    formatted_partes.short_description = 'Partes'
    
    def formatted_items_table(self, obj):
        """Display items in a table"""
        factura = self._get_factura_data(obj)
        if not factura:
            return format_html('<p style="color: #999;">No hay items disponibles</p>')
        
        items = factura.get('items', [])
        if not items:
            return format_html('<p style="color: #999;">Sin items</p>')
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e8f5e9;">'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: left;">#</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: left;">Descripción</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: right;">Cantidad</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: right;">Precio Unit.</th>'
        html += '<th style="padding: 10px; border-bottom: 2px solid #66bb6a; text-align: right;">Subtotal</th>'
        html += '</tr>'
        
        total_items = 0
        for idx, item in enumerate(items, 1):
            subtotal = float(item.get('subtotal', 0) or 0)
            total_items += subtotal
            
            bg = 'background-color: #f5f5f5;' if idx % 2 == 0 else ''
            html += f'<tr style="{bg}">'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{idx}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{item.get("descripcion", "-")}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">{item.get("cantidad", 0)}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${float(item.get("precio_unitario", 0) or 0):,.2f}</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right; font-weight: bold;">${subtotal:,.2f}</td>'
            html += '</tr>'
        
        # Total row
        html += '<tr style="background-color: #c8e6c9; font-weight: bold;">'
        html += '<td colspan="4" style="padding: 10px; text-align: right;">TOTAL ITEMS:</td>'
        html += f'<td style="padding: 10px; text-align: right;">${total_items:,.2f}</td>'
        html += '</tr>'
        
        html += '</table>'
        return mark_safe(html)
    formatted_items_table.short_description = 'Items'
    
    def formatted_totales(self, obj):
        """Display totales e impuestos"""
        factura = self._get_factura_data(obj)
        if not factura:
            return format_html('<p style="color: #999;">No hay datos disponibles</p>')
        
        # Nueva estructura: factura.totales
        # Legacy: fiscalidad.totales + fiscalidad.impuestos
        totales = factura.get('totales', {})
        if not totales and 'fiscalidad' in factura:
            totales = factura['fiscalidad'].get('totales', {})
        
        html = '<div style="display: flex; gap: 20px; flex-wrap: wrap;">'
        
        # Totales principales
        html += '<div style="flex: 1; min-width: 300px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #fff9c4;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #fbc02d;">💰 TOTALES</th></tr>'
        
        subtotal = totales.get('subtotal_gravado')
        if subtotal:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Subtotal Gravado</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${float(subtotal):,.2f}</td></tr>'
        
        descuentos = totales.get('descuentos', 0)
        if descuentos and float(descuentos) > 0:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Descuentos</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right; color: #dc3545;">-${float(descuentos):,.2f}</td></tr>'
        
        total = totales.get('importe_total')
        if total:
            html += f'<tr style="background-color: #fff59d;"><td style="padding: 10px; font-weight: bold; font-size: 16px;">IMPORTE TOTAL</td>'
            html += f'<td style="padding: 10px; text-align: right; font-weight: bold; font-size: 18px; color: #28a745;">${float(total):,.2f}</td></tr>'
        
        html += '</table></div>'
        
        # IVA y otros impuestos
        html += '<div style="flex: 1; min-width: 300px;">'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f3e5f5;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #ab47bc;">📊 IMPUESTOS</th></tr>'
        
        # IVA
        iva = totales.get('iva', {})
        if iva:
            for key, value in iva.items():
                if value and float(value) > 0:
                    label = key.replace('_', ' ').title()
                    html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{label}</td>'
                    html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${float(value):,.2f}</td></tr>'
        
        # Percepciones
        percepciones = totales.get('percepciones', {})
        if percepciones:
            total_perc = percepciones.get('total_percepciones', 0)
            if total_perc and float(total_perc) > 0:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Total Percepciones</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right;">${float(total_perc):,.2f}</td></tr>'
        
        # Retenciones
        retenciones = totales.get('retenciones', {})
        if retenciones:
            total_ret = retenciones.get('total_retenciones', 0)
            if total_ret and float(total_ret) > 0:
                html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Total Retenciones</td>'
                html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; text-align: right; color: #dc3545;">-${float(total_ret):,.2f}</td></tr>'
        
        html += '</table></div></div>'
        
        return mark_safe(html)
    formatted_totales.short_description = 'Totales'
    
    def formatted_validacion(self, obj):
        """Display validation score and status"""
        validacion = self._get_validacion_data(obj)
        if not validacion:
            return format_html('<p style="color: #999;">No hay datos de validación</p>')
        
        # Nueva estructura
        score = validacion.get('score', validacion.get('validation_score', 0))
        if isinstance(score, float) and score <= 1:
            score = score * 100  # Convertir a porcentaje si es decimal
        
        nivel = validacion.get('nivel_confianza', 'desconocido')
        indicador = validacion.get('indicador', '⚪')
        requiere = validacion.get('requiere_revision', False)
        tiene_errores = validacion.get('tiene_errores', False)
        
        # Determinar color
        if score >= 80:
            color = '#28a745'
        elif score >= 60:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        html = '<div style="display: flex; gap: 20px; align-items: center; padding: 15px; background-color: #f8f9fa; border-radius: 8px;">'
        
        # Score grande
        html += f'<div style="text-align: center; padding: 20px;">'
        html += f'<div style="font-size: 48px; font-weight: bold; color: {color};">{score:.0f}%</div>'
        html += f'<div style="font-size: 14px; color: #666;">Score de Validación</div>'
        html += '</div>'
        
        # Detalles
        html += '<div style="flex: 1;">'
        html += f'<p><strong>Nivel de Confianza:</strong> {indicador} {nivel.upper()}</p>'
        
        if requiere:
            html += '<p style="color: #ffc107;"><strong>⚠️ Requiere revisión manual</strong></p>'
        
        if tiene_errores:
            html += '<p style="color: #dc3545;"><strong>❌ Contiene errores de validación</strong></p>'
        else:
            html += '<p style="color: #28a745;"><strong>✅ Sin errores críticos</strong></p>'
        
        html += '</div></div>'
        
        return mark_safe(html)
    formatted_validacion.short_description = 'Validación'
    
    def formatted_alertas(self, obj):
        """Display alerts, errors, and warnings"""
        alertas = self._get_alertas_data(obj)
        if not alertas:
            return format_html('<p style="color: #28a745;">✅ Sin alertas</p>')
        
        errores = alertas.get('errores', [])
        warnings = alertas.get('warnings', [])
        correcciones = alertas.get('correcciones_aplicadas', [])
        recomendaciones = alertas.get('recomendaciones', [])
        
        if not errores and not warnings and not correcciones:
            return format_html('<p style="color: #28a745; font-weight: bold;">✅ Sin errores ni advertencias</p>')
        
        html = '<div>'
        
        # Errores
        if errores:
            html += '<div style="margin-bottom: 15px; padding: 10px; background-color: #ffebee; border-radius: 5px;">'
            html += f'<h4 style="color: #dc3545; margin: 0 0 10px 0;">❌ ERRORES ({len(errores)})</h4>'
            html += '<ul style="margin: 0; padding-left: 20px;">'
            for error in errores:
                html += f'<li style="color: #dc3545; margin-bottom: 5px;">{error}</li>'
            html += '</ul></div>'
        
        # Warnings
        if warnings:
            html += '<div style="margin-bottom: 15px; padding: 10px; background-color: #fff8e1; border-radius: 5px;">'
            html += f'<h4 style="color: #ff8f00; margin: 0 0 10px 0;">⚠️ ADVERTENCIAS ({len(warnings)})</h4>'
            html += '<ul style="margin: 0; padding-left: 20px;">'
            for warning in warnings:
                html += f'<li style="color: #856404; margin-bottom: 5px;">{warning}</li>'
            html += '</ul></div>'
        
        # Correcciones aplicadas
        if correcciones:
            html += '<div style="margin-bottom: 15px; padding: 10px; background-color: #e3f2fd; border-radius: 5px;">'
            html += f'<h4 style="color: #1976d2; margin: 0 0 10px 0;">🔧 CORRECCIONES APLICADAS ({len(correcciones)})</h4>'
            html += '<ul style="margin: 0; padding-left: 20px;">'
            for corr in correcciones:
                html += f'<li style="color: #0d47a1; margin-bottom: 5px;">{corr}</li>'
            html += '</ul></div>'
        
        # Recomendaciones
        if recomendaciones:
            html += '<div style="padding: 10px; background-color: #f5f5f5; border-radius: 5px;">'
            html += '<h4 style="color: #666; margin: 0 0 10px 0;">💡 RECOMENDACIONES</h4>'
            html += '<ul style="margin: 0; padding-left: 20px;">'
            for rec in recomendaciones:
                html += f'<li style="color: #666; margin-bottom: 5px;">{rec}</li>'
            html += '</ul></div>'
        
        html += '</div>'
        return mark_safe(html)
    formatted_alertas.short_description = 'Alertas'
    
    def formatted_metadata(self, obj):
        """Display processing metadata"""
        metadata = self._get_metadata_data(obj)
        if not metadata:
            return format_html('<p style="color: #999;">No hay metadata disponible</p>')
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #e1f5fe;"><th colspan="2" style="padding: 10px; text-align: left; border-bottom: 2px solid #4fc3f7;">🔧 METADATA</th></tr>'
        
        # Tiempo
        tiempo = metadata.get('tiempo_extraccion_seg') or obj.extraction_time
        if tiempo:
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Tiempo de Extracción</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{float(tiempo):.2f} segundos</td></tr>'
        
        # Método
        metodo = metadata.get('metodo_extraccion') or obj.extraction_method
        html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Método de Extracción</td>'
        html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{metodo}</td></tr>'
        
        # Schema
        schema = metadata.get('schema_utilizado') or obj.schema_type
        html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Schema Utilizado</td>'
        html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{schema}</td></tr>'
        
        # Gemini retry
        gemini_retry = metadata.get('gemini_retry', {})
        if gemini_retry.get('utilizado'):
            html += '<tr><td colspan="2" style="padding: 8px; background-color: #e3f2fd; font-weight: bold;">🤖 Re-extracción con Gemini</td></tr>'
            html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Score inicial</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{gemini_retry.get("score_inicial", 0):.1f}%</td></tr>'
            html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Score final</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{gemini_retry.get("score_final", 0):.1f}%</td></tr>'
            mejora = gemini_retry.get("mejora_pp", 0)
            color = '#28a745' if mejora > 0 else '#dc3545'
            html += f'<tr><td style="padding: 8px 8px 8px 30px; border-bottom: 1px solid #dee2e6;">Mejora</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6; color: {color}; font-weight: bold;">{mejora:+.1f}pp</td></tr>'
        
        # Orquestación
        orquestacion = metadata.get('orquestacion', {})
        if orquestacion:
            estrategia = orquestacion.get('estrategia', 'N/A')
            html += f'<tr><td style="padding: 8px; border-bottom: 1px solid #dee2e6; font-weight: bold;">Estrategia de Orquestación</td>'
            html += f'<td style="padding: 8px; border-bottom: 1px solid #dee2e6;">{estrategia}</td></tr>'
        
        html += '</table>'
        return mark_safe(html)
    formatted_metadata.short_description = 'Metadata'
    
    def formatted_raw_json(self, obj):
        """Display raw JSON"""
        if not obj.raw_extraction:
            return format_html('<p style="color: #999;">No hay JSON disponible</p>')
        
        try:
            formatted_json = json.dumps(obj.raw_extraction, indent=2, ensure_ascii=False)
            html = f'<pre style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; max-height: 500px; font-size: 12px;">{formatted_json}</pre>'
            return mark_safe(html)
        except Exception as e:
            return format_html('<p style="color: #dc3545;">Error: {}</p>', str(e))
    formatted_raw_json.short_description = 'Raw JSON'
    
    # =========================================================================
    # CHANGELIST VIEW
    # =========================================================================
    
    def changelist_view(self, request, extra_context=None):
        """Add statistics to the change list view"""
        extra_context = extra_context or {}
        
        stats = Invoice.objects.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            avg_extraction_time=Avg('extraction_time'),
            avg_score=Avg('validation_score'),
            total_amount=Sum('importe_total')
        )
        
        # Count Gemini usage
        gemini_used = Invoice.objects.filter(
            Q(extraction_method='gemini') | Q(gemini_retry_used=True)
        ).count()
        
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
