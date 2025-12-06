# 📚 API Usage Guide - Invoice Extraction

## 🎯 Endpoints Disponibles

### 1. `/api/invoices/process/` - Procesar una factura (LlamaExtract + Gemini retry opcional)
### 2. `/api/invoices/process-gemini/` - 🆕 Procesar una factura con Gemini 2.5 Flash exclusivamente
### 3. `/api/invoices/process-batch/` - Procesar múltiples facturas en paralelo (hasta 8)

---

## 🆚 Comparación de Endpoints

| Aspecto | `/process/` (Principal) | `/process-gemini/` (Gemini Puro) |
|---------|------------------------|-----------------------------------|
| **Extractor inicial** | LlamaExtract | Gemini 2.5 Flash |
| **Retry automático** | Gemini (si score < 0.6) | Gemini con contexto (si score < 0.6) |
| **Tiempo promedio** | 8-15s | 12-20s |
| **Post-procesamiento** | ✅ Completo | ✅ Completo (idéntico) |
| **Validaciones** | ✅ Todas | ✅ Todas (idéntico) |
| **Formato de respuesta** | ✅ Legacy format | ✅ Legacy format (idéntico) |
| **Extracción modular** | ✅ Soportado | ✅ Soportado |
| **Costo estimado** | $0.002-0.005 | $0.01-0.02 |
| **Cuándo usar** | Default, producción | Testing, backup, comparación |

### 💡 Recomendaciones

- **Usa `/process/`** (principal) para:
  - Producción general
  - Mejor balance velocidad/costo
  - Flujo probado y estable

- **Usa `/process-gemini/`** (Gemini puro) para:
  - Testing y comparación de resultados
  - Backup si LlamaExtract tiene problemas
  - Facturas complejas que podrían beneficiarse de Gemini
  - Evaluación de proveedores

---

## 📄 1. Procesar Una Factura Individual

### Endpoint
```
POST /api/invoices/process/
```

### Parámetros

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `document` | File | ✅ Sí | - | Archivo de factura (PDF, JPG, PNG, DOCX) |
| `schema_type` | String | ❌ No | `completo` | Tipo de extracción: `completo`, `simplificado`, `modular` |
| `segments` | Array | ❌ No | - | Segmentos a extraer (solo si `schema_type=modular`) |
| `use_gemini_only` | Boolean | ❌ No | `false` | Usar solo Gemini sin LlamaExtract |

### Ejemplos cURL

#### Extracción completa (default)
```bash
curl -X POST http://localhost:8000/api/invoices/process/ \
  -F "document=@Ejemplo1.jpeg"
```

#### Extracción modular (solo items y documento)
```bash
curl -X POST http://localhost:8000/api/invoices/process/ \
  -F "document=@Ejemplo1.jpeg" \
  -F "schema_type=modular" \
  -F "segments[]=items" \
  -F "segments[]=documento"
```

#### Usar solo Gemini (sin LlamaExtract)
```bash
curl -X POST http://localhost:8000/api/invoices/process/ \
  -F "document=@Ejemplo1.jpeg" \
  -F "use_gemini_only=true"
```

### Response (Estructura Original)

