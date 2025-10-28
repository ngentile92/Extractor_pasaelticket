# 📦 Extracción Modular de Facturas Argentinas

## 🎯 Descripción

El sistema de extracción de facturas argentinas ahora soporta **extracción modular**, permitiéndote seleccionar qué segmentos de información extraer de los documentos. Esto te permite:

- **Optimizar costos**: Extrae solo lo que necesitas
- **Mejorar velocidad**: Menos datos = procesamiento más rápido
- **Flexibilidad**: Adapta la extracción a diferentes casos de uso

## 📋 Segmentos Disponibles

El sistema divide la información de la factura en 5 segmentos principales:

| Segmento | Descripción | Incluye |
|----------|-------------|---------|
| **`items`** | Line items / Productos | Código, descripción, cantidad, precio unitario, subtotal |
| **`partes`** | Emisor y Receptor | Datos de empresa (emisor) y cliente (receptor): CUIT, razón social, domicilio, condición IVA |
| **`documento`** | Datos del documento | Tipo de comprobante, número, punto de venta, CAE, fechas, condición de venta |
| **`fiscalidad`** | Información fiscal completa | Totales, cálculos, impuestos (IVA, percepciones, retenciones) |
| **`totales`** | Solo totales | Subtotal, descuentos, importe total (solo si `fiscalidad` no está incluida) |

## 🚀 Uso

### 1. API REST (Endpoint)

#### Extraer TODO (comportamiento por defecto)

```bash
curl -X POST http://127.0.0.1:8000/api/invoices/process/ \
  -F "document=@invoice.pdf"
```

#### Extraer solo Items y Documento

```bash
curl -X POST http://127.0.0.1:8000/api/invoices/process/ \
  -F "document=@invoice.pdf" \
  -F "schema_type=modular" \
  -F "segments[]=items" \
  -F "segments[]=documento"
```

#### Extraer solo Partes y Fiscalidad

```bash
curl -X POST http://127.0.0.1:8000/api/invoices/process/ \
  -F "document=@invoice.pdf" \
  -F "schema_type=modular" \
  -F "segments[]=partes" \
  -F "segments[]=fiscalidad"
```

#### Extraer solo Documento

```bash
curl -X POST http://127.0.0.1:8000/api/invoices/process/ \
  -F "document=@invoice.pdf" \
  -F "schema_type=modular" \
  -F "segments[]=documento"
```

### 2. Python (Script de prueba)

```bash
# Extraer todo
python test_modular_extraction.py invoice.pdf

# Extraer solo items y documento
python test_modular_extraction.py invoice.pdf items documento

# Extraer solo partes
python test_modular_extraction.py invoice.pdf partes

# Extraer fiscalidad y documento
python test_modular_extraction.py invoice.pdf fiscalidad documento
```

### 3. Código Python (Programático)

```python
from invoice_extractor.services import InvoiceExtractionService

# Extraer todo (default)
service = InvoiceExtractionService(schema_type='completo')
result = service.extract_invoice_data('invoice.pdf')

# Extraer solo items y documento
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['items', 'documento']
)
result = service.extract_invoice_data('invoice.pdf')

# Extraer solo partes
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['partes']
)
result = service.extract_invoice_data('invoice.pdf')

# Extraer fiscalidad completa
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['fiscalidad', 'documento']
)
result = service.extract_invoice_data('invoice.pdf')
```

## 📊 Ejemplos de Respuesta

### Extracción Completa

```json
{
  "success": true,
  "data": {
    "items": [...],
    "partes": {...},
    "documento": {...},
    "fiscalidad": {...}
  },
  "metadata": {
    "extraction_time": 45.23,
    "schema_type": "completo",
    "agent_name": "comprobante-argentino-completo"
  }
}
```

