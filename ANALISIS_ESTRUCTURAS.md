# 📊 Análisis de Diferencias entre Estructuras

## 🎯 Estructura Original (Target)
```json
{
  "items": [...],
  "partes": {...},
  "documento": {...},
  "fiscalidad": {...}
}
```

## 🔄 Estructura Actual (Nueva)
```json
{
  "raw_data": {...},
  "processed_data": {...},
  "validation_result": {...},
  "processing_metadata": {...},
  "extraction_metadata": {...}
}
```

---

## 📋 DIFERENCIAS DETALLADAS

### 1️⃣ **ITEMS**

#### Original:
- Raíz directa: `items[]`
- Campos: `codigo`, `cantidad`, `subtotal`, `descripcion`, `unidad_medida`, `precio_unitario`

#### Actual:
- Dentro de: `processed_data.items[]`
- **MISMO formato de campos** ✅

**Acción**: Mover `processed_data.items` → raíz `items`

---

### 2️⃣ **PARTES**

#### Original:
```json
"partes": {
  "cliente": {
    "cuit": "33-71677240-9",
    "domicilio": "...",
    "provincia": "Capital Federal",
    "condicion_iva": "IVA RESPONSABLE INSCRIPTO",
    "domicilio_calle": null,
    "domicilio_localidad": null,
    "apellido_nombre_razon_social": "BLUE NIGHT SRL"
  },
  "empresa": {
    "cuit": "33-70715731-9",
    "provincia": "Buenos Aires",
    "razon_social": "El Emporio de Lanús S.A.",
    "condicion_iva": "IVA RESPONSABLE INSCRIPTO",
    "domicilio_calle": null,
    "ingresos_brutos": "902-618019-0",
    "domicilio_comercial": "...",
    "domicilio_localidad": null,
    "domicilio_codigo_postal": null,
    "fecha_inicio_actividades": "01/05/2000"
  }
}
```

#### Actual:
```json
"processed_data.partes": {
  "empresa": { /* mismo orden de campos */ },
  "cliente": { /* mismo orden de campos */ }
}
```

**Diferencias**:
- ❌ Condición IVA incompleta en actual: `"RESPONSABLE INSCRIPTO"` vs `"IVA RESPONSABLE INSCRIPTO"`
- ❌ Provincia normalizada en actual: `"BUENOS AIRES"` vs `"Buenos Aires"`
- ❌ Razón social normalizada: `"EL EMPORIO DE LANUS S.A."` vs `"El Emporio de Lanús S.A."`

**Acción**: Preservar valores originales (sin normalización agresiva)

---

### 3️⃣ **DOCUMENTO**

#### Original:
```json
"documento": {
  "cae": "75389042666725",
  "codigo": "001",
  "moneda": "ARS",
  "punto_venta": "00010",
  "fecha_emision": "22/09/2025",
  "numero_remito": null,
  "observaciones": "SI EL PAGO EXCEDE...",
  "condicion_venta": "20 DIAS F.F.",
  "tipo_comprobante": "FACTURAS A",
  "numero_comprobante": "00010-00665092",
  "numero_orden_compra": null,
  "fecha_vencimiento_cae": "02/10/2025",
  "fecha_vencimiento_pago": null
}
```

#### Actual:
```json
"processed_data.documento": {
  "tipo_comprobante": "FACTURA A",  // ❌ Falta la 'S'
  "codigo": "001",
  "numero_comprobante": "0010-00665092",  // ❌ Punto de venta con menos ceros
  "punto_venta": "0010",  // ❌ 4 dígitos vs 5
  "fecha_emision": "22/09/2025",
  "cae": "75389042666725",
  "fecha_vencimiento_cae": "02/10/2025",
  "moneda": "ARS",
  "condicion_venta": "DEPOSITO EN CTA, 20 DIAS F.F.",  // ❌ Texto diferente
  "numero_remito": null,
  "observaciones": null,  // ❌ Perdió las observaciones
  "numero_orden_compra": "0000400243532",  // ❌ Valor diferente
  "fecha_vencimiento_pago": null
}
```