```json
{
  "id": 123,
  "status": "completed",
  "message": "Invoice processed successfully",
  "data": {
    "items": [
      {
        "codigo": "13186",
        "descripcion": "ALCAPARRAS VINAG C/PONTE 830G",
        "cantidad": 1.0,
        "unidad_medida": "G",
        "precio_unitario": 11208.1,
        "subtotal": 11208.1
      }
    ],
    "partes": {
      "cliente": {
        "apellido_nombre_razon_social": "BLUE NIGHT SRL",
        "cuit": "33-71677240-9",
        "condicion_iva": "IVA RESPONSABLE INSCRIPTO",
        "domicilio": "AV COSTANERA RAFAEL OBLIGADO 6600",
        "domicilio_calle": null,
        "domicilio_localidad": null,
        "provincia": "Capital Federal"
      },
      "empresa": {
        "razon_social": "El Emporio de Lanús S.A.",
        "cuit": "33-70715731-9",
        "condicion_iva": "IVA RESPONSABLE INSCRIPTO",
        "ingresos_brutos": "902-618019-0",
        "domicilio_comercial": "Sitio de Montevideo 2035/37",
        "domicilio_calle": null,
        "domicilio_localidad": null,
        "domicilio_codigo_postal": null,
        "provincia": "Buenos Aires",
        "fecha_inicio_actividades": "01/05/2000"
      }
    },
    "documento": {
      "tipo_comprobante": "FACTURAS A",
      "codigo": "001",
      "numero_comprobante": "00010-00665092",
      "punto_venta": "00010",
      "fecha_emision": "22/09/2025",
      "cae": "75389042666725",
      "fecha_vencimiento_cae": "02/10/2025",
      "moneda": "ARS",
      "condicion_venta": "20 DIAS F.F.",
      "numero_remito": null,
      "observaciones": "SI EL PAGO EXCEDE...",
      "numero_orden_compra": null,
      "fecha_vencimiento_pago": null
    },
    "fiscalidad": {
      "totales": {
        "subtotal_gravado": 891793.82,
        "importe_total": 1105824.33,
        "descuentos": 0
      },
      "calculos": {
        "items_count": 11,
        "items_subtotal_total": 891793.82,
        "total_iva_calculado": 187276.7,
        "total_percepciones_calculado": 26753.81,
        "total_retenciones_calculado": null,
        "diferencia_matematica": 0
      },
      "impuestos": {
        "iva": {
          "21": 187276.7
        },
        "icl_idc": 0,
        "retencion_iva": null,
        "percepcion_iva": 0,
        "retencion_suss": null,
        "percepcion_iibb": [
          {
            "provincia": "caba",
            "monto": 26753.81
          }
        ],
        "retenciones_iibb": [],
        "otras_retenciones": null,
        "impuestos_internos": 0,
        "retencion_ganancias": null,
        "percepcion_ganancias": 0
      }
    },
    "metadata": {
      "validation": {
        "validation_score": 1.0,
        "confidence_level": "high",
        "has_validation_errors": false,
        "requires_review": false,
        "errors_count": 0,
        "warnings_count": 4,
        "alerts_count": 4
      },
      "processing": {
        "processing_time": 0.523,
        "processing_timestamp": "2025-11-05T20:30:15.123456",
        "pipeline_version": "1.0.0",
        "phases_executed": ["normalization", "corrections", "fiscal_validation"]
      },
      "extraction": {
        "extraction_time": 12.5,
        "extraction_method": "llamaextract",
        "schema_type": "completo"
      },
      "gemini_retry": {
        "used": true,
        "first_score": 0.65,
        "second_score": 1.0,
        "improvement": 35.0,
        "method_used": "gemini"
      }
    }
  }
}
```

---

## 🤖 2. Procesar con Gemini 2.5 Flash Exclusivamente

### Endpoint
```
POST /api/invoices-gemini/upload-gemini/
```

### Descripción

Este endpoint utiliza **exclusivamente Gemini 2.5 Flash** para la extracción, sin usar LlamaExtract. Mantiene el mismo post-procesamiento, validaciones y formato de respuesta que el endpoint principal.

**Ventajas**:
- No requiere LLAMAAPI_KEY (solo credenciales de Google)
- Un solo proveedor (Google)
- Útil para testing A/B y comparación de resultados
- Backup si LlamaExtract tiene problemas

**Diferencias con `/process/`**:
- Extracción inicial con Gemini en lugar de LlamaExtract
- Retry también con Gemini (con contexto enriquecido)
- Mismo formato de respuesta (100% compatible)

### Parámetros

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `document` | File | ✅ Sí | - | Archivo de factura (PDF, JPG, PNG) |
| `schema_type` | String | ❌ No | `completo` | Tipo de extracción: `completo`, `simplificado`, `modular` |
| `segments` | Array | ❌ No | - | Segmentos a extraer (solo si `schema_type=modular`) |
| `enable_retry` | Boolean | ❌ No | `true` | Habilitar retry automático con contexto si score < 0.6 |

### Ejemplos cURL

#### Extracción completa con Gemini
```bash
curl -X POST http://localhost:8000/api/invoices-gemini/upload-gemini/ \
  -F "document=@Ejemplo1.jpeg"
```

#### Extracción modular (solo items y fiscalidad)
```bash
curl -X POST http://localhost:8000/api/invoices-gemini/upload-gemini/ \
  -F "document=@Ejemplo2.jpeg" \
  -F "schema_type=modular" \
  -F "segments[]=items" \
  -F "segments[]=fiscalidad"
```

#### Sin retry automático
```bash
curl -X POST http://localhost:8000/api/invoices-gemini/upload-gemini/ \
  -F "document=@Ejemplo3.jpeg" \
  -F "enable_retry=false"
```

### Response (Idéntico al endpoint principal)

```json
{
  "id": 456,
  "status": "completed",
  "message": "Invoice processed successfully with Gemini",
  "data": {
    "items": [...],
    "partes": {...},
    "documento": {...},
    "fiscalidad": {...},
    "metadata": {
      "validation": {
        "validation_score": 0.92,
        "confidence_level": "high",
        "has_validation_errors": false,
        "requires_review": false,
        "errors_count": 0,
        "warnings_count": 1,
        "alerts_count": 0
      },
      "processing": {
        "processing_time": 2.45,
        "processing_timestamp": "2025-11-09T15:30:00",
        "pipeline_version": "1.0.0",
        "phases_executed": [
          "normalization",
          "corrections",
          "fiscal_validation"
        ]
      },
      "extraction": {
        "extraction_time": 12.8,
        "extraction_method": "gemini-2.5-flash",
        "schema_type": "completo"
      },
      "gemini_retry": {
        "used": true,
        "first_score": 0.55,
        "second_score": 0.92,
        "improvement": 37.0,
        "method_used": "gemini"
      }
    }
  }
}
```