### Extracción Modular (items + documento)

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "codigo": "100912",
        "descripcion": "MONSTER GREEN EAN 473X6",
        "cantidad": 2,
        "unidad_medida": "CJ",
        "precio_unitario": 8396.12,
        "subtotal": 16792.24
      }
    ],
    "documento": {
      "tipo_comprobante": "FACTURAS A",
      "codigo": "001",
      "numero_comprobante": "00001-00000599",
      "punto_venta": "00001",
      "fecha_emision": "16/10/2023",
      "cae": "354116294418039"
    }
  },
  "metadata": {
    "extraction_time": 32.15,
    "schema_type": "modular",
    "segments": ["documento", "items"],
    "agent_name": "comprobante-argentino-modular-documento_items"
  }
}
```

## 🎯 Casos de Uso

### 1. Solo necesito ver los items
```python
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['items']
)
```
**Ideal para**: Inventario, validación de productos, comparación de precios

### 2. Solo necesito identificar el documento
```python
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['documento']
)
```
**Ideal para**: Clasificación de documentos, verificación de CAE, organización

### 3. Solo necesito saber quién facturó a quién
```python
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['partes']
)
```
**Ideal para**: Registro de proveedores/clientes, verificación de CUIT

### 4. Solo necesito los montos totales
```python
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['fiscalidad']  # o ['totales'] si solo quieres subtotal/total/descuentos
)
```
**Ideal para**: Contabilidad rápida, resúmenes financieros

### 5. Necesito todo excepto items (documento + partes + fiscalidad)
```python
service = InvoiceExtractionService(
    schema_type='modular',
    segments=['documento', 'partes', 'fiscalidad']
)
```
**Ideal para**: Auditoría fiscal sin necesidad de detalle de items

## ⚡ Ventajas

### Optimización de Costos
- LlamaExtract cobra por tokens procesados
- Menos campos = menos tokens = menor costo

### Velocidad
- Menos datos a extraer = procesamiento más rápido
- Ideal para procesamiento en batch de miles de facturas

### Flexibilidad
- Adapta la extracción a tu caso de uso específico
- Combina segmentos según necesites

## 🔧 Configuración Avanzada

### Crear Schema Personalizado

```python
from invoice_extractor.schemas import SchemaComposer

# Crear compositor de schema
composer = SchemaComposer(segments=['items', 'documento'])

# Obtener el schema Pydantic dinámico
schema = composer.get_schema()

# Ver qué segmentos están incluidos
print(composer.get_segment_list())  # ['documento', 'items']

# Ver todos los segmentos disponibles
print(SchemaComposer.get_available_segments())  
# {'items', 'partes', 'documento', 'fiscalidad', 'totales'}
```

## 📝 Notas Importantes

1. **`fiscalidad` incluye `totales`**: Si pides `fiscalidad`, automáticamente obtienes `totales`, `calculos` e `impuestos`.

2. **`totales` solo funciona si no hay `fiscalidad`**: Si quieres solo subtotal/total/descuentos sin el resto de la información fiscal, usa `totales` sin `fiscalidad`.

3. **Agentes LlamaExtract**: Se crean agentes diferentes para cada combinación de segmentos. El sistema los reutiliza automáticamente.

4. **Post-procesamiento**: El post-procesamiento (normalización, correcciones, validaciones) se aplica a todos los datos extraídos, independientemente de los segmentos seleccionados.

5. **Base de datos**: Los campos no extraídos quedarán como `NULL` en la base de datos. El `schema_type` guardado incluirá información de los segmentos (ej: `"modular_documento_items"`).

## 🧪 Testing

Usa el script de prueba incluido para experimentar:

```bash
# Ver ayuda
python test_modular_extraction.py

# Probar diferentes combinaciones
python test_modular_extraction.py invoice.pdf items
python test_modular_extraction.py invoice.pdf partes documento
python test_modular_extraction.py invoice.pdf fiscalidad
```

## 📚 Referencia Rápida

| Schema Type | Descripción | Uso |
|-------------|-------------|-----|
| `completo` | Extrae todo | Por defecto, máxima información |
| `simplificado` | Schema básico | Casos muy simples, no modular |
| `modular` | Selección de segmentos | Máxima flexibilidad |

## 🎉 Ejemplos Completos

### Ejemplo 1: Pipeline de clasificación y extracción

```python
# Paso 1: Clasificar documento (solo documento)
service_clasificacion = InvoiceExtractionService(
    schema_type='modular',
    segments=['documento']
)
doc_info = service_clasificacion.extract_invoice_data('invoice.pdf')

# Paso 2: Si es factura A, extraer fiscalidad completa
if doc_info['data']['documento']['tipo_comprobante'] == 'FACTURAS A':
    service_fiscal = InvoiceExtractionService(
        schema_type='modular',
        segments=['fiscalidad', 'partes']
    )
    fiscal_data = service_fiscal.extract_invoice_data('invoice.pdf')
```

### Ejemplo 2: Extracción progresiva

```python
# Primero: Solo totales para decisión rápida
service_totales = InvoiceExtractionService(
    schema_type='modular',
    segments=['totales', 'documento']
)
quick_check = service_totales.extract_invoice_data('invoice.pdf')

# Si el total es > $100,000, extraer todo
if quick_check['data']['totales']['importe_total'] > 100000:
    service_completo = InvoiceExtractionService(schema_type='completo')
    full_data = service_completo.extract_invoice_data('invoice.pdf')
```

---

**¿Preguntas?** Revisa la documentación completa en `README.md` o abre un issue en el repositorio.

