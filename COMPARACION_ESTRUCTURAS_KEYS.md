# 📊 Comparación de Estructuras - Solo Keys (no valores)

## 🎯 DIFERENCIAS ESTRUCTURALES CLAVE

### 1️⃣ **NIVEL RAÍZ DEL JSON**

#### ❌ Estructura Nueva (Actual):
```json
{
  "raw_data": {...},
  "processed_data": {...},
  "validation_result": {...},
  "processing_metadata": {...},
  "extraction_metadata": {...}
}
```

#### ✅ Estructura Vieja (Target/Legacy):
```json
{
  "items": [...],
  "partes": {...},
  "documento": {...},
  "fiscalidad": {...}
}
```

**🔑 Diferencia:** Nueva estructura tiene wrappers (`raw_data`, `processed_data`), vieja es **directa en raíz**.

---

### 2️⃣ **ITEMS**

#### Estructura Nueva:
```json
"processed_data": {
  "items": [
    {
      "codigo": ...,
      "descripcion": ...,
      "cantidad": ...,
      "unidad_medida": ...,
      "precio_unitario": ...,
      "subtotal": ...
    }
  ]
}
```

#### Estructura Vieja:
```json
"items": [
  {
    "codigo": ...,
    "cantidad": ...,
    "subtotal": ...,
    "descripcion": ...,
    "unidad_medida": ...,
    "precio_unitario": ...
  }
]
```

**✅ Keys idénticas:** `codigo`, `descripcion`, `cantidad`, `unidad_medida`, `precio_unitario`, `subtotal`
**🔑 Diferencia:** Solo el orden de las keys (no importa en JSON)

---

### 3️⃣ **PARTES**

#### Estructura Nueva:
```json
"processed_data": {
  "partes": {
    "empresa": {
      "cuit": ...,
      "provincia": ...,
      "condicion_iva": ...,
      "domicilio_calle": ...,          // ← NUEVO
      "domicilio_localidad": ...,      // ← NUEVO
      "domicilio_codigo_postal": ...,  // ← NUEVO
      "razon_social": ...,
      "ingresos_brutos": ...,
      "domicilio_comercial": ...,
      "fecha_inicio_actividades": ...
    },
    "cliente": {
      "cuit": ...,
      "provincia": ...,
      "condicion_iva": ...,
      "domicilio_calle": ...,          // ← NUEVO
      "domicilio_localidad": ...,      // ← NUEVO
      "domicilio_codigo_postal": ...,  // ← NUEVO
      "apellido_nombre_razon_social": ...,
      "domicilio": ...
    }
  }
}
```

#### Estructura Vieja:
```json
"partes": {
  "cliente": {
    "cuit": ...,
    "domicilio": ...,
    "provincia": ...,
    "condicion_iva": ...,
    "domicilio_calle": null,           // ← Existe pero null
    "domicilio_localidad": null,       // ← Existe pero null
    "apellido_nombre_razon_social": ...
  },
  "empresa": {
    "cuit": ...,
    "provincia": ...,
    "razon_social": ...,
    "condicion_iva": ...,
    "domicilio_calle": null,           // ← Existe pero null
    "ingresos_brutos": ...,
    "domicilio_comercial": ...,
    "domicilio_localidad": null,       // ← Existe pero null
    "domicilio_codigo_postal": null,  // ← Existe pero null
    "fecha_inicio_actividades": ...
  }
}
```

**✅ Keys compatibles:** Todas las keys existen en ambas estructuras
**🔑 Diferencia:** Orden de keys (cliente/empresa) y valores null vs valores presentes

---

### 4️⃣ **DOCUMENTO**

#### Estructura Nueva:
```json
"processed_data": {
  "documento": {
    "tipo_comprobante": ...,
    "codigo": ...,
    "numero_comprobante": ...,
    "punto_venta": ...,
    "fecha_emision": ...,
    "cae": ...,
    "fecha_vencimiento_cae": ...,
    "moneda": ...,
    "condicion_venta": ...,
    "numero_remito": null,
    "observaciones": null,
    "numero_orden_compra": ...,
    "fecha_vencimiento_pago": null
  }
}
```

#### Estructura Vieja:
```json
"documento": {
  "cae": ...,
  "codigo": ...,
  "moneda": ...,
  "punto_venta": ...,
  "fecha_emision": ...,
  "numero_remito": null,
  "observaciones": ...,
  "condicion_venta": ...,
  "tipo_comprobante": ...,
  "numero_comprobante": ...,
  "numero_orden_compra": null,
  "fecha_vencimiento_cae": ...,
  "fecha_vencimiento_pago": null
}
```

**✅ Keys idénticas:** Todas las keys existen en ambas estructuras
**🔑 Diferencia:** Solo orden de keys (no importa en JSON)

---

### 5️⃣ **FISCALIDAD - Totales**

#### Estructura Nueva:
```json
"processed_data": {
  "fiscalidad": {
    "totales": {
      "subtotal_gravado": ...,
      "importe_total": ...
    }
  }
}
```

#### Estructura Vieja:
```json
"fiscalidad": {
  "totales": {
    "descuentos": 0,           // ← FALTA en nueva
    "importe_total": ...,
    "subtotal_gravado": ...
  }
}
```

**🔑 Diferencia:** Nueva estructura **NO tiene** `descuentos` en `totales` (aunque la normalización lo agrega)