**Acción**: Preservar valores extraídos originalmente (sin normalización)

---

### 4️⃣ **FISCALIDAD**

#### Original:
```json
"fiscalidad": {
  "totales": {
    "descuentos": 0,
    "importe_total": 1105824.33,
    "subtotal_gravado": 891793.82
  },
  "calculos": {
    "items_count": 11,
    "total_iva_calculado": 187276.7,
    "items_subtotal_total": 891793.82,
    "diferencia_matematica": 0,
    "total_retenciones_calculado": null,
    "total_percepciones_calculado": 26753.81
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
        "monto": 26753.81,
        "provincia": "caba"
      }
    ],
    "retenciones_iibb": [],
    "otras_retenciones": null,
    "impuestos_internos": 0,
    "retencion_ganancias": null,
    "percepcion_ganancias": 0
  }
}
```

#### Actual:
```json
"processed_data.fiscalidad": {
  "totales": {
    "subtotal_gravado": 891793.82,
    "importe_total": 1105824.33
    // ❌ Falta "descuentos"
  },
  "impuestos": {
    "iva_21": 187276.7,  // ❌ Estructura plana vs anidada
    "iva_105": 0.0,
    "iva_27": 0.0,
    "percepcion_iibb": [...],
    "impuestos_internos": 0.0
    // ❌ Faltan varios campos (retencion_iva, retencion_ganancias, etc.)
  },
  "calculos": {
    "total_iva_calculado": 187276.7,
    "total_percepciones_calculado": 26753.81,
    "total_retenciones_calculado": 0.0,
    "diferencia_matematica": 0.0
    // ❌ Faltan items_count, items_subtotal_total
  }
}
```

**Diferencias críticas**:
- ❌ `impuestos.iva` debería ser objeto anidado: `{"21": 187276.7}` no `iva_21: 187276.7`
- ❌ Faltan campos en totales, calculos, impuestos

---

## 🎯 PLAN DE ACCIÓN

### 1. **Adaptar Estructura de Salida**
- Crear función `transform_to_legacy_format()` que convierta:
  - `processed_data.items` → `items`
  - `processed_data.partes` → `partes`
  - `processed_data.documento` → `documento`
  - `processed_data.fiscalidad` → `fiscalidad` (con transformaciones)

### 2. **Preservar Datos Originales**
- No normalizar agresivamente (mantener mayúsculas/minúsculas originales)
- No perder campos como `observaciones`
- Mantener formato de IVA como objeto anidado

### 3. **Estructura Final Propuesta**
```json
{
  // ========== ESTRUCTURA ORIGINAL (raíz) ==========
  "items": [...],
  "partes": {...},
  "documento": {...},
  "fiscalidad": {...},
  
  // ========== METADATA ADICIONAL (opcional) ==========
  "metadata": {
    "validation": {...},  // Resumen de validación
    "processing": {...},  // Tiempos, versión
    "extraction": {...}   // Método usado, Gemini, etc.
  }
}
```

### 4. **Endpoint Batch (Paralelo)**
- Nuevo endpoint: `POST /api/invoices/process-batch/`
- Acepta hasta 8 imágenes simultáneas
- Usa `asyncio.gather()` o `ThreadPoolExecutor`
- Retorna array de resultados con mismo formato

---

## 🔧 ARCHIVOS A MODIFICAR

1. **`invoice_extractor/utils/post_processor.py`**
   - Agregar método `transform_to_legacy_format()`
   - Ajustar normalizaciones para preservar datos originales

2. **`invoice_extractor/views.py`**
   - Crear `ProcessBatchInvoiceView` 
   - Modificar salida de `ProcessInvoiceView` para usar nuevo formato

3. **`invoice_extractor/schemas.py`**
   - Actualizar schema de fiscalidad (IVA anidado)

4. **`invoice_extractor/urls.py`**
   - Agregar ruta `/process-batch/`

