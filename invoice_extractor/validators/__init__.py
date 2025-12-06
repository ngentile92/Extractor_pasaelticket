# invoice_extractor/validators/__init__.py
"""
✅ Validadores para facturas argentinas

Este paquete contiene todos los validadores necesarios:
- MasterValidator: Orquestador principal
- CUITValidator: Validación de CUITs
- ItemsValidator: Validación de items
- FiscalValidator: Validación fiscal básica
- FiscalValidatorAdvanced: Validación fiscal avanzada
- ConfidenceScorer: Cálculo de score de confianza

Uso simple (recomendado):
    from invoice_extractor.validators import MasterValidator
    
    validator = MasterValidator()
    result = validator.validate_complete(extracted_data)
    
    print(f"Score: {result['confidence_score']}")
    print(f"Errores: {result['validation_errors']}")

Uso avanzado (validadores específicos):
    from invoice_extractor.validators import CUITValidator, ItemsValidator
    
    cuit_validator = CUITValidator()
    is_valid = cuit_validator.validate("20-12345678-9")
"""

from .master_validator import MasterValidator
from .cuit_validator import CUITValidator
from .items_validator import ItemsValidator
from .fiscal_validator import FiscalValidator
from .fiscal_validator_advanced import FiscalValidatorAdvanced
from .confidence_scorer import ConfidenceScorer

__all__ = [
    'MasterValidator',
    'CUITValidator',
    'ItemsValidator',
    'FiscalValidator',
    'FiscalValidatorAdvanced',
    'ConfidenceScorer',
]


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def validate_invoice(extracted_data: dict) -> dict:
    """
    Función de conveniencia para validar una factura extraída.
    
    Usa MasterValidator internamente.
    
    Args:
        extracted_data: Datos extraídos de la factura
    
    Returns:
        dict con:
        - confidence_score: Float 0-1
        - is_valid: Boolean
        - validation_errors: Lista de errores
        - alerts: Lista de alertas
    """
    validator = MasterValidator()
    return validator.validate_complete(extracted_data)


def get_confidence_score(extracted_data: dict) -> float:
    """
    Obtener solo el score de confianza de los datos extraídos.
    
    Args:
        extracted_data: Datos extraídos de la factura
    
    Returns:
        Score de confianza (0.0 a 1.0)
    """
    result = validate_invoice(extracted_data)
    return result.get('confidence_score', 0.0)


def is_valid_cuit(cuit: str) -> bool:
    """
    Verificar si un CUIT es válido.
    
    Args:
        cuit: CUIT a validar (con o sin guiones)
    
    Returns:
        True si el CUIT es válido
    """
    validator = CUITValidator()
    result = validator.validate_complete(cuit)
    return result.get('is_valid', False)