---

### 6️⃣ **FISCALIDAD - Cálculos**

#### Estructura Nueva:
```json
"processed_data": {
  "fiscalidad": {
    "calculos": {
      "total_iva_calculado": ...,
      "total_percepciones_calculado": ...,
      "total_retenciones_calculado": ...,
      "diferencia_matematica": ...
    }
  }
}
```

#### Estructura Vieja:
```json
"fiscalidad": {
  "calculos": {
    "items_count": 11,                  // ← FALTA en nueva
    "total_iva_calculado": ...,
    "items_subtotal_total": ...,        // ← FALTA en nueva
    "diferencia_matematica": ...,
    "total_retenciones_calculado": null,
    "total_percepciones_calculado": ...
  }
}
```

**🔑 Diferencias:**
- Nueva estructura **NO tiene** `items_count`
- Nueva estructura **NO tiene** `items_subtotal_total`

---

### 7️⃣ **FISCALIDAD - Impuestos (CRÍTICO)**

#### Estructura Nueva:
```json
"processed_data": {
  "fiscalidad": {
    "impuestos": {
      "iva_21": 187276.7,        // ← Formato plano
      "iva_105": 0.0,
      "iva_27": 0.0,
      "percepcion_iibb": [...],
      "impuestos_internos": 0.0
    }
  }
}
```

#### Estructura Vieja:
```json
"fiscalidad": {
  "impuestos": {
    "iva": {                    // ← Formato dict anidado
      "21": 187276.7
    },
    "icl_idc": 0,               // ← FALTA en nueva
    "retencion_iva": null,      // ← FALTA en nueva
    "percepcion_iva": 0,        // ← FALTA en nueva
    "retencion_suss": null,     // ← FALTA en nueva
    "percepcion_iibb": [...],
    "retenciones_iibb": [],     // ← FALTA en nueva
    "otras_retenciones": null,  // ← FALTA en nueva
    "impuestos_internos": 0,
    "retencion_ganancias": null,     // ← FALTA en nueva
    "percepcion_ganancias": 0        // ← FALTA en nueva
  }
}
```

**🔑 Diferencias CRÍTICAS:**

1. **IVA Structure:**
   - Nueva: `iva_21`, `iva_105`, `iva_27` (campos planos)
   - Vieja: `iva: {"21": valor}` (dict anidado)

2. **Campos faltantes en nueva:**
   - `icl_idc`
   - `retencion_iva`
   - `percepcion_iva`
   - `retencion_suss`
   - `retenciones_iibb`
   - `otras_retenciones`
   - `retencion_ganancias`
   - `percepcion_ganancias`

---

## 📋 RESUMEN DE CAMBIOS ESTRUCTURALES NECESARIOS

### ✅ Ya implementado:
1. ✅ Normalización de `iva_X` → `iva: {"X": valor}`
2. ✅ Agregar `descuentos` en `totales` si falta
3. ✅ Salida directa en raíz (sin `raw_data`, `processed_data` wrappers)

### ⚠️ Pendiente:
1. ⚠️ Asegurar que `totales.descuentos` siempre existe
2. ⚠️ Asegurar que `calculos.items_count` siempre existe
3. ⚠️ Asegurar que `calculos.items_subtotal_total` siempre existe
4. ⚠️ Asegurar que todos los campos de `impuestos` existen (aunque sean null/0):
   - `icl_idc`
   - `retencion_iva`
   - `percepcion_iva`
   - `retencion_suss`
   - `retenciones_iibb`
   - `otras_retenciones`
   - `retencion_ganancias`
   - `percepcion_ganancias`

---

## 🎯 ESTRUCTURA FINAL TARGET

```json
{
  "items": [...],
  "partes": {...},
  "documento": {...},
  "fiscalidad": {
    "totales": {
      "descuentos": 0,           // ← SIEMPRE presente
      "importe_total": ...,
      "subtotal_gravado": ...
    },
    "calculos": {
      "items_count": 11,         // ← SIEMPRE presente
      "items_subtotal_total": ..., // ← SIEMPRE presente
      "total_iva_calculado": ...,
      "total_percepciones_calculado": ...,
      "total_retenciones_calculado": null,
      "diferencia_matematica": ...
    },
    "impuestos": {
      "iva": {                   // ← Formato dict anidado
        "21": 187276.7
      },
      "icl_idc": 0,              // ← SIEMPRE presente
      "retencion_iva": null,     // ← SIEMPRE presente
      "percepcion_iva": 0,       // ← SIEMPRE presente
      "retencion_suss": null,    // ← SIEMPRE presente
      "percepcion_iibb": [...],
      "retenciones_iibb": [],    // ← SIEMPRE presente
      "otras_retenciones": null, // ← SIEMPRE presente
      "impuestos_internos": 0,
      "retencion_ganancias": null,  // ← SIEMPRE presente
      "percepcion_ganancias": 0     // ← SIEMPRE presente
    }
  },
  "metadata": {...}  // ← Opcional, nuevo campo
}
```

---

## 🔧 ACCIONES REQUERIDAS

1. **Actualizar `normalize_fiscalidad()`** para asegurar todos los campos de `impuestos`
2. **Actualizar `normalize_fiscalidad()`** para calcular `items_count` y `items_subtotal_total` en `calculos`
3. **Verificar que `descuentos` siempre existe** en `totales`

