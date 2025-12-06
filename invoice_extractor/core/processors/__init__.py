# invoice_extractor/core/processors/__init__.py
"""
🔧 Processors - Pipeline de procesamiento de datos

Este módulo expone los procesadores disponibles.
Las importaciones se hacen bajo demanda para evitar ciclos.

Uso:
    from invoice_extractor.core.processors import InvoicePostProcessor
"""


def __getattr__(name):
    """Importación lazy para evitar ciclos."""
    if name == 'InvoicePostProcessor':
        from invoice_extractor.utils.post_processor import InvoicePostProcessor
        return InvoicePostProcessor
    elif name == 'process_invoice':
        from invoice_extractor.utils.post_processor import process_invoice
        return process_invoice
    elif name == 'transform_to_legacy_format':
        from invoice_extractor.utils.post_processor import transform_to_legacy_format
        return transform_to_legacy_format
    elif name == 'BatchPostProcessor':
        from invoice_extractor.utils.post_processor import BatchPostProcessor
        return BatchPostProcessor
    elif name == 'normalize_all':
        from invoice_extractor.utils.normalization import normalize_all
        return normalize_all
    elif name == 'apply_all_corrections':
        from invoice_extractor.utils.corrections import apply_all_corrections
        return apply_all_corrections
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    'InvoicePostProcessor',
    'process_invoice',
    'transform_to_legacy_format',
    'BatchPostProcessor',
    'normalize_all',
    'apply_all_corrections',
]
