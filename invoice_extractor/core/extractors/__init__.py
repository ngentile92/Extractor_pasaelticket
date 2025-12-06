# invoice_extractor/core/extractors/__init__.py
"""
🤖 Extractors - Servicios de extracción de datos

Este módulo expone el extractor principal (Gemini).

Uso:
    from invoice_extractor.core.extractors import GeminiExtractor
    
    # O importar directamente
    from invoice_extractor.services_gemini_extractor import GeminiExtractor
"""


def __getattr__(name):
    """Importación lazy para evitar ciclos."""
    if name == 'GeminiExtractor':
        from invoice_extractor.services_gemini_extractor import GeminiExtractor
        return GeminiExtractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'GeminiExtractor',
]
