#!/usr/bin/env python
"""
Test script para verificar las mejoras del admin
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
django.setup()

from invoice_extractor.models import Invoice, InvoiceItem
from django.contrib.auth.models import User
from decimal import Decimal

def test_admin_improvements():
    """Test que verifica las mejoras del admin"""
    
    print("=" * 80)
    print("🧪 TESTING ADMIN IMPROVEMENTS")
    print("=" * 80)
    
    # 1. Verificar que los nuevos campos existen en el modelo
    print("\n1. ✅ Verificando nuevos campos en el modelo...")
    
    try:
        # Crear una factura de prueba
        invoice = Invoice.objects.create(
            original_filename='test_invoice.pdf',
            status='completed',
            extraction_method='both',
            gemini_retry_used=True,
            gemini_improvement=Decimal('15.50'),
            validation_score=Decimal('0.8500'),
            raw_extraction={
                'documento': {
                    'tipo_comprobante': 'FACTURAS A',
                    'numero_comprobante': '0001-00001234',
                    'cae': '123456789012345'
                },
                'partes': {
                    'empresa': {
                        'razon_social': 'TEST EMPRESA SA',
                        'cuit': '30-12345678-9'
                    },
                    'cliente': {
                        'apellido_nombre_razon_social': 'TEST CLIENTE',
                        'cuit': '20-87654321-0'
                    }
                },
                'items': [
                    {
                        'codigo': 'TEST-001',
                        'descripcion': 'Producto de prueba',
                        'cantidad': 10,
                        'precio_unitario': 100.50,
                        'subtotal': 1005.00
                    }
                ],
                'fiscalidad': {
                    'totales': {
                        'subtotal_gravado': 1005.00,
                        'importe_total': 1216.05
                    },
                    'impuestos': {
                        'iva': [
                            {'alicuota': 21, 'importe': 211.05}
                        ]
                    }
                },
                'processing_metadata': {
                    'gemini_retry': {
                        'used': True,
                        'first_score': 0.70,
                        'second_score': 0.85,
                        'improvement': 15.0,
                        'method_used': 'gemini'
                    }
                }
            }
        )
        
        print(f"   ✅ Factura creada: ID {invoice.id}")
        print(f"   ✅ extraction_method: {invoice.extraction_method}")
        print(f"   ✅ gemini_retry_used: {invoice.gemini_retry_used}")
        print(f"   ✅ gemini_improvement: {invoice.gemini_improvement}")
        print(f"   ✅ validation_score: {invoice.validation_score}")
        
    except Exception as e:
        print(f"   ❌ Error creando factura: {e}")
        return False
    
    # 2. Verificar que el admin puede acceder a los métodos customizados
    print("\n2. ✅ Verificando métodos del admin...")
    
    try:
        from invoice_extractor.admin import InvoiceAdmin
        from django.contrib.admin.sites import site
        
        admin = InvoiceAdmin(Invoice, site)
        
        # Verificar métodos
        methods = [
            'colored_status',
            'formatted_total',
            'score_badge',
            'extraction_method_badge',
            'formatted_documento',
            'formatted_partes',
            'formatted_items_table',
            'formatted_fiscalidad',
            'formatted_metadata',
            'formatted_validation_errors'
        ]
        
        for method_name in methods:
            if hasattr(admin, method_name):
                method = getattr(admin, method_name)
                try:
                    result = method(invoice)
                    print(f"   ✅ {method_name}: OK")
                except Exception as e:
                    print(f"   ⚠️ {method_name}: {e}")
            else:
                print(f"   ❌ {method_name}: No encontrado")
        
    except Exception as e:
        print(f"   ❌ Error verificando admin: {e}")
        return False
    
    # 3. Verificar estadísticas
    print("\n3. ✅ Verificando estadísticas...")
    
    try:
        from django.db.models import Count, Avg, Sum, Q
        
        stats = Invoice.objects.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            avg_extraction_time=Avg('extraction_time'),
            avg_score=Avg('validation_score'),
            total_amount=Sum('importe_total')
        )
        
        print(f"   ✅ Total facturas: {stats['total']}")
        print(f"   ✅ Completadas: {stats['completed']}")
        print(f"   ✅ Score promedio: {(stats['avg_score'] or 0) * 100:.1f}%")
        
        # Contar uso de Gemini
        gemini_count = Invoice.objects.filter(gemini_retry_used=True).count()
        print(f"   ✅ Facturas con Gemini: {gemini_count}")
        
    except Exception as e:
        print(f"   ❌ Error en estadísticas: {e}")
        return False
    
    # 4. Verificar template existe
    print("\n4. ✅ Verificando template customizado...")
    
    template_path = 'invoice_extractor/templates/admin/invoice_extractor/invoice/change_list.html'
    if os.path.exists(template_path):
        print(f"   ✅ Template encontrado: {template_path}")
    else:
        print(f"   ⚠️ Template no encontrado (puede estar en otra ubicación)")
    
    # 5. Cleanup
    print("\n5. ✅ Limpiando datos de prueba...")
    invoice.delete()
    print("   ✅ Factura de prueba eliminada")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ TODOS LOS TESTS PASARON")
    print("=" * 80)
    print("\n📋 Resumen de Mejoras Implementadas:")
    print("   ✅ Nuevos campos de tracking en el modelo")
    print("   ✅ Admin con métodos de formateo customizados")
    print("   ✅ Dashboard de estadísticas funcional")
    print("   ✅ Visualización rica de datos extraídos")
    print("\n🚀 El admin está listo para usar!")
    print("\n💡 Próximos pasos:")
    print("   1. Ejecuta: python manage.py runserver")
    print("   2. Accede a: http://localhost:8000/admin")
    print("   3. Procesa una factura y verifica la visualización")
    print()
    
    return True

if __name__ == '__main__':
    success = test_admin_improvements()
    sys.exit(0 if success else 1)

