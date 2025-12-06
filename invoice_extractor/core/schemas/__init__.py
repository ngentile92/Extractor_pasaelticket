# invoice_extractor/core/schemas/__init__.py
"""
📋 Schemas - Definiciones de datos para facturas argentinas

Schemas únicos y consolidados para toda la aplicación.
Evita duplicación de definiciones en diferentes módulos.

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

# Re-exportar con nombres alternativos para compatibilidad
ComprobanteArgentino = InvoiceComplete
ComprobanteSimplificado = InvoiceSimplificado
Partes = InvoicePartes
Documento = InvoiceDocumento
Fiscalidad = InvoiceFiscalidad
Totales = InvoiceTotales
Calculos = InvoiceCalculos
Impuestos = InvoiceImpuestos

__all__ = [
    # Nombres nuevos (preferidos)
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
    
    # Nombres legacy (para compatibilidad)
    'ComprobanteArgentino',
    'ComprobanteSimplificado',
    'Partes',
    'Documento',
    'Fiscalidad',
    'Totales',
    'Calculos',
    'Impuestos',
]