### Campos Específicos de Gemini

#### `metadata.extraction.extraction_method`
- Valor: `"gemini-2.5-flash"`
- Indica que se usó Gemini exclusivamente

#### `metadata.gemini_retry` (opcional)
Solo presente si se activó el retry automático:

```json
{
  "used": true,
  "first_score": 0.55,
  "second_score": 0.92,
  "improvement": 37.0,
  "method_used": "gemini"
}
```

- `used`: `true` si se ejecutó el retry
- `first_score`: Score de la primera extracción
- `second_score`: Score de la segunda extracción (con contexto)
- `improvement`: Mejora en puntos porcentuales
- `method_used`: `"gemini"` (siempre, ya que ambas extracciones son con Gemini)

### Testing y Comparación

#### Script de comparación
```python
import requests

# Endpoint principal (LlamaExtract)
r1 = requests.post('http://localhost:8000/api/invoices/process/', 
                   files={'document': open('Ejemplo1.jpeg', 'rb')})

# Endpoint Gemini
r2 = requests.post('http://localhost:8000/api/invoices-gemini/upload-gemini/', 
                   files={'document': open('Ejemplo1.jpeg', 'rb')})

# Comparar scores
score1 = r1.json()['data']['metadata']['validation']['validation_score']
score2 = r2.json()['data']['metadata']['validation']['validation_score']

print(f"LlamaExtract: {score1:.2%}")
print(f"Gemini:       {score2:.2%}")
```

---

## 📦 3. Procesar Múltiples Facturas en Paralelo

### Endpoint
```
POST /api/invoices/process-batch/
```

### Características
- ✅ Procesa hasta **8 facturas simultáneamente**
- ✅ Usa **ThreadPoolExecutor** para máxima eficiencia
- ✅ Retorna resultados individuales para cada factura
- ✅ Estadísticas agregadas (éxito/fallo, tiempo total)

### Parámetros

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `documents` | File[] | ✅ Sí | - | Lista de archivos de facturas (máx. 8) |
| `schema_type` | String | ❌ No | `completo` | Se aplica a TODAS las facturas |
| `segments` | Array | ❌ No | - | Se aplica a TODAS las facturas |
| `use_gemini_only` | Boolean | ❌ No | `false` | Se aplica a TODAS las facturas |

### Ejemplos cURL

#### Procesar 3 facturas simultáneamente
```bash
curl -X POST http://localhost:8000/api/invoices/process-batch/ \
  -F "documents=@Ejemplo1.jpeg" \
  -F "documents=@Ejemplo2.jpeg" \
  -F "documents=@Ejemplo3.jpeg"
```

#### Procesar múltiples facturas con extracción modular
```bash
curl -X POST http://localhost:8000/api/invoices/process-batch/ \
  -F "documents=@factura1.pdf" \
  -F "documents=@factura2.pdf" \
  -F "documents=@factura3.pdf" \
  -F "documents=@factura4.pdf" \
  -F "schema_type=modular" \
  -F "segments[]=items" \
  -F "segments[]=documento" \
  -F "segments[]=fiscalidad"
```

#### Procesar 8 facturas (máximo) usando solo Gemini
```bash
curl -X POST http://localhost:8000/api/invoices/process-batch/ \
  -F "documents=@f1.jpg" \
  -F "documents=@f2.jpg" \
  -F "documents=@f3.jpg" \
  -F "documents=@f4.jpg" \
  -F "documents=@f5.jpg" \
  -F "documents=@f6.jpg" \
  -F "documents=@f7.jpg" \
  -F "documents=@f8.jpg" \
  -F "use_gemini_only=true"
```

### Response

```json
{
  "total": 3,
  "successful": 2,
  "failed": 1,
  "processing_time": 18.45,
  "results": [
    {
      "success": true,
      "id": 124,
      "status": "completed",
      "filename": "Ejemplo1.jpeg",
      "data": {
        "items": [...],
        "partes": {...},
        "documento": {...},
        "fiscalidad": {...},
        "metadata": {...}
      }
    },
    {
      "success": true,
      "id": 125,
      "status": "completed",
      "filename": "Ejemplo2.jpeg",
      "data": {
        "items": [...],
        "partes": {...},
        "documento": {...},
        "fiscalidad": {...},
        "metadata": {...}
      }
    },
    {
      "success": false,
      "id": 126,
      "status": "failed",
      "filename": "Ejemplo3.jpeg",
      "error": "Extraction failed: Invalid document format"
    }
  ]
}
```

