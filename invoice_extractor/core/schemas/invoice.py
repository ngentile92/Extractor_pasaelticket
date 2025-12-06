"""
📋 Invoice Schema - Definición única de datos para facturas argentinas

Este módulo contiene TODAS las definiciones de schemas Pydantic para facturas.
Es el ÚNICO lugar donde se definen estos schemas para evitar duplicación.

Schemas disponibles:
- InvoiceItem: Producto/servicio individual
- InvoicePartes: Empresa y Cliente
- InvoiceDocumento: Datos del documento
- InvoiceFiscalidad: Totales e impuestos
- InvoiceComplete: Schema completo (todos los campos)
- InvoiceSimplificado: Schema básico
- SchemaComposer: Generador de schemas modulares
"""

from typing import Optional, List, Dict, Set
from pydantic import BaseModel, Field, create_model


# =============================================================================
# ITEM SCHEMA - Producto/Servicio
# =============================================================================

class InvoiceItem(BaseModel):
    """
    Producto o servicio individual de una factura.
    
    Representa una fila de la tabla de items.
    
    Validaciones:
    - cantidad debe ser > 0
    - precio_unitario debe ser >= 0
    - subtotal debe ser >= 0 y = cantidad × precio_unitario
    
    Campos opcionales para facturas con impuestos por línea:
    - descuento_item: Descuento aplicado a este item
    - iva_item: IVA calculado para este item
    - iva_tasa: Tasa de IVA aplicada (21, 10.5, 27, etc.)
    - impuestos_internos_item: Impuestos internos para este item
    - subtotal_con_impuestos: Subtotal final con todos los impuestos
    """
    codigo: Optional[str] = Field(
        None,
        description="Código del producto (corto, alfanumérico)",
        max_length=50
    )
    descripcion: str = Field(
        ...,
        description="Descripción del producto/servicio",
        max_length=500
    )
    cantidad: float = Field(
        ...,
        description="Cantidad (debe ser > 0)",
        gt=0
    )
    unidad_medida: Optional[str] = Field(
        None,
        description="Unidad de medida: UN, CJ, KG, LT, M, etc.",
        max_length=20
    )
    precio_unitario: float = Field(
        ...,
        description="Precio por unidad (debe ser >= 0)",
        ge=0
    )
    subtotal: float = Field(
        ...,
        description="Subtotal del item = cantidad × precio_unitario (antes de impuestos)",
        ge=0
    )
    
    # 🆕 Campos opcionales para facturas con impuestos por línea
    descuento_item: Optional[float] = Field(
        None,
        description="Descuento aplicado a este item específico",
        ge=0
    )
    subtotal_neto: Optional[float] = Field(
        None,
        description="Subtotal después de descuento (subtotal - descuento_item)",
        ge=0
    )
    iva_tasa: Optional[float] = Field(
        None,
        description="Tasa de IVA aplicada: 21, 10.5, 27, 5, 2.5, 0"
    )
    iva_item: Optional[float] = Field(
        None,
        description="Monto de IVA calculado para este item",
        ge=0
    )
    impuestos_internos_item: Optional[float] = Field(
        None,
        description="Impuestos internos para este item",
        ge=0
    )
    otros_impuestos_item: Optional[float] = Field(
        None,
        description="Otros impuestos aplicados a este item",
        ge=0
    )
    subtotal_con_impuestos: Optional[float] = Field(
        None,
        description="Subtotal final del item con todos los impuestos incluidos",
        ge=0
    )


# =============================================================================
# PARTES SCHEMAS - Empresa y Cliente
# =============================================================================

class Cliente(BaseModel):
    """Cliente/receptor de la factura."""
    apellido_nombre_razon_social: str = Field(
        ...,
        description="Nombre completo o razón social del cliente"
    )
    cuit: Optional[str] = Field(
        None,
        description="CUIT en formato XX-XXXXXXXX-X (11 dígitos)"
    )
    condicion_iva: Optional[str] = Field(
        None,
        description="Condición IVA: RESPONSABLE INSCRIPTO, MONOTRIBUTO, EXENTO, CONSUMIDOR FINAL"
    )
    domicilio: Optional[str] = Field(None, description="Dirección completa")
    domicilio_calle: Optional[str] = Field(None, description="Calle y número")
    domicilio_localidad: Optional[str] = Field(None, description="Ciudad/Localidad")
    provincia: Optional[str] = Field(None, description="Provincia")


