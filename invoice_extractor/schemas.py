"""
Pydantic Schemas for LlamaExtract - Argentine Invoice Data Extraction

These schemas define the structure for extracting data from Argentine invoices
including AFIP-compliant tax information, line items, and party details.

MODULAR EXTRACTION DESIGN:
This module supports modular extraction where you can select which segments to extract:
1. 'partes' - Emisor (empresa) y receptor (cliente) y sus datos
2. 'fiscalidad' - Totales e impuestos
3. 'items' - Line items / productos
4. 'totales' - Totales varios (subtotales, descuentos, total)
5. 'documento' - Datos del documento en sí (tipo, número, CAE, fechas)

You can extract ALL segments or select a subset by composing the schema dynamically.
"""

from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field, create_model
from decimal import Decimal


# ============================================================================
# ITEM SCHEMAS - Line Items / Products
# ============================================================================

class InvoiceItem(BaseModel):
    """
    Individual line item from an Argentine invoice.
    
    Represents a single product or service row in the invoice table.
    
    IMPORTANT EXTRACTION RULES:
    1. Extract EACH ROW as a SEPARATE item - do NOT duplicate or merge rows
    2. The 'codigo' is usually a SHORT alphanumeric code (e.g., '100972', '84819', '48')
    3. The 'descripcion' is the LONGER product name (e.g., 'MONSTER GREEN EAN 473X6')
    4. Extract items in the ORDER they appear in the table
    5. Verify that subtotal = cantidad × precio_unitario for each item
    """
    codigo: Optional[str] = Field(
        None,
        description="""Product code/SKU from the FIRST/LEFTMOST column of the table.
        
        CHARACTERISTICS:
        - SHORT: Usually < 10 characters
        - SIMPLE: Just numbers or simple alphanumeric (e.g., '100972', '84819', '48', '197', '2843')
        - NOT A PRICE: If it looks like a price (has comma/decimal), it's NOT a code
        - NOT A DESCRIPTION: If it's a long product name, it's NOT a code
        
        ⚠️ CRITICAL: If unsure, LEAVE THIS EMPTY (None) rather than putting wrong data here.
        Better to have empty code + correct description than wrong code."""
    )
    descripcion: str = Field(
        ...,
        description="""Product name/description from the SECOND column (after código).
        
        CHARACTERISTICS:
        - LONGER: Usually > 10 characters
        - DESCRIPTIVE TEXT: Product names like 'MONSTER GREEN EAN 473X6', 'CC ZERO 600MLX6'
        - NOT A NUMBER: If it's just a number like '6.598,35', it's probably a PRICE, not description
        - NOT A CODE: If it's very short like '100972', it's probably a CODE
        
        ⚠️ EXTRACTION ORDER (look at the physical table columns from left to right):
        Column 1 (leftmost) = codigo (short)
        Column 2 = descripcion (this field - longer text)
        Column 3 = precio_unitario (number with decimals)
        
        NEVER put prices or numbers in the description field!"""
    )
    cantidad: float = Field(
        ...,
        description="""Quantity of items ordered/sold. Must be POSITIVE (> 0).
        Can be decimal for fractional quantities (e.g., 2.5, 0.75).
        Common examples: 1, 2, 8, 6, 4
        NEVER negative - if you see a negative sign, it's likely a discount line, not quantity.""",
        gt=0
    )
    unidad_medida: Optional[str] = Field(
        None,
        description="""Unit of measure - how the quantity is counted.
        Common values: 'CJ' (caja/box), 'UN' (unidad/unit), 'KG' (kilogram), 'LT' (liter), 'M' (meter)
        Extract as shown in the invoice."""
    )
    precio_unitario: float = Field(
        ...,
        description="""Unit price per single item, BEFORE applying quantity.
        This is the price for ONE unit.
        Must be >= 0 (can be 0 for free items).
        Example: if 2 items cost $200 total, precio_unitario = $100""",
        ge=0
    )
    subtotal: float = Field(
        ...,
        description="""Line item subtotal: cantidad × precio_unitario.
        This is the TOTAL for this line item.
        Must be >= 0 and should equal cantidad × precio_unitario (verify this!).
        Examples: if cantidad=2 and precio_unitario=100, then subtotal=200""",
        ge=0
    )


