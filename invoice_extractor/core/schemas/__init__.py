# invoice_extractor/core/schemas/__init__.py
"""
📋 Schemas - Definiciones de datos para facturas argentinas

Schemas únicos y consolidados para toda la aplicación.

Uso:
    from invoice_extractor.core.schemas import (
        InvoiceItem,
        InvoicePartes,
        InvoiceDocumento,
        InvoiceFiscalidad,
        InvoiceComplete,
        SchemaComposer,
    )
"""

from .invoice import (
    # Items
    InvoiceItem,
    
    # Partes (Cliente y Empresa)
    Cliente,
    Empresa,
    InvoicePartes,
    
    # Documento
    InvoiceDocumento,
    
    # Fiscalidad
    InvoiceTotales,
    InvoiceCalculos,
    PercepcionIIBB,
    InvoiceImpuestos,
    InvoiceFiscalidad,
    
    # Schema completo
    InvoiceComplete,
    InvoiceSimplificado,
    
    # Composer para extracción modular
    SchemaComposer,
)

__all__ = [
    'InvoiceItem',
    'Cliente',
    'Empresa',
    'InvoicePartes',
    'InvoiceDocumento',
    'InvoiceTotales',
    'InvoiceCalculos',
    'PercepcionIIBB',
    'InvoiceImpuestos',
    'InvoiceFiscalidad',
    'InvoiceComplete',
    'InvoiceSimplificado',
    'SchemaComposer',
]
