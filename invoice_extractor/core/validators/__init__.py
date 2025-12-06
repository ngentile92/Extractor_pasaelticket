# invoice_extractor/core/validators/__init__.py
"""
✅ Validators - Validación de datos extraídos

Este módulo expone los validadores disponibles.
Las importaciones se hacen bajo demanda para evitar ciclos.

Uso:
    from invoice_extractor.core.validators import MasterValidator
"""


def __getattr__(name):
    """Importación lazy para evitar ciclos."""
    if name == 'MasterValidator':
        from invoice_extractor.validators.master_validator import MasterValidator
        return MasterValidator
    elif name == 'CUITValidator':
        from invoice_extractor.validators.cuit_validator import CUITValidator
        return CUITValidator
    elif name == 'ItemsValidator':
        from invoice_extractor.validators.items_validator import ItemsValidator
        return ItemsValidator
    elif name == 'FiscalValidator':
        from invoice_extractor.validators.fiscal_validator import FiscalValidator
        return FiscalValidator
    elif name == 'FiscalValidatorAdvanced':
        from invoice_extractor.validators.fiscal_validator_advanced import FiscalValidatorAdvanced
        return FiscalValidatorAdvanced
    elif name == 'ConfidenceScorer':
        from invoice_extractor.validators.confidence_scorer import ConfidenceScorer
        return ConfidenceScorer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'MasterValidator',
    'CUITValidator',
    'ItemsValidator',
    'FiscalValidator',
    'FiscalValidatorAdvanced',
    'ConfidenceScorer',
]