# ============================================================================
# PARTY SCHEMAS - Cliente (Customer) and Empresa (Vendor)
# ============================================================================

class Cliente(BaseModel):
    """
    Customer/buyer information from an Argentine invoice.
    
    Includes tax identification (CUIT) and address details.
    """
    apellido_nombre_razon_social: str = Field(
        ...,
        description="Customer full name or business name (e.g., 'BUSAN MOTORS S.A.')"
    )
    cuit: str = Field(
        ...,
        description="Argentine tax ID (CUIT) in format XX-XXXXXXXX-X (e.g., '33-71067631-9')"
    )
    condicion_iva: str = Field(
        ...,
        description="VAT status (e.g., 'IVA RESPONSABLE INSCRIPTO', 'MONOTRIBUTO', 'EXENTO')"
    )
    domicilio: Optional[str] = Field(
        None,
        description="Full address if provided as single field"
    )
    domicilio_calle: Optional[str] = Field(
        None,
        description="Street address if provided separately"
    )
    domicilio_localidad: Optional[str] = Field(
        None,
        description="City/locality if provided separately"
    )
    provincia: Optional[str] = Field(
        None,
        description="Province/state (e.g., 'Buenos Aires', 'CABA')"
    )


class Empresa(BaseModel):
    """
    Vendor/seller/issuer information from an Argentine invoice.
    
    Includes business registration details and tax information.
    """
    razon_social: str = Field(
        ...,
        description="Business legal name (e.g., 'Axis Logística S.A.')"
    )
    cuit: str = Field(
        ...,
        description="Argentine tax ID (CUIT) in format XX-XXXXXXXX-X (e.g., '30-67776234-5')"
    )
    condicion_iva: str = Field(
        ...,
        description="VAT status (typically 'IVA RESPONSABLE INSCRIPTO' for businesses)"
    )
    ingresos_brutos: Optional[str] = Field(
        None,
        description="Gross income tax number (e.g., '901-914756-1')"
    )
    domicilio_comercial: Optional[str] = Field(
        None,
        description="Commercial address if provided as single field"
    )
    domicilio_calle: Optional[str] = Field(
        None,
        description="Street address if provided separately"
    )
    domicilio_localidad: Optional[str] = Field(
        None,
        description="City/locality if provided separately"
    )
    domicilio_codigo_postal: Optional[str] = Field(
        None,
        description="Postal code"
    )
    provincia: Optional[str] = Field(
        None,
        description="Province/state"
    )
    fecha_inicio_actividades: Optional[str] = Field(
        None,
        description="Business start date in DD/MM/YYYY format"
    )


class Partes(BaseModel):
    """
    Parties involved in the invoice transaction.
    
    Contains both customer (buyer) and empresa (vendor/seller) information.
    """
    cliente: Cliente = Field(
        ...,
        description="Customer/buyer information"
    )
    empresa: Empresa = Field(
        ...,
        description="Vendor/seller/issuer information"
    )


# ============================================================================
# DOCUMENT SCHEMAS - Invoice Document Information
# ============================================================================

class Documento(BaseModel):
    """
    Invoice document information and AFIP compliance data.
    
    Includes document type, numbering, dates, and electronic authorization (CAE).
    """
    tipo_comprobante: str = Field(
        ...,
        description="Document type (e.g., 'FACTURAS A', 'FACTURAS B', 'TIQUE FACTURA A', 'NOTA DE CREDITO')"
    )
    codigo: str = Field(
        ...,
        description="AFIP document type code (e.g., '001' for Factura A, '006' for Factura B, '081' for Ticket)"
    )
    numero_comprobante: str = Field(
        ...,
        description="Invoice number in format XXXXX-XXXXXXXX (e.g., '0029-00271813')"
    )
    punto_venta: str = Field(
        ...,
        description="Point of sale number (e.g., '0029')"
    )
    fecha_emision: str = Field(
        ...,
        description="Issue date in DD/MM/YYYY format (e.g., '22/10/2025')"
    )
    cae: Optional[str] = Field(
        None,
        description="Electronic authorization code (CAE) from AFIP (e.g., '75435949439809')"
    )
    fecha_vencimiento_cae: Optional[str] = Field(
        None,
        description="CAE expiration date in DD/MM/YYYY format"
    )
    moneda: str = Field(
        default="ARS",
        description="Currency code (typically 'ARS' for Argentine pesos)"
    )
    condicion_venta: Optional[str] = Field(
        None,
        description="Payment terms (e.g., '14 Días Fecha Factura', 'CONTADO')"
    )
    fecha_vencimiento_pago: Optional[str] = Field(
        None,
        description="Payment due date in DD/MM/YYYY format"
    )
    numero_remito: Optional[str] = Field(
        None,
        description="Delivery note number if applicable"
    )
    numero_orden_compra: Optional[str] = Field(
        None,
        description="Purchase order number if applicable"
    )
    observaciones: Optional[str] = Field(
        None,
        description="Additional notes or observations on the invoice"
    )


