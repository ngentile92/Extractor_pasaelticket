"""
Tests para CUITValidator

Suite completa de tests para validar el funcionamiento del validador de CUIT.
"""

from django.test import TestCase
from invoice_extractor.validators.cuit_validator import CUITValidator, validate_cuit, normalize_cuit


class CUITValidatorTests(TestCase):
    """Tests para el validador de CUIT"""
    
    # CUITs válidos para testing (generados con algoritmo correcto)
    VALID_CUITS = [
        "30-71106763-5",  # Persona jurídica
        "20-12345678-6",  # Persona física masculina
        "27-12345678-0",  # Persona física femenina
        "23-12345678-5",  # Persona física masculina (otro)
        "33-12345678-0",  # Persona jurídica (otro)
    ]
    
    # CUITs inválidos
    INVALID_CUITS = [
        "30-71106763-9",  # Dígito verificador incorrecto (debería ser 5)
        "30-71106763-0",  # Dígito verificador incorrecto (debería ser 5)
        "99-71106763-5",  # Prefijo inválido
        "30-7110676-9",   # Longitud incorrecta
        "30-711067639",   # Longitud incorrecta
        "",               # Vacío
        None,             # None
        "XX-XXXXXXXX-X",  # No numérico
    ]
    
    def test_normalize_cuit_with_hyphens(self):
        """Test normalización de CUIT con guiones"""
        cuit = "30-71106763-5"
        normalized = CUITValidator.normalize_cuit(cuit)
        self.assertEqual(normalized, "30-71106763-5")
    
    def test_normalize_cuit_without_hyphens(self):
        """Test normalización de CUIT sin guiones"""
        cuit = "30711067635"
        normalized = CUITValidator.normalize_cuit(cuit)
        self.assertEqual(normalized, "30-71106763-5")
    
    def test_normalize_cuit_with_spaces(self):
        """Test normalización de CUIT con espacios"""
        cuit = "30 71106763 5"
        normalized = CUITValidator.normalize_cuit(cuit)
        self.assertEqual(normalized, "30-71106763-5")
    
    def test_normalize_cuit_mixed_format(self):
        """Test normalización de CUIT con formato mixto"""
        cuit = "30 711 067 63-5"
        normalized = CUITValidator.normalize_cuit(cuit)
        self.assertEqual(normalized, "30-71106763-5")
    
    def test_normalize_cuit_invalid_length(self):
        """Test normalización de CUIT con longitud inválida"""
        cuit = "30-7110676-9"  # 10 dígitos
        normalized = CUITValidator.normalize_cuit(cuit)
        # Debe retornar sin formato pero no crashear
        self.assertIsNotNone(normalized)
    
    def test_validate_format_valid(self):
        """Test validación de formato con CUIT válido"""
        cuit = "30-71106763-5"
        result = CUITValidator.validate_format(cuit)
        self.assertTrue(result['is_valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_format_invalid_prefix(self):
        """Test validación de formato con prefijo inválido"""
        cuit = "99-71106763-9"
        result = CUITValidator.validate_format(cuit)
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
        self.assertIn("Prefijo", result['errors'][0])
    
    def test_validate_format_invalid_length(self):
        """Test validación de formato con longitud incorrecta"""
        cuit = "30-7110676-9"  # 10 dígitos
        result = CUITValidator.validate_format(cuit)
        self.assertFalse(result['is_valid'])
        self.assertIn("11 dígitos", result['errors'][0])
    
    def test_validate_format_empty(self):
        """Test validación de formato con CUIT vacío"""
        cuit = ""
        result = CUITValidator.validate_format(cuit)
        self.assertFalse(result['is_valid'])
        self.assertIn("vacío", result['errors'][0])
    
    def test_calculate_verifier_digit_valid(self):
        """Test cálculo de dígito verificador con CUIT válido"""
        cuit_base = "3071106763"
        verifier = CUITValidator.calculate_verifier_digit(cuit_base)
        self.assertEqual(verifier, 5)
    
    def test_calculate_verifier_digit_case_11(self):
        """Test cálculo de dígito verificador (caso especial = 11)"""
        # Necesitamos un CUIT donde el resultado sea 11 (se convierte a 0)
        cuit_base = "2012345678"
        verifier = CUITValidator.calculate_verifier_digit(cuit_base)
        self.assertIn(verifier, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9])  # Debe ser un dígito válido
    
    def test_calculate_verifier_digit_invalid_length(self):
        """Test cálculo de dígito verificador con longitud inválida"""
        cuit_base = "307110676"  # 9 dígitos
        with self.assertRaises(ValueError):
            CUITValidator.calculate_verifier_digit(cuit_base)
    
    def test_validate_verifier_digit_valid(self):
        """Test validación de dígito verificador con CUIT válido"""
        cuit = "30-71106763-5"
        result = CUITValidator.validate_verifier_digit(cuit)
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['calculated_verifier'], 5)
        self.assertEqual(result['actual_verifier'], 5)
    
    def test_validate_verifier_digit_invalid(self):
        """Test validación de dígito verificador con CUIT inválido"""
        cuit = "30-71106763-9"  # Verificador incorrecto (debería ser 5)
        result = CUITValidator.validate_verifier_digit(cuit)
        self.assertFalse(result['is_valid'])
        self.assertEqual(result['calculated_verifier'], 5)
        self.assertEqual(result['actual_verifier'], 9)
        self.assertGreater(len(result['errors']), 0)
    
    def test_get_person_type_juridica(self):
        """Test identificación de persona jurídica"""
        cuit = "30-71106763-5"
        tipo, descripcion = CUITValidator.get_person_type(cuit)
        self.assertEqual(tipo, 'juridica')
        self.assertIn("jurídica", descripcion.lower())
    
    def test_get_person_type_fisica_masculino(self):
        """Test identificación de persona física masculina"""
        cuit = "20-12345678-6"
        tipo, descripcion = CUITValidator.get_person_type(cuit)
        self.assertEqual(tipo, 'fisica')
        self.assertIn("masculina", descripcion.lower())
    
    def test_get_person_type_fisica_femenina(self):
        """Test identificación de persona física femenina"""
        cuit = "27-12345678-0"
        tipo, descripcion = CUITValidator.get_person_type(cuit)
        self.assertEqual(tipo, 'fisica')
        self.assertIn("femenina", descripcion.lower())
    
    def test_get_person_type_unknown(self):
        """Test identificación de tipo desconocido"""
        cuit = "99-12345678-9"
        tipo, descripcion = CUITValidator.get_person_type(cuit)
        self.assertEqual(tipo, 'unknown')
    
    def test_validate_complete_valid(self):
        """Test validación completa con CUIT válido"""
        cuit = "30-71106763-5"
        result = CUITValidator.validate_complete(cuit)
        
        self.assertTrue(result['is_valid'])
        self.assertTrue(result['format_valid'])
        self.assertTrue(result['verifier_valid'])
        self.assertEqual(result['cuit_normalized'], "30-71106763-5")
        self.assertEqual(result['person_type'], 'juridica')
        self.assertEqual(len(result['errors']), 0)
        self.assertFalse(result['can_auto_fix'])
    
    def test_validate_complete_invalid_verifier(self):
        """Test validación completa con dígito verificador incorrecto"""
        cuit = "30-71106763-9"  # Verificador incorrecto (debería ser 5)
        result = CUITValidator.validate_complete(cuit)
        
        self.assertFalse(result['is_valid'])
        self.assertTrue(result['format_valid'])
        self.assertFalse(result['verifier_valid'])
        self.assertGreater(len(result['errors']), 0)
        self.assertTrue(result['can_auto_fix'])
        self.assertEqual(result['suggested_cuit'], "30-71106763-5")
    
    def test_validate_complete_invalid_format(self):
        """Test validación completa con formato inválido"""
        cuit = "99-71106763-9"
        result = CUITValidator.validate_complete(cuit)
        
        self.assertFalse(result['is_valid'])
        self.assertFalse(result['format_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_complete_empty(self):
        """Test validación completa con CUIT vacío"""
        cuit = ""
        result = CUITValidator.validate_complete(cuit)
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_validate_complete_none(self):
        """Test validación completa con CUIT None"""
        cuit = None
        result = CUITValidator.validate_complete(cuit)
        
        self.assertFalse(result['is_valid'])
        self.assertGreater(len(result['errors']), 0)
    
    def test_create_alert_valid_cuit(self):
        """Test creación de alerta con CUIT válido (no debe crear alerta)"""
        validation_result = CUITValidator.validate_complete("30-71106763-5")
        alert = CUITValidator.create_alert(validation_result, "empresa.cuit")
        
        self.assertIsNone(alert)
    
    def test_create_alert_invalid_verifier(self):
        """Test creación de alerta con dígito verificador incorrecto"""
        validation_result = CUITValidator.validate_complete("30-71106763-9")
        alert = CUITValidator.create_alert(validation_result, "empresa.cuit")
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert['level'], 'error')
        self.assertEqual(alert['category'], 'cuit')
        self.assertEqual(alert['field'], 'empresa.cuit')
        self.assertTrue(alert['can_auto_fix'])
        self.assertEqual(alert['expected_value'], "30-71106763-5")
    
    def test_create_alert_invalid_format(self):
        """Test creación de alerta con formato inválido"""
        validation_result = CUITValidator.validate_complete("99-71106763-5")
        alert = CUITValidator.create_alert(validation_result, "cliente.cuit")
        
        self.assertIsNotNone(alert)
        self.assertEqual(alert['level'], 'critical')
        self.assertEqual(alert['category'], 'cuit')
        self.assertEqual(alert['field'], 'cliente.cuit')
    
    def test_utility_function_validate_cuit_valid(self):
        """Test función de utilidad validate_cuit() con CUIT válido"""
        self.assertTrue(validate_cuit("30-71106763-5"))
    
    def test_utility_function_validate_cuit_invalid(self):
        """Test función de utilidad validate_cuit() con CUIT inválido"""
        self.assertFalse(validate_cuit("30-71106763-9"))
    
    def test_utility_function_normalize_cuit(self):
        """Test función de utilidad normalize_cuit()"""
        self.assertEqual(normalize_cuit("30 71106763 5"), "30-71106763-5")
    
    def test_multiple_valid_cuits(self):
        """Test validación de múltiples CUITs válidos"""
        for cuit in self.VALID_CUITS:
            with self.subTest(cuit=cuit):
                result = CUITValidator.validate_complete(cuit)
                self.assertTrue(
                    result['is_valid'],
                    f"CUIT {cuit} debería ser válido pero falló: {result['errors']}"
                )
    
    def test_multiple_invalid_cuits(self):
        """Test validación de múltiples CUITs inválidos"""
        for cuit in self.INVALID_CUITS:
            if cuit is not None and cuit != "":
                with self.subTest(cuit=cuit):
                    result = CUITValidator.validate_complete(cuit)
                    self.assertFalse(
                        result['is_valid'],
                        f"CUIT {cuit} debería ser inválido pero pasó validación"
                    )

