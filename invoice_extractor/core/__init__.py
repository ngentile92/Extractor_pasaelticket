# invoice_extractor/core/__init__.py
"""
🎯 Core - Módulos centrales del extractor de facturas

Este paquete contiene los componentes principales:
- schemas: Definiciones de datos (Pydantic)
- extractors: Extractores de datos (Gemini, LlamaExtract)
- processors: Procesamiento de datos (normalización, corrección)
- validators: Validación de datos extraídos

NOTA: Las importaciones se hacen lazy para evitar ciclos de importación.

Uso:
    from invoice_extractor.core.schemas import InvoiceSchema
    from invoice_extractor.core.extractors import GeminiExtractor
    from invoice_extractor.core.validators import MasterValidator
"""

# Solo importar schemas directamente (no tiene dependencias circulares)
from . import schemas

# Los demás módulos se importan bajo demanda para evitar ciclos
# Usar: from invoice_extractor.core.extractors import GeminiExtractor
# En lugar de: from invoice_extractor.core import extractors

__all__ = ['schemas']