# ============================================================================
# FISCALIDAD SCHEMAS - Tax and Financial Calculations
# ============================================================================

class Totales(BaseModel):
    """
    Financial totals from the invoice.
    """
    subtotal_gravado: float = Field(
        ...,
        description="Taxable subtotal amount before taxes",
        ge=0
    )
    importe_total: float = Field(
        ...,
        description="Total invoice amount including all taxes",
        ge=0
    )
    descuentos: float = Field(
        default=0,
        description="Total discounts applied",
        ge=0
    )


class Calculos(BaseModel):
    """
    Calculated values for validation and reconciliation.
    
    These fields help verify arithmetic consistency in the extraction.
    """
    items_count: int = Field(
        ...,
        description="Total number of line items",
        gt=0
    )
    items_subtotal_total: float = Field(
        ...,
        description="Sum of all line item subtotals",
        ge=0
    )
    total_iva_calculado: float = Field(
        ...,
        description="Calculated total VAT amount",
        ge=0
    )
    total_percepciones_calculado: Optional[float] = Field(
        None,
        description="Calculated total perceptions",
        ge=0
    )
    total_retenciones_calculado: Optional[float] = Field(
        None,
        description="Calculated total withholdings",
        ge=0
    )
    diferencia_matematica: float = Field(
        default=0,
        description="Arithmetic difference found during validation (should be close to 0)"
    )


class PercepcionIIBB(BaseModel):
    """
    Provincial gross income tax perception.
    
    Argentina has provincial-level gross income taxes (Ingresos Brutos).
    """
    provincia: str = Field(
        ...,
        description="Province code in lowercase with underscores (e.g., 'buenos_aires', 'caba', 'cordoba')"
    )
    monto: float = Field(
        ...,
        description="Perception amount for this province",
        ge=0
    )


class Impuestos(BaseModel):
    """
    Detailed tax breakdown for Argentine invoices.
    
    Includes VAT (IVA), perceptions, withholdings, and internal taxes.
    """
    # IVA (Value Added Tax) - Simplified for LlamaExtract compatibility
    iva_21: float = Field(
        default=0,
        description="IVA 21% amount",
        ge=0
    )
    iva_105: float = Field(
        default=0,
        description="IVA 10.5% amount", 
        ge=0
    )
    iva_27: float = Field(
        default=0,
        description="IVA 27% amount",
        ge=0
    )
    iva_5: float = Field(
        default=0,
        description="IVA 5% amount",
        ge=0
    )
    iva_25: float = Field(
        default=0,
        description="IVA 2.5% amount",
        ge=0
    )
    
    # Perceptions (Percepciones)
    percepcion_iva: float = Field(
        default=0,
        description="VAT perception amount",
        ge=0
    )
    percepcion_iibb: List[PercepcionIIBB] = Field(
        default_factory=list,
        description="Provincial gross income tax perceptions"
    )
    percepcion_ganancias: float = Field(
        default=0,
        description="Income tax perception",
        ge=0
    )
    
    # Withholdings (Retenciones)
    retencion_iva: Optional[float] = Field(
        None,
        description="VAT withholding amount",
        ge=0
    )
    retenciones_iibb: List[PercepcionIIBB] = Field(
        default_factory=list,
        description="Provincial gross income tax withholdings"
    )
    retencion_ganancias: Optional[float] = Field(
        None,
        description="Income tax withholding",
        ge=0
    )
    retencion_suss: Optional[float] = Field(
        None,
        description="SUSS (health insurance) withholding",
        ge=0
    )
    
    # Other taxes
    impuestos_internos: float = Field(
        default=0,
        description="Internal taxes (e.g., fuel taxes)",
        ge=0
    )
    icl_idc: float = Field(
        default=0,
        description="ICL/IDC combustibles taxes",
        ge=0
    )
    otras_retenciones: Optional[float] = Field(
        None,
        description="Other withholdings not categorized above",
        ge=0
    )