---

## 🔧 Diferencias Clave entre Estructura Original y Nueva

### ✅ Campos Idénticos
- `items[]` - Misma estructura
- `partes.cliente` - Misma estructura
- `partes.empresa` - Misma estructura
- `documento` - Misma estructura base

### 🔄 Campos Transformados

#### 1. **Impuestos IVA**
**Original (esperado):**
```json
"impuestos": {
  "iva": {
    "21": 187276.7,
    "105": 0,
    "27": 0
  }
}
```

**Nueva estructura interna (antes de transformación):**
```json
"impuestos": {
  "iva_21": 187276.7,
  "iva_105": 0,
  "iva_27": 0
}
```

**✅ Solución:** La función `transform_to_legacy_format()` convierte automáticamente `iva_21` → `iva.21`

#### 2. **Totales**
**Original:**
```json
"totales": {
  "subtotal_gravado": 891793.82,
  "importe_total": 1105824.33,
  "descuentos": 0
}
```

**✅ Asegurado:** Se agrega `descuentos: 0` si falta

#### 3. **Cálculos**
**Original:**
```json
"calculos": {
  "items_count": 11,
  "items_subtotal_total": 891793.82,
  "total_iva_calculado": 187276.7,
  "total_percepciones_calculado": 26753.81,
  "total_retenciones_calculado": null,
  "diferencia_matematica": 0
}
```

**✅ Asegurado:** Se calcula `items_count` y `items_subtotal_total` si faltan

---

## 🆕 Metadata Adicional

La estructura original se mantiene IDÉNTICA, pero ahora se agrega un objeto `metadata` opcional con información adicional:

```json
"metadata": {
  "validation": {
    "validation_score": 1.0,
    "confidence_level": "high",
    "has_validation_errors": false,
    "requires_review": false,
    "errors_count": 0,
    "warnings_count": 4,
    "alerts_count": 4
  },
  "processing": {
    "processing_time": 0.523,
    "processing_timestamp": "2025-11-05T20:30:15.123456",
    "pipeline_version": "1.0.0",
    "phases_executed": ["normalization", "corrections", "fiscal_validation"]
  },
  "extraction": {
    "extraction_time": 12.5,
    "extraction_method": "llamaextract",
    "schema_type": "completo"
  },
  "gemini_retry": {
    "used": true,
    "first_score": 0.65,
    "second_score": 1.0,
    "improvement": 35.0,
    "method_used": "gemini"
  }
}
```

Este objeto es **opcional** y puede ser ignorado si solo te interesa la estructura original (`items`, `partes`, `documento`, `fiscalidad`).

---

## 🚀 Ventajas del Endpoint Batch

### Procesamiento en Paralelo
- Procesa hasta 8 facturas simultáneamente
- Tiempo total = ~tiempo de la factura más lenta (no suma de todas)
- Ejemplo: 8 facturas que tardan 10s cada una → ~10-12s total (vs 80s secuencial)

### Estadísticas Agregadas
- Total procesado
- Éxitos/Fallos
- Tiempo total
- Resultados individuales

### Manejo de Errores
- Si una factura falla, las demás continúan
- Cada resultado indica éxito/fallo individualmente
- Errores detallados en modo DEBUG

---

## 📊 Comparación de Tiempos

| Facturas | Secuencial | Paralelo (batch) | Mejora |
|----------|------------|------------------|--------|
| 1 | 10s | 10s | 0% |
| 2 | 20s | 10-11s | 45-50% |
| 4 | 40s | 11-13s | 67-70% |
| 8 | 80s | 12-15s | 81-85% |

---

## 🔐 Seguridad y Límites

- **Máximo 8 documentos** por batch (para evitar sobrecarga)
- Validación de tipos de archivo
- Límites de tamaño de archivo (configurables en Django settings)
- Timeout por documento (para evitar bloqueos infinitos)

---

## 🐛 Troubleshooting

### Error: "No documents provided"
**Solución:** Usar `documents` (plural) como nombre del campo:
```bash
-F "documents=@file1.pdf" -F "documents=@file2.pdf"
```

### Error: "Maximum 8 documents allowed"
**Solución:** Dividir en múltiples requests o procesar secuencialmente.

### Error: "Processing failed"
**Solución:** Activar DEBUG en settings para ver detalles del error.

---

## 📝 Notas Finales

1. **Estructura idéntica a la original:** Los campos principales (`items`, `partes`, `documento`, `fiscalidad`) son 100% compatibles.
2. **Metadata opcional:** Puedes ignorar el objeto `metadata` si no lo necesitas.
3. **Procesamiento inteligente:** Gemini retry automático si hay errores matemáticos.
4. **Escalabilidad:** El endpoint batch es ideal para procesamiento masivo.

