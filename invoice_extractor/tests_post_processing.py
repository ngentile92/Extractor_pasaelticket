# invoice_extractor/tests_post_processing.py
"""
🧪 Tests para el sistema de post-procesamiento

Tests unitarios para:
- Normalización
- Correcciones
- Validaciones fiscales
- Post-procesador completo
"""

from django.test import TestCase
from decimal import Decimal

from invoice_extractor.utils.normalization import (
    is_nullish,
    convert_nullish_to_none,
    normalize_text,
    normalize_cuit,
    normalize_number,
    normalize_all
)
from invoice_extractor.utils.corrections import (
    apply_items_correction,
    apply_document_type_correction,
    apply_fiscal_calculations_correction
)
from invoice_extractor.validators.afip_document_types import afip_catalog
from invoice_extractor.validators.fiscal_validator import FiscalValidator
from invoice_extractor.utils.post_processor import process_invoice


class NormalizationTests(TestCase):
    """Tests para el módulo de normalización"""
    
    def test_is_nullish(self):
        """Test detección de valores nullish"""
        self.assertTrue(is_nullish(None))
        self.assertTrue(is_nullish(""))
        self.assertTrue(is_nullish("."))
        self.assertTrue(is_nullish("-"))
        self.assertTrue(is_nullish("   "))
        self.assertFalse(is_nullish("VALID TEXT"))
        self.assertFalse(is_nullish(0))
    
    def test_normalize_text(self):
        """Test normalización de texto"""
        self.assertEqual(normalize_text("  hello  world  "), "HELLO WORLD")
        self.assertEqual(normalize_text("mixed   Case"), "MIXED CASE")
        self.assertIsNone(normalize_text("."))
        self.assertIsNone(normalize_text(None))
    
    def test_normalize_cuit(self):
        """Test normalización de CUIT"""
        self.assertEqual(normalize_cuit("30525390085"), "30-52539008-5")
        self.assertEqual(normalize_cuit("30-52539008-5"), "30-52539008-5")
        self.assertEqual(normalize_cuit("30 52539008 5"), "30-52539008-5")
        self.assertIsNone(normalize_cuit("invalid"))
        self.assertIsNone(normalize_cuit("123"))  # Too short
    
    def test_normalize_number(self):
        """Test normalización de números"""
        # Formato argentino
        self.assertEqual(normalize_number("1.234,56"), 1234.56)
        # Formato inglés
        self.assertEqual(normalize_number("1,234.56"), 1234.56)
        # Con símbolo de moneda
        self.assertEqual(normalize_number("$1234.56"), 1234.56)
        # Negativos
        self.assertEqual(normalize_number("-100"), -100.0)
        # Force positive
        self.assertEqual(normalize_number("-100", force_positive=True), 100.0)


class AFIPDocumentTypeTests(TestCase):
    """Tests para el catálogo AFIP"""
    
    def test_get_by_code(self):
        """Test búsqueda por código"""
        doc = afip_catalog.get_by_code("001")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.denominacion, "FACTURAS A")
        self.assertEqual(doc.regimen, "A")
    
    def test_get_by_name(self):
        """Test búsqueda por nombre"""
        result = afip_catalog.get_by_name("FACTURA A")
        self.assertIsNotNone(result)
        codigo, doc = result
        self.assertEqual(codigo, "001")
        self.assertEqual(doc.denominacion, "FACTURAS A")
    
    def test_validate_match_correct(self):
        """Test validación de coincidencia correcta"""
        validation = afip_catalog.validate_match("001", "FACTURAS A")
        self.assertTrue(validation["is_valid"])
        self.assertEqual(validation["match_score"], 1.0)
        self.assertEqual(validation["codigo_encontrado"], "001")
    
    def test_validate_match_inconsistent(self):
        """Test validación de coincidencia inconsistente"""
        validation = afip_catalog.validate_match("001", "FACTURAS B")
        self.assertFalse(validation["is_valid"])
        self.assertGreater(len(validation["inconsistencias"]), 0)


class CorrectionsTests(TestCase):
    """Tests para el módulo de correcciones"""
    
    def test_items_correction_swap(self):
        """Test intercambio de código/descripción"""
        data = {
            "items": [
                {
                    "codigo": "DESCRIPCION MUY LARGA QUE DEBERIA SER LA DESCRIPCION",
                    "descripcion": "COD123",
                    "cantidad": 1,
                    "precio_unitario": 100,
                    "subtotal": 100
                }
            ]
        }
        
        corrected = apply_items_correction(data)
        item = corrected["items"][0]
        
        # Verificar que se intercambiaron
        self.assertEqual(item["codigo"], "COD123")
        self.assertIn("DESCRIPCION", item["descripcion"])
    
    def test_fiscal_calculations_correction(self):
        """Test recálculo de totales fiscales"""
        data = {
            "fiscalidad": {
                "impuestos": {
                    "iva_21": 100.50,
                    "iva_105": 50.25,
                    "percepcion_iva": 10.00,
                    "retencion_iva": 5.00
                },
                "calculos": {}
            }
        }
        
        corrected = apply_fiscal_calculations_correction(data)
        calculos = corrected["fiscalidad"]["calculos"]
        
        # Verificar cálculos
        self.assertEqual(calculos["total_iva_calculado"], 150.75)
        self.assertEqual(calculos["total_percepciones_calculado"], 10.00)
        self.assertEqual(calculos["total_retenciones_calculado"], 5.00)