class Fiscalidad(BaseModel):
    """
    Complete fiscal and financial information for the invoice.
    
    Combines totals, calculations, and detailed tax breakdown.
    """
    totales: Totales = Field(
        ...,
        description="Financial totals"
    )
    calculos: Calculos = Field(
        ...,
        description="Calculated values for validation"
    )
    impuestos: Impuestos = Field(
        ...,
        description="Detailed tax breakdown"
    )


# ============================================================================
# MAIN SCHEMA - Complete Argentine Invoice
# ============================================================================

class ComprobanteArgentino(BaseModel):
    """
    Complete Argentine invoice/voucher extraction schema.
    
    This is the main schema that LlamaExtract will use to extract data from
    Argentine fiscal documents (facturas, tickets, notas de crédito, etc.).
    
    It includes:
    - Line items (products/services) - EXTRACT EACH ROW SEPARATELY
    - Party information (customer and vendor)
    - Document details (numbering, dates, CAE)
    - Complete fiscal breakdown (taxes, perceptions, withholdings)
    
    ⚠️ CRITICAL FOR ITEMS EXTRACTION:
    - Extract items from the ITEMS TABLE in the invoice
    - Each ROW in the table = ONE item in the list
    - Do NOT duplicate items
    - Do NOT merge multiple rows into one item
    - Preserve the ORDER of items as they appear
    - Verify each item's math: cantidad × precio_unitario = subtotal
    """
    items: List[InvoiceItem] = Field(
        ...,
        description="""List of ALL line items (products/services) from the invoice items table.
        
        EXTRACTION RULES:
        1. Look for the ITEMS TABLE (usually has columns: CANT, CODIGO, PRODUCTO, P.UNITARIO, SUBTOTAL)
        2. Extract EACH ROW as a separate item
        3. Do NOT duplicate rows - each physical row = one item
        4. Maintain the ORDER from top to bottom
        5. Skip any TOTAL or SUBTOTAL rows (those are not items)
        
        Example table:
        | 2 CJ | 100972 | MONSTER GREEN EAN 473X6 | 8096.12 | 16192.24 |  ← Extract as ONE item
        | 8 CJ | 84819  | SW591X6 S/G (6P)        | 3747.15 | 29977.20 |  ← Extract as ANOTHER item
        """,
        min_items=1
    )
    partes: Partes = Field(
        ...,
        description="Parties involved: customer (buyer) and empresa (seller/vendor)"
    )
    documento: Documento = Field(
        ...,
        description="Document information including type, numbering, dates, and CAE"
    )
    fiscalidad: Fiscalidad = Field(
        ...,
        description="Complete fiscal information: totals, calculations, and tax breakdown"
    )


# ============================================================================
# ALTERNATE SCHEMAS - For different complexity levels
# ============================================================================

class ComprobanteSimplificado(BaseModel):
    """
    Simplified schema for basic invoice extraction.
    
    Use this for simpler documents or when you need faster processing
    with less detail.
    """
    items: List[InvoiceItem] = Field(
        ...,
        description="List of line items",
        min_items=1
    )
    
    # Simplified party info
    cliente_nombre: str = Field(..., description="Customer name")
    cliente_cuit: str = Field(..., description="Customer CUIT")
    empresa_nombre: str = Field(..., description="Vendor name")
    empresa_cuit: str = Field(..., description="Vendor CUIT")
    
    # Simplified document info
    tipo_comprobante: str = Field(..., description="Document type")
    numero_comprobante: str = Field(..., description="Invoice number")
    fecha_emision: str = Field(..., description="Issue date DD/MM/YYYY")
    
    # Simplified fiscal info
    subtotal: float = Field(..., description="Subtotal before taxes")
    total_iva: float = Field(..., description="Total VAT amount")
    importe_total: float = Field(..., description="Total amount")


# ============================================================================
# MODULAR SCHEMA COMPOSER - Dynamic Schema Generation
# ============================================================================