class Empresa(BaseModel):
    """Empresa/emisor de la factura."""
    razon_social: str = Field(
        ...,
        description="Razón social de la empresa"
    )
    cuit: str = Field(
        ...,
        description="CUIT en formato XX-XXXXXXXX-X (11 dígitos)"
    )
    condicion_iva: str = Field(
        ...,
        description="Condición IVA: RESPONSABLE INSCRIPTO, MONOTRIBUTO, EXENTO"
    )
    ingresos_brutos: Optional[str] = Field(
        None,
        description="Número de Ingresos Brutos"
    )
    domicilio_comercial: Optional[str] = Field(None, description="Dirección comercial")
    domicilio_calle: Optional[str] = Field(None, description="Calle y número")
    domicilio_localidad: Optional[str] = Field(None, description="Ciudad/Localidad")
    domicilio_codigo_postal: Optional[str] = Field(None, description="Código postal")
    provincia: Optional[str] = Field(None, description="Provincia")
    fecha_inicio_actividades: Optional[str] = Field(
        None,
        description="Fecha inicio actividades DD/MM/YYYY"
    )


class InvoicePartes(BaseModel):
    """Partes involucradas en la factura."""
    cliente: Cliente = Field(..., description="Cliente/receptor")
    empresa: Empresa = Field(..., description="Empresa/emisor")


# =============================================================================
# DOCUMENTO SCHEMA
# =============================================================================

class InvoiceDocumento(BaseModel):
    """Datos del documento fiscal."""
    tipo_comprobante: str = Field(
        ...,
        description="Tipo: FACTURA A, FACTURA B, FACTURA C, NOTA DE CREDITO, etc."
    )
    codigo: str = Field(
        ...,
        description="Código AFIP (001=Factura A, 006=Factura B, 011=Factura C)"
    )
    numero_comprobante: str = Field(
        ...,
        description="Número de comprobante completo"
    )
    punto_venta: str = Field(
        ...,
        description="Punto de venta (4-5 dígitos)"
    )
    fecha_emision: str = Field(
        ...,
        description="Fecha de emisión DD/MM/YYYY"
    )
    cae: Optional[str] = Field(
        None,
        description="CAE (Código Autorización Electrónica, 14 dígitos)"
    )
    fecha_vencimiento_cae: Optional[str] = Field(
        None,
        description="Fecha vencimiento CAE DD/MM/YYYY"
    )
    moneda: str = Field(
        default="ARS",
        description="Moneda (ARS, USD, EUR)"
    )
    condicion_venta: Optional[str] = Field(
        None,
        description="Condición de venta: CONTADO, CUENTA CORRIENTE, etc."
    )
    fecha_vencimiento_pago: Optional[str] = Field(
        None,
        description="Fecha vencimiento pago DD/MM/YYYY"
    )
    numero_remito: Optional[str] = Field(None, description="Número de remito")
    numero_orden_compra: Optional[str] = Field(None, description="Número de orden de compra")
    observaciones: Optional[str] = Field(None, description="Observaciones")


# =============================================================================
# FISCALIDAD SCHEMAS - Totales e Impuestos
# =============================================================================

class InvoiceTotales(BaseModel):
    """
    Totales de la factura.
    
    Soporta dos estructuras:
    1. Simple: subtotal_gravado + impuestos = importe_total
    2. Detallada: subtotal_bruto - descuentos = subtotal_neto + impuestos = importe_total
    """
    # Campos principales (siempre presentes)
    subtotal_gravado: float = Field(
        ...,
        description="Subtotal neto gravado (después de descuentos, antes de impuestos)",
        ge=0
    )
    importe_total: float = Field(
        ...,
        description="Total final a pagar",
        ge=0
    )
    
    # 🆕 Campos para estructura detallada (opcionales)
    subtotal_bruto: Optional[float] = Field(
        None,
        description="Suma de precios netos de items (antes de descuentos)",
        ge=0
    )
    descuentos: float = Field(
        default=0,
        description="Total de descuentos aplicados",
        ge=0
    )
    subtotal_exento: Optional[float] = Field(
        None,
        description="Subtotal de items exentos de IVA",
        ge=0
    )
    subtotal_no_gravado: Optional[float] = Field(
        None,
        description="Subtotal de items no gravados",
        ge=0
    )
    subtotal_con_iva: Optional[float] = Field(
        None,
        description="Subtotal con IVA pero sin otros impuestos",
        ge=0
    )
    
    # 🆕 Totales de impuestos globales (para validar vs suma de items)
    total_iva: Optional[float] = Field(
        None,
        description="Total de IVA (suma de todos los items o global declarado)",
        ge=0
    )
    total_impuestos_internos: Optional[float] = Field(
        None,
        description="Total de impuestos internos",
        ge=0
    )
    total_otros_tributos: Optional[float] = Field(
        None,
        description="Total de otros tributos (percepciones, etc.)",
        ge=0
    )


