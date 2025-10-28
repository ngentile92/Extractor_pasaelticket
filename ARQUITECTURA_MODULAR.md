# 🏗️ Arquitectura del Sistema Modular

## 📊 Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USUARIO / CLIENTE                            │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ POST /api/invoices/process/
                                  │ - document: file
                                  │ - schema_type: "modular"
                                  │ - segments: ["items", "documento"]
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     API ENDPOINT (views.py)                          │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  1. Parse parámetros (schema_type, segments)               │    │
│  │  2. Crear InvoiceExtractionService(schema_type, segments)  │    │
│  │  3. Extraer datos                                          │    │
│  │  4. Post-procesar                                          │    │
│  │  5. Mapear a Django models (condicional por segmento)      │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│              INVOICE EXTRACTION SERVICE (services.py)                │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Si schema_type == "modular":                              │    │
│  │    ┌───────────────────────────────────────────┐           │    │
│  │    │  SchemaComposer(segments)                 │           │    │
│  │    │  ↓                                        │           │    │
│  │    │  - Validar segmentos                     │           │    │
│  │    │  - Generar schema Pydantic dinámico      │           │    │
│  │    │  - create_model() con campos selectos    │           │    │
│  │    └───────────────────────────────────────────┘           │    │
│  │  Sino:                                                     │    │
│  │    - Usar ComprobanteArgentino (completo)                  │    │
│  │    - o ComprobanteSimplificado                             │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   LLAMA EXTRACT (LlamaCloud API)                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  1. Crear/obtener agente con schema dinámico               │    │
│  │  2. Enviar documento + schema                              │    │
│  │  3. LLM extrae SOLO los campos del schema                  │    │
│  │  4. Retornar datos estructurados                           │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    POST-PROCESADOR (post_processor.py)               │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  FASE 1: Normalización                                     │    │
│  │  - Textos a mayúsculas                                     │    │
│  │  - Fechas a formato ISO                                    │    │
│  │  - CUITs normalizados                                      │    │
│  │  - Provincias estandarizadas                               │    │
│  │                                                            │    │
│  │  FASE 2: Correcciones                                      │    │
│  │  - Consolidar domicilios                                   │    │
│  │  - Corregir tipos de comprobante (catálogo AFIP)           │    │
│  │  - Recalcular totales fiscales                             │    │
│  │                                                            │    │
│  │  FASE 3: Validaciones                                      │    │
│  │  - Validación aritmética                                   │    │
│  │  - Validación AFIP                                         │    │
│  │  - Normalización IIBB provincias                           │    │
│  │  - Calcular validation_score                               │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DJANGO MODELS (models.py)                       │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Invoice:                                                  │    │
│  │  - Datos del documento (si 'documento' en segments)        │    │
│  │  - Datos de empresa/cliente (si 'partes' en segments)      │    │
│  │  - Totales (si 'fiscalidad' o 'totales' en segments)       │    │
│  │  - validation_score                                        │    │
│  │  - raw_extraction (JSON con todo)                          │    │
│  │                                                            │    │
│  │  InvoiceItem: (si 'items' en segments)                     │    │
│  │  - código, descripción, cantidad, precio, subtotal         │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         RESPUESTA JSON                               │
│  {                                                                   │
│    "id": 1,                                                          │
│    "status": "completed",                                            │
│    "message": "Invoice processed successfully",                      │
│    "data": {                                                         │
│      "items": [...],          // Solo si segment 'items' incluido    │
│      "documento": {...},      // Solo si segment 'documento' incluido│
│      "raw_extraction": {                                             │
│        "extraction_metadata": {                                      │
│          "schema_type": "modular",                                   │
│          "segments": ["documento", "items"]                          │
│        }                                                             │
│      }                                                               │
│    }                                                                 │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Schemas Dinámicos

### Ejemplo 1: Extracción de Items + Documento

```python
# Input
segments = ['items', 'documento']

# SchemaComposer genera dinámicamente:
ComprobanteArgentino_documento_items = create_model(
    'ComprobanteArgentino_documento_items',
    items=(
        List[InvoiceItem],
        Field(..., description="List of line items")
    ),
    documento=(
        Documento,
        Field(..., description="Document information")
    )
)

# LlamaExtract extrae SOLO estos campos
{
  "items": [
    {"codigo": "123", "descripcion": "Producto", ...}
  ],
  "documento": {
    "tipo_comprobante": "FACTURAS A",
    "numero_comprobante": "001-00000123",
    ...
  }
}
```

### Ejemplo 2: Extracción de Partes solamente

```python
# Input
segments = ['partes']

# SchemaComposer genera:
ComprobanteArgentino_partes = create_model(
    'ComprobanteArgentino_partes',
    partes=(
        Partes,
        Field(..., description="Parties involved")
    )
)

# LlamaExtract extrae SOLO partes
{
  "partes": {
    "empresa": {
      "razon_social": "COCA-COLA FEMSA",
      "cuit": "30-71106763-9",
      ...
    },
    "cliente": {
      "apellido_nombre_razon_social": "BUSAN MOTORS S.A.",
      "cuit": "30-71366962-5",
      ...
    }
  }
}
```

## 🧩 Componentes del Sistema

### 1. SchemaComposer (schemas.py)

```python
class SchemaComposer:
    AVAILABLE_SEGMENTS = {
        'items', 'partes', 'fiscalidad', 'totales', 'documento'
    }
    
    def __init__(self, segments: Optional[List[str]] = None):
        # Validar y almacenar segmentos
        
    def get_schema(self) -> type[BaseModel]:
        # Crear schema Pydantic dinámico con create_model()
        
    def get_segment_list(self) -> List[str]:
        # Retornar lista de segmentos incluidos
```

**Responsabilidades:**
- ✅ Validar segmentos solicitados
- ✅ Generar schemas Pydantic dinámicos
- ✅ Reutilizar componentes base (Cliente, Empresa, etc.)

### 2. InvoiceExtractionService (services.py)

```python
class InvoiceExtractionService:
    def __init__(
        self,
        schema_type: str = "completo",
        segments: Optional[List[str]] = None
    ):
        if schema_type == "modular":
            self.schema_composer = SchemaComposer(segments)
        
    def _get_schema(self) -> Type:
        if self.schema_type == "modular":
            return self.schema_composer.get_schema()
        elif self.schema_type == "simplificado":
            return ComprobanteSimplificado
        return ComprobanteArgentino
```

**Responsabilidades:**
- ✅ Inicializar SchemaComposer si es modular
- ✅ Obtener schema apropiado
- ✅ Crear/obtener agentes de LlamaExtract
- ✅ Ejecutar extracción

### 3. InvoiceViewSet (views.py)

```python
@action(detail=False, methods=['post'], url_path='process')
def upload(self, request):
    # 1. Parse parámetros
    schema_type = request.data.get('schema_type', 'completo')
    segments = request.data.getlist('segments[]') or None
    
    # 2. Inicializar servicio
    service = InvoiceExtractionService(schema_type, segments)
    
    # 3. Extraer
    result = service.extract_invoice_data(file_path)
    
    # 4. Mapear a models (CONDICIONAL)
    if 'documento' in processed_data:
        # Mapear documento
    if 'partes' in processed_data:
        # Mapear empresa y cliente
    if 'items' in processed_data:
        # Crear InvoiceItems
    if 'fiscalidad' in processed_data:
        # Mapear totales e impuestos
```

**Responsabilidades:**
- ✅ Parsear parámetros de request
- ✅ Mapear datos extraídos a Django models
- ✅ Manejar segmentos faltantes (dejar NULL)
- ✅ Guardar metadata de extracción

## 📊 Comparación de Modos

| Aspecto | Completo | Modular | Simplificado |
|---------|----------|---------|--------------|
| **Segmentos** | Todos | Seleccionables | Básicos fijos |
| **Flexibilidad** | ❌ Baja | ✅ Alta | ❌ Baja |
| **Velocidad** | 🐢 Lenta | 🚀 Rápida | 🚀 Rápida |
| **Costo** | 💰💰💰 Alto | 💰 Variable | 💰 Bajo |
| **Casos de uso** | Auditoría completa | Optimización | Prototipos |

## 🎯 Casos de Uso por Segmento

```
┌────────────────────────────────────────────────────────────┐
│  SEGMENTOS          │  CASOS DE USO                        │
├────────────────────────────────────────────────────────────┤
│  items              │  • Inventario                        │
│                     │  • Comparación de precios            │
│                     │  • Análisis de productos             │
├────────────────────────────────────────────────────────────┤
│  partes             │  • Registro proveedores/clientes     │
│                     │  • Verificación CUIT                 │
│                     │  • Base de datos contactos           │
├────────────────────────────────────────────────────────────┤
│  documento          │  • Clasificación documentos          │
│                     │  • Verificación CAE                  │
│                     │  • Organización archivo              │
├────────────────────────────────────────────────────────────┤
│  fiscalidad         │  • Contabilidad completa             │
│                     │  • Auditoría fiscal                  │
│                     │  • Reportes de impuestos             │
├────────────────────────────────────────────────────────────┤
│  totales            │  • Resúmenes rápidos                 │
│                     │  • Dashboard financiero              │
│                     │  • Validación montos                 │
└────────────────────────────────────────────────────────────┘
```

## 🔧 Extensibilidad

### Agregar Nuevo Segmento

1. **Definir schema en schemas.py:**
```python
class Transporte(BaseModel):
    tipo_transporte: str
    patente: Optional[str]
    chofer: Optional[str]
```

2. **Agregar a AVAILABLE_SEGMENTS:**
```python
AVAILABLE_SEGMENTS = {
    'items', 'partes', 'documento', 'fiscalidad', 'totales',
    'transporte'  # ← Nuevo
}
```

3. **Agregar caso en SchemaComposer.get_schema():**
```python
if 'transporte' in self.segments:
    fields['transporte'] = (
        Transporte,
        Field(..., description="Transport information")
    )
```

4. **Actualizar mapeo en views.py:**
```python
if 'transporte' in processed_data:
    transporte = processed_data.get('transporte', {})
    invoice.tipo_transporte = transporte.get('tipo_transporte')
    # ...
```

---

**Sistema completamente funcional y extensible** 🎉