class FiscalValidatorTests(TestCase):
    """Tests para el validador fiscal"""
    
    def setUp(self):
        self.validator = FiscalValidator()
    
    def test_validator_initialization(self):
        """Test inicialización del validador"""
        self.assertIsNotNone(self.validator)
        self.assertEqual(self.validator.validation_score, 1.0)
        self.assertEqual(len(self.validator.validation_errors), 0)
    
    def test_arithmetic_consistency(self):
        """Test validación de consistencia aritmética"""
        invoice_data = {
            "items": [
                {"subtotal": 100.00},
                {"subtotal": 50.00}
            ],
            "fiscalidad": {
                "totales": {
                    "subtotal_gravado": 150.00,
                    "importe_total": 181.50
                },
                "impuestos": {
                    "iva_21": 31.50
                }
            }
        }
        
        result = self.validator._validate_arithmetic_invariants(invoice_data)
        
        # No debe haber errores significativos
        self.assertLess(
            result["differences"].get("items_vs_subtotal", 0),
            1.0  # Tolerancia de $1
        )


class PostProcessorIntegrationTests(TestCase):
    """Tests de integración para el post-procesador completo"""
    
    def test_full_processing_pipeline(self):
        """Test del pipeline completo de post-procesamiento"""
        # Datos simulados de extracción
        extracted_data = {
            "documento": {
                "tipo_comprobante": "factura a",  # Minúsculas, debe normalizarse
                "codigo": "001",
                "numero_comprobante": "  0001-00000123  ",  # Con espacios
                "fecha_emision": "16/10/2023",  # Formato argentino
                "moneda": "ARS"
            },
            "partes": {
                "empresa": {
                    "razon_social": "  empresa  test  s.a.  ",  # Espacios múltiples
                    "cuit": "30525390085",  # Sin guiones
                    "condicion_iva": "resp insc"  # Abreviado
                },
                "cliente": {
                    "apellido_nombre_razon_social": "cliente test",
                    "cuit": "20123456789"
                }
            },
            "items": [
                {
                    "codigo": None,  # Nullish
                    "descripcion": "PRODUCTO 1",
                    "cantidad": 2,
                    "precio_unitario": 100.00,
                    "subtotal": None  # Debe calcularse
                }
            ],
            "fiscalidad": {
                "totales": {
                    "subtotal_gravado": 200.00,
                    "importe_total": 242.00
                },
                "impuestos": {
                    "iva_21": 42.00,
                    "percepcion_iva": 0
                },
                "calculos": {}
            }
        }
        
        # Procesar
        result = process_invoice(extracted_data)
        
        # Verificar resultado
        self.assertIn("processed_data", result)
        self.assertIn("validation_result", result)
        self.assertIn("processing_metadata", result)
        
        processed = result["processed_data"]
        validation = result["validation_result"]
        
        # Verificar normalizaciones
        # El tipo de comprobante puede ser "FACTURA A" o "FACTURAS A" dependiendo de la corrección AFIP
        self.assertIn(processed["documento"]["tipo_comprobante"], ["FACTURA A", "FACTURAS A"])
        self.assertEqual(processed["documento"]["numero_comprobante"], "0001-00000123")
        self.assertEqual(processed["partes"]["empresa"]["cuit"], "30-52539008-5")
        self.assertEqual(processed["partes"]["empresa"]["condicion_iva"], "RESPONSABLE INSCRIPTO")
        
        # Verificar cálculos
        self.assertEqual(processed["items"][0]["subtotal"], 200.00)
        
        # Verificar validation_score existe
        self.assertIn("validation_score", validation)
        self.assertIsInstance(validation["validation_score"], float)
        self.assertGreaterEqual(validation["validation_score"], 0.0)
        self.assertLessEqual(validation["validation_score"], 1.0)


class EdgeCaseTests(TestCase):
    """Tests de casos borde y edge cases"""
    
    def test_empty_data(self):
        """Test con datos vacíos"""
        result = process_invoice({})
        self.assertIn("processed_data", result)
        self.assertIn("validation_result", result)
    
    def test_missing_required_fields(self):
        """Test con campos requeridos faltantes"""
        data = {
            "items": [],
            "documento": {},
            "partes": {}
        }
        result = process_invoice(data)
        
        # Debe completarse sin errores
        self.assertIsNotNone(result)
        self.assertIn("validation_result", result)
    
    def test_invalid_numbers(self):
        """Test con números inválidos"""
        data = {
            "fiscalidad": {
                "totales": {
                    "subtotal_gravado": "invalid",
                    "importe_total": "not a number"
                }
            }
        }
        
        # No debe lanzar excepción
        result = process_invoice(data)
        self.assertIsNotNone(result)


# Script para ejecutar tests manualmente
if __name__ == '__main__':
    import sys
    from django.core.management import execute_from_command_line
    
    execute_from_command_line([sys.argv[0], 'test', 'invoice_extractor.tests_post_processing'])