class SchemaComposer:
    """
    Composes dynamic Pydantic schemas based on selected segments.
    
    This allows for flexible extraction where you can choose which parts
    of the invoice to extract (partes, fiscalidad, items, totales, documento).
    
    Usage:
        # Extract only items and documento
        composer = SchemaComposer(segments=['items', 'documento'])
        schema = composer.get_schema()
        
        # Extract everything
        composer = SchemaComposer(segments='all')
        schema = composer.get_schema()
        
        # Extract partes and fiscalidad only
        composer = SchemaComposer(segments=['partes', 'fiscalidad'])
        schema = composer.get_schema()
    """
    
    AVAILABLE_SEGMENTS = {
        'items', 'partes', 'fiscalidad', 'totales', 'documento'
    }
    
    def __init__(self, segments: Optional[List[str]] = None):
        """
        Initialize the schema composer.
        
        Args:
            segments: List of segment names to include, or 'all' for everything.
                     Available: ['items', 'partes', 'fiscalidad', 'totales', 'documento']
                     If None or 'all', includes all segments.
        """
        if segments is None or segments == 'all' or (isinstance(segments, list) and 'all' in segments):
            self.segments = self.AVAILABLE_SEGMENTS.copy()
        else:
            # Validate segments
            invalid_segments = set(segments) - self.AVAILABLE_SEGMENTS
            if invalid_segments:
                raise ValueError(
                    f"Invalid segments: {invalid_segments}. "
                    f"Available segments: {self.AVAILABLE_SEGMENTS}"
                )
            self.segments = set(segments)
    
    def get_schema(self) -> type[BaseModel]:
        """
        Generate a dynamic Pydantic schema based on selected segments.
        
        Returns:
            A Pydantic model class with only the selected fields.
        """
        fields = {}
        
        # Build fields dictionary based on selected segments
        if 'items' in self.segments:
            fields['items'] = (
                List[InvoiceItem],
                Field(
                    ...,
                    description="List of line items (products/services) on the invoice",
                    min_items=1
                )
            )
        
        if 'partes' in self.segments:
            fields['partes'] = (
                Partes,
                Field(
                    ...,
                    description="Parties involved: customer (buyer) and empresa (seller/vendor)"
                )
            )
        
        if 'documento' in self.segments:
            fields['documento'] = (
                Documento,
                Field(
                    ...,
                    description="Document information including type, numbering, dates, and CAE"
                )
            )
        
        if 'fiscalidad' in self.segments:
            fields['fiscalidad'] = (
                Fiscalidad,
                Field(
                    ...,
                    description="Complete fiscal information: totals, calculations, and tax breakdown"
                )
            )
        
        if 'totales' in self.segments:
            # If 'totales' is requested separately (not as part of fiscalidad)
            # and fiscalidad is not included, add totales directly
            if 'fiscalidad' not in self.segments:
                fields['totales'] = (
                    Totales,
                    Field(
                        ...,
                        description="Financial totals (subtotal, total, descuentos)"
                    )
                )
        
        # Create dynamic model
        model_name = f"ComprobanteArgentino_{'_'.join(sorted(self.segments))}"
        
        dynamic_model = create_model(
            model_name,
            **fields,
            __doc__=f"Dynamic Argentine invoice schema with segments: {', '.join(sorted(self.segments))}"
        )
        
        return dynamic_model
    
    def get_segment_list(self) -> List[str]:
        """Return the list of segments included in this composer."""
        return sorted(list(self.segments))
    
    @classmethod
    def get_available_segments(cls) -> Set[str]:
        """Return all available segment names."""
        return cls.AVAILABLE_SEGMENTS.copy()


# ============================================================================
# EXPORT - Schemas to use with LlamaExtract
# ============================================================================

# Use ComprobanteArgentino for full extraction (recommended)
# Use ComprobanteSimplificado for faster, simpler extraction
# Use SchemaComposer for modular extraction

__all__ = [
    'ComprobanteArgentino',
    'ComprobanteSimplificado',
    'SchemaComposer',
    'InvoiceItem',
    'Partes',
    'Cliente',
    'Empresa',
    'Documento',
    'Fiscalidad',
    'Totales',
    'Calculos',
    'Impuestos',
    'PercepcionIIBB',
]