class InvoiceCalculos(BaseModel):
    """Cálculos de validación."""
    items_count: int = Field(
        ...,
        description="Cantidad de items",
        gt=0
    )
    items_subtotal_total: float = Field(
        ...,
        description="Suma de subtotales de items",
        ge=0
    )
    total_iva_calculado: float = Field(
        ...,
        description="Total IVA calculado",
        ge=0
    )
    total_percepciones_calculado: Optional[float] = Field(
        None,
        description="Total percepciones calculado",
        ge=0
    )
    total_retenciones_calculado: Optional[float] = Field(
        None,
        description="Total retenciones calculado",
        ge=0
    )
    diferencia_matematica: float = Field(
        default=0,
        description="Diferencia matemática encontrada"
    )


class PercepcionIIBB(BaseModel):
    """Percepción de Ingresos Brutos por provincia."""
    provincia: str = Field(..., description="Provincia (ej: buenos_aires, caba)")
    monto: float = Field(..., description="Monto de la percepción", ge=0)


class InvoiceImpuestos(BaseModel):
    """Desglose de impuestos."""
    # IVA - Diccionario con tasas como claves
    iva: Dict[str, float] = Field(
        default_factory=dict,
        description="IVA por tasa: {'21': monto, '105': monto, '27': monto}"
    )
    
    # Percepciones
    percepcion_iva: float = Field(default=0, description="Percepción IVA", ge=0)
    percepcion_iibb: List[PercepcionIIBB] = Field(
        default_factory=list,
        description="Percepciones IIBB por provincia"
    )
    percepcion_ganancias: float = Field(default=0, description="Percepción Ganancias", ge=0)
    
    # Retenciones
    retencion_iva: Optional[float] = Field(None, description="Retención IVA", ge=0)
    retenciones_iibb: List[PercepcionIIBB] = Field(
        default_factory=list,
        description="Retenciones IIBB por provincia"
    )
    retencion_ganancias: Optional[float] = Field(None, description="Retención Ganancias", ge=0)
    retencion_suss: Optional[float] = Field(None, description="Retención SUSS", ge=0)
    
    # Otros impuestos
    impuestos_internos: float = Field(default=0, description="Impuestos internos", ge=0)
    icl_idc: float = Field(default=0, description="ICL/IDC combustibles", ge=0)
    otras_retenciones: Optional[float] = Field(None, description="Otras retenciones", ge=0)


class InvoiceFiscalidad(BaseModel):
    """Información fiscal completa."""
    totales: InvoiceTotales = Field(..., description="Totales")
    calculos: InvoiceCalculos = Field(..., description="Cálculos de validación")
    impuestos: InvoiceImpuestos = Field(..., description="Desglose de impuestos")


# =============================================================================
# SCHEMAS COMPLETOS
# =============================================================================

class InvoiceComplete(BaseModel):
    """
    Schema completo para factura argentina.
    
    Incluye todos los campos necesarios para una extracción completa:
    - items: Lista de productos/servicios
    - partes: Empresa y Cliente
    - documento: Datos del documento
    - fiscalidad: Totales e impuestos
    """
    items: List[InvoiceItem] = Field(
        ...,
        description="Lista de items/productos",
        min_length=1
    )
    partes: InvoicePartes = Field(..., description="Empresa y Cliente")
    documento: InvoiceDocumento = Field(..., description="Datos del documento")
    fiscalidad: InvoiceFiscalidad = Field(..., description="Totales e impuestos")


class InvoiceSimplificado(BaseModel):
    """Schema simplificado para extracción básica."""
    items: List[InvoiceItem] = Field(..., description="Lista de items", min_length=1)
    
    # Partes simplificado
    cliente_nombre: str = Field(..., description="Nombre del cliente")
    cliente_cuit: Optional[str] = Field(None, description="CUIT del cliente")
    empresa_nombre: str = Field(..., description="Nombre de la empresa")
    empresa_cuit: str = Field(..., description="CUIT de la empresa")
    
    # Documento simplificado
    tipo_comprobante: str = Field(..., description="Tipo de comprobante")
    numero_comprobante: str = Field(..., description="Número de comprobante")
    fecha_emision: str = Field(..., description="Fecha de emisión")
    
    # Fiscal simplificado
    subtotal: float = Field(..., description="Subtotal", ge=0)
    total_iva: float = Field(..., description="Total IVA", ge=0)
    importe_total: float = Field(..., description="Total a pagar", ge=0)


# =============================================================================
# SCHEMA COMPOSER - Generador de schemas modulares
# =============================================================================

class SchemaComposer:
    """
    Generador de schemas Pydantic dinámicos para extracción modular.
    
    Permite extraer solo los segmentos necesarios de una factura.
    
    Uso:
        # Extraer solo items y fiscalidad
        composer = SchemaComposer(segments=['items', 'fiscalidad'])
        schema = composer.get_schema()
        
        # Extraer todo
        composer = SchemaComposer(segments='all')
        schema = composer.get_schema()
    """
    
    AVAILABLE_SEGMENTS = {'items', 'partes', 'fiscalidad', 'totales', 'documento'}
    
    def __init__(self, segments: Optional[List[str]] = None):
        """
        Inicializar el composer.
        
        Args:
            segments: Lista de segmentos a incluir, o 'all'/None para todos.
                     Opciones: ['items', 'partes', 'fiscalidad', 'totales', 'documento']
        """
        if segments is None or segments == 'all' or (isinstance(segments, list) and 'all' in segments):
            self.segments = self.AVAILABLE_SEGMENTS.copy()
        else:
            # Validar segmentos
            invalid = set(segments) - self.AVAILABLE_SEGMENTS
            if invalid:
                raise ValueError(
                    f"Segmentos inválidos: {invalid}. "
                    f"Disponibles: {self.AVAILABLE_SEGMENTS}"
                )
            self.segments = set(segments)
    
    def get_schema(self) -> type:
        """
        Generar schema Pydantic dinámico con los segmentos seleccionados.
        
        Returns:
            Clase Pydantic con solo los campos solicitados
        """
        fields = {}
        
        if 'items' in self.segments:
            fields['items'] = (
                List[InvoiceItem],
                Field(..., description="Lista de items", min_length=1)
            )
        
        if 'partes' in self.segments:
            fields['partes'] = (
                InvoicePartes,
                Field(..., description="Empresa y Cliente")
            )
        
        if 'documento' in self.segments:
            fields['documento'] = (
                InvoiceDocumento,
                Field(..., description="Datos del documento")
            )
        
        if 'fiscalidad' in self.segments:
            fields['fiscalidad'] = (
                InvoiceFiscalidad,
                Field(..., description="Totales e impuestos")
            )
        
        if 'totales' in self.segments and 'fiscalidad' not in self.segments:
            fields['totales'] = (
                InvoiceTotales,
                Field(..., description="Totales")
            )
        
        # Crear modelo dinámico
        model_name = f"Invoice_{'_'.join(sorted(self.segments))}"
        
        return create_model(
            model_name,
            **fields,
            __doc__=f"Schema dinámico con segmentos: {', '.join(sorted(self.segments))}"
        )
    
    def get_segment_list(self) -> List[str]:
        """Retorna lista de segmentos incluidos."""
        return sorted(list(self.segments))
    
    @classmethod
    def get_available_segments(cls) -> Set[str]:
        """Retorna segmentos disponibles."""
        return cls.AVAILABLE_SEGMENTS.copy()


# =============================================================================
# ALIASES PARA COMPATIBILIDAD (desde schemas.py original)
# =============================================================================

# Estos aliases permiten usar los nombres originales
Partes = InvoicePartes
Documento = InvoiceDocumento
Fiscalidad = InvoiceFiscalidad
Totales = InvoiceTotales
Calculos = InvoiceCalculos
Impuestos = InvoiceImpuestos
ComprobanteArgentino = InvoiceComplete
ComprobanteSimplificado = InvoiceSimplificado

