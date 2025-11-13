# ✅ Estado de las Validaciones y Retry

## 📋 Resumen Ejecutivo

**¿Se están ejecutando las validaciones?** ✅ **SÍ**

**¿Los errores se usan en el retry?** ✅ **SÍ**

**¿Se comparan resultados finales después del retry?** ✅ **SÍ**

---

## 1. ✅ Validaciones Implementadas

### 1.1 CUIT con Dígito Verificador

**Archivo**: `invoice_extractor/validators/cuit_validator.py`

**Qué hace**:
- Valida formato `XX-XXXXXXXX-X`
- Calcula dígito verificador con algoritmo AFIP (módulo 11)
- Multiplicadores: `[5, 4, 3, 2, 7, 6, 5, 4, 3, 2]`
- Valida prefijos válidos (20, 23, 24, 27, 30, 33, 34)

```python
@staticmethod
def calculate_verifier_digit(cuit_base: str) -> int:
    """Calcula dígito verificador según algoritmo AFIP (módulo 11)"""
    digits = cuit_base[:10]
    suma = sum(int(d) * m for d, m in zip(digits, MULTIPLIERS))
    verificador = 11 - (suma % 11)
    
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9
    
    return verificador
```

**Genera**:
- ❌ **Error** si el CUIT es inválido
- ⚠️ **Warning** si falta el dígito verificador

---

### 1.2 Validación de Items: cantidad × precio = subtotal

**Archivo**: `invoice_extractor/validators/items_validator.py`

**Qué hace**:
```python
@staticmethod
def validate_item_calculation(item: Dict) -> Dict[str, Any]:
    """Valida que subtotal = cantidad × precio_unitario"""
    
    cantidad = safe_float(item.get('cantidad', 0))
    precio_unitario = safe_float(item.get('precio_unitario', 0))
    subtotal_declarado = safe_float(item.get('subtotal', 0))
    
    subtotal_calculado = cantidad * precio_unitario
    diferencia = abs(subtotal_calculado - subtotal_declarado)
    
    is_valid = diferencia <= 0.01  # Tolerancia de 1 centavo
```

**Genera**:
- ❌ **Error** si `|cantidad × precio - subtotal| > $0.01`
- ⚠️ **Warning** si la diferencia es < 1% pero > $0.01

---

### 1.3 Validación de Suma de Items

**Archivo**: `invoice_extractor/validators/items_validator.py`

**Qué hace**:
```python
@staticmethod
def validate_items_sum(items: List[Dict], declared_total: float) -> Dict:
    """Valida que Σ(subtotales) = total declarado"""
    
    total_calculado = sum(safe_float(item.get('subtotal', 0)) 
                          for item in items)
    
    diferencia = abs(total_calculado - declared_total)
    is_valid = diferencia <= 0.01  # Tolerancia de 1 centavo
```

**Genera**:
- ❌ **Error** si `|Σ(subtotales) - subtotal_gravado| > $0.01`

---

### 1.4 Validación de Total Final

**Archivo**: `invoice_extractor/validators/fiscal_validator_advanced.py`

**Qué hace**:
```python
def validate_total_calculation(self, fiscalidad: Dict) -> Dict:
    """
    Formula:
    TOTAL = subtotal_gravado 
            - descuentos
            + IVA (21% + 10.5% + 27% + ...)
            + percepciones
            - retenciones
            + impuestos_internos
            + ICL/IDC
    """
    
    total_calculado = (subtotal_gravado 
                       - descuentos
                       + total_iva
                       + percepciones
                       - retenciones
                       + impuestos_internos
                       + icl_idc)
    
    diferencia = abs(total_calculado - importe_total_declarado)
    is_valid = diferencia <= 0.50  # Tolerancia de $0.50
```

**Genera**:
- ❌ **Error** si `|total_calculado - importe_total| > $0.50`
- ⚠️ **Warning** si la diferencia es > $0.10 pero <= $0.50

---

### 1.5 Otras Validaciones Contables

**Archivo**: `invoice_extractor/validators/fiscal_validator.py`

#### Invariante 1: Consistencia Items-Subtotal
```python
suma_items = sum(item['subtotal'] for item in items)
subtotal_gravado = totales['subtotal_gravado']

if abs(suma_items - subtotal_gravado) > tolerancia:
    errors.append("Inconsistencia items-subtotal")
```

#### Invariante 2: Subtotal + Impuestos = Total
```python
total_calculado = subtotal + total_impuestos - descuentos
if abs(total_calculado - importe_total) > tolerancia:
    errors.append("Inconsistencia subtotal+impuestos≠total")
```

#### Validación de Discriminación de IVA
```python
total_iva = iva_21 + iva_105 + iva_27 + iva_5 + iva_25
# Verifica que cada tasa esté correctamente aplicada
```

---

## 2. ✅ Flujo de Retry con Contexto

### 2.1 LlamaExtract Flow (`/api/invoices/process/`)

```
┌─────────────────────────────────────────┐
│ 1. Extracción con LlamaExtract          │
└─────────────────────┬───────────────────┘
                      │
┌─────────────────────▼───────────────────┐
│ 2. Post-procesamiento                   │
│    - Normalización                       │
│    - Correcciones                        │
│    - VALIDACIONES (CUIT, Items, Totales)│
└─────────────────────┬───────────────────┘
                      │
                      │ validation_score
                      │
┌─────────────────────▼───────────────────┐
│ 3. ¿score <= 0.8?                       │
└─────────────────────┬───────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │ SÍ                        │ NO
        ▼                           ▼
┌────────────────────┐    ┌──────────────────┐
│ 4. RETRY con Gemini│    │ Devolver resultado│
│    + contexto       │    └──────────────────┘
│    de errores      │
└────────┬───────────┘
         │
┌────────▼───────────────────────────────┐
│ 5. Re-procesamiento                    │
│    - Normalización                      │
│    - Correcciones                       │
│    - RE-VALIDACIONES                    │
└────────┬───────────────────────────────┘
         │
┌────────▼───────────────────────────────┐
│ 6. Comparar scores                     │
│    Devolver MEJOR resultado            │
└────────────────────────────────────────┘
```

**Código clave** (`invoice_extractor/utils/post_processor.py:195-285`):

```python
def process_with_gemini_retry(self, extracted_data, file_path):
    # PASO 1: Procesar primera extracción
    first_result = self.process(extracted_data)
    first_score = first_result["validation_result"]["validation_score"]
    first_errors = first_result["validation_result"]["validation_errors"]
    
    # PASO 2: ¿Vale la pena re-extraer?
    if not self.gemini_corrector.should_retry(first_result['validation_result']):
        return first_result
    
    # PASO 3: Re-extraer con Gemini + contexto de errores
    logger.info("🔄 Re-extrayendo con Gemini + contexto...")
    retry_extracted = self.gemini_corrector.retry_extraction_with_gemini(
        file_path=file_path,
        original_data=first_result['processed_data'],
        validation_result=first_result['validation_result']  # ← Errores de validación
    )
    
    if retry_extracted:
        # PASO 4: Re-procesar Y RE-VALIDAR
        retry_result = self.process(retry_extracted)  # ← Ejecuta TODAS las validaciones de nuevo
        retry_score = retry_result['validation_result']['validation_score']
        
        # PASO 5: Comparar y elegir el mejor
        if retry_score > first_score:
            return retry_result
        else:
            return first_result
    
    return first_result
```

---

### 2.2 Gemini Puro Flow (`/api/invoices-gemini/upload-gemini/`)

**Idéntico** al flujo de LlamaExtract, pero:
- Primera extracción es con **Gemini** (no LlamaExtract)
- Retry también usa **Gemini** (con contexto)

**Código** (`invoice_extractor/views_gemini.py:185-220`):

```python
# PASO 2: Procesar y validar
result = processor.process(extracted)
validation_score = result['validation_result']['validation_score']

# PASO 3: ¿Retry?
if enable_retry and validation_score <= 0.8:
    retry_extracted = gemini_extractor.retry_with_context(
        file_path=file_path,
        original_data=extracted,
        validation_result=result['validation_result']  # ← Errores
    )
    
    if retry_extracted:
        # Re-procesar Y RE-VALIDAR
        retry_result = processor.process(retry_extracted)
        retry_score = retry_result['validation_result']['validation_score']
        
        # Comparar y elegir
        if retry_score > validation_score:
            # Usar resultado del retry
            result = retry_result
```

---

## 3. ✅ Contexto de Errores en el Retry

**Archivo**: `invoice_extractor/services_gemini_corrector.py:198-306`

### Prompt Generado para Gemini

```python
def build_correction_prompt(self, original_data, validation_result):
    errors = validation_result.get("validation_errors", [])
    
    prompt = """
🚨 ATENCIÓN: La extracción automática anterior tuvo ERRORES MATEMÁTICOS.

📋 ERRORES DETECTADOS:
  1. Item #0: subtotal incorrecto (cant:2 × $1500 = $3000, pero tiene $3100)
  2. CUIT empresa inválido: 30-5348596-8 (verificador incorrecto, debe ser 5)
  3. Inconsistencia suma items: $15,234.50 vs subtotal gravado: $15,230.00
  4. Total calculado $18,456.78 ≠ total declarado $18,450.00

📊 DATOS EXTRAÍDOS (CON ERRORES):
Items extraídos (5 items):
  1. ❌ 001 | HAMBURGUESA... | cant:2 × $1,500.00 = $3,100.00  ← Debería ser $3,000
  2. ✅ 002 | PAPAS... | cant:3 × $500.00 = $1,500.00
  ...

Totales extraídos:
  - Subtotal gravado: $15,230.00
  - Importe total: $18,450.00

🎯 TU TAREA: Re-extraer CORRECTAMENTE, corrigiendo errores.

🔍 INSTRUCCIONES CRÍTICAS:
1. Para CADA item: cantidad × precio_unitario = subtotal
2. Suma TODOS los subtotales = subtotal_gravado
3. Verifica CUIT con dígito verificador correcto
4. Calcula: subtotal + IVA + percepciones = total
...
"""
```

**El prompt incluye**:
- ❌ Lista de errores específicos
- 📊 Datos extraídos (con indicadores de qué está mal)
- 🎯 Instrucciones para corregir cada tipo de error
- ⚠️ Contexto específico según tipo de error

---

## 4. ✅ Re-validación Después del Retry

### Confirmación en el Código

**`invoice_extractor/utils/post_processor.py:269`**:
```python
if retry_extracted:
    # Re-procesar Y RE-VALIDAR
    retry_result = self.process(retry_extracted)  # ← Ejecuta TODO de nuevo
    retry_score = retry_result['validation_result']['validation_score']
```

**`processor.process()` ejecuta** (`post_processor.py:73-150`):
1. **Normalización** (`normalize_all`)
2. **Correcciones** (`apply_all_corrections`)
3. **Validaciones COMPLETAS**:
   - `MasterValidator.validate_complete()`
     - CUIT empresa y cliente (con dígito verificador)
     - Items (cantidad × precio = subtotal)
     - Suma de items
     - Fiscalidad (IVA, percepciones, totales)
     - Consistencia aritmética
4. **Scoring** (`ConfidenceScorer`)

**Por lo tanto**: Después del retry, se ejecutan TODAS las validaciones nuevamente y se generan nuevos errores/warnings.

---

## 5. ✅ Comparación de Resultados FINALES

### En el Test

**Archivo**: `test_gemini_endpoint.py:579-617`

```python
def compare_with_llamaextract(file_name: str):
    # 1. Extraer con LlamaExtract
    llama_response = requests.post(
        f"{BASE_URL}/invoices/process/",
        files={'document': file},
        data={'schema_type': 'completo'},
        timeout=180
    ).json()  # ← Respuesta FINAL (después de retry si hubo)
    
    # 2. Extraer con Gemini
    gemini_response = requests.post(
        f"{BASE_URL}/invoices-gemini/upload-gemini/",
        files={'document': file},
        data={'schema_type': 'completo'},
        timeout=180
    ).json()  # ← Respuesta FINAL (después de retry si hubo)
    
    # 3. Comparar
    llama_score = llama_response['data']['metadata']['validation']['validation_score']
    gemini_score = gemini_response['data']['metadata']['validation']['validation_score']
    
    # 4. Generar reporte
    generate_comparison_report(file_name, llama_response, gemini_response)
```

**✅ SÍ, estamos comparando los resultados FINALES** porque:
- Cada endpoint (`/invoices/process/` y `/invoices-gemini/upload-gemini/`) devuelve el resultado **después** de:
  1. Extracción inicial
  2. Post-procesamiento y validación
  3. Retry con contexto (si `score <= 0.8`)
  4. Re-procesamiento y re-validación
  5. Selección del mejor resultado

---

## 6. ⚠️ Warnings Finales en la Respuesta

### Estructura de Respuesta

```json
{
  "id": 1,
  "status": "completed",
  "data": {
    "items": [...],
    "documento": {...},
    "partes": {...},
    "fiscalidad": {...},
    "metadata": {
      "extraction": {
        "extraction_method": "llamaextract",
        "extraction_time": 15.47,
        "retry_used": true,
        "retry_method": "gemini-2.5-flash",
        "improvement": "+0.15pp"
      },
      "validation": {
        "validation_score": 0.85,
        "confidence_level": "medium",
        "validation_errors": [
          "CUIT empresa: dígito verificador incorrecto",
          "Item #2: subtotal no coincide (esperado $1500, tiene $1520)"
        ],
        "validation_warnings": [
          "Diferencia menor en suma de items: $0.50"
        ],
        "requires_review": true
      }
    }
  }
}
```

**Los warnings finales** se devuelven en:
- `data.metadata.validation.validation_errors` ← Errores que quedaron después del retry
- `data.metadata.validation.validation_warnings` ← Warnings que quedaron

---

## 7. 📊 Resumen de Validaciones por Categoría

| Categoría | Validación | Tolerancia | Genera Error | Archivo |
|-----------|------------|------------|--------------|---------|
| **CUIT** | Dígito verificador | Exacto | ✅ | `cuit_validator.py` |
| **CUIT** | Formato válido | Exacto | ✅ | `cuit_validator.py` |
| **Items** | cant × precio = subtotal | $0.01 | ✅ | `items_validator.py` |
| **Items** | Σ(subtotales) = subtotal_gravado | $0.01 | ✅ | `items_validator.py` |
| **Totales** | subtotal + IVA = total | $0.50 | ✅ | `fiscal_validator_advanced.py` |
| **IVA** | Discriminación por alícuota | $0.50 | ⚠️ | `fiscal_validator_advanced.py` |
| **Percepciones** | Consistencia | $0.50 | ⚠️ | `fiscal_validator_advanced.py` |
| **Retenciones** | Consistencia | $0.50 | ⚠️ | `fiscal_validator_advanced.py` |

---

## 8. ✅ Conclusión

### ¿Están todas las validaciones activas?

**✅ SÍ**, todas se ejecutan en:
1. Post-procesamiento inicial
2. Re-procesamiento después del retry

### ¿Los errores se usan para el retry?

**✅ SÍ**, se pasan a Gemini en un prompt detallado con:
- Lista de errores específicos
- Datos extraídos (con indicadores de qué está mal)
- Instrucciones para corregir

### ¿Se comparan resultados finales?

**✅ SÍ**, las comparaciones son entre:
- Resultado final de LlamaExtract (después de retry si hubo)
- Resultado final de Gemini (después de retry si hubo)

### ¿Se devuelven warnings finales?

**✅ SÍ**, en `data.metadata.validation`:
- `validation_errors`: Errores que persistieron
- `validation_warnings`: Warnings menores
- `requires_review`: Flag si necesita revisión manual

---

## 💡 Recomendaciones

### 1. Agregar más validaciones contables

**Sugerencias**:

#### A. Validación de Percepciones IIBB
```python
# Si hay percepción IIBB, debe ser ~3-5% del subtotal
if percepcion_iibb > 0:
    expected_range = (subtotal * 0.025, subtotal * 0.055)
    if not (expected_range[0] <= percepcion_iibb <= expected_range[1]):
        warnings.append(
            f"Percepción IIBB fuera de rango esperado (2.5%-5.5%): "
            f"${percepcion_iibb} sobre subtotal ${subtotal}"
        )
```

#### B. Validación de Coherencia de Fechas
```python
# CAE no puede estar vencido (vto < fecha_emision)
if fecha_vencimiento_cae < fecha_emision:
    errors.append(
        f"CAE vencido: vto {fecha_vencimiento_cae} < emisión {fecha_emision}"
    )
```

#### C. Validación de Rangos de Precios
```python
# Detectar precios anormalmente altos/bajos
for item in items:
    if item['precio_unitario'] > 1_000_000:
        warnings.append(
            f"Precio unitario muy alto en '{item['descripcion']}': "
            f"${item['precio_unitario']:,.2f}"
        )
    if item['precio_unitario'] < 0.01 and item['cantidad'] > 0:
        warnings.append(
            f"Precio unitario muy bajo en '{item['descripcion']}': "
            f"${item['precio_unitario']:.4f}"
        )
```

#### D. Validación de Tipo de Comprobante vs Condición IVA
```python
# Factura A requiere que ambas partes sean RI
if tipo_comprobante == "FACTURA A":
    if empresa['condicion_iva'] != "RESPONSABLE INSCRIPTO":
        errors.append("Factura A pero empresa no es RI")
    if cliente['condicion_iva'] != "RESPONSABLE INSCRIPTO":
        errors.append("Factura A pero cliente no es RI")

# Factura B requiere que al menos uno sea no-RI
if tipo_comprobante == "FACTURA B":
    if (empresa['condicion_iva'] == "RESPONSABLE INSCRIPTO" and
        cliente['condicion_iva'] == "RESPONSABLE INSCRIPTO"):
        warnings.append("Factura B pero ambas partes son RI (debería ser A)")
```

### 2. Mejorar logging de validaciones

Agregar más detalles en los logs:
```python
logger.info(f"🔍 Validando CUIT empresa: {cuit}")
logger.info(f"   Prefijo: {cuit[:2]} → {tipo_persona}")
logger.info(f"   Dígito verificador: esperado={esperado}, actual={actual}")
```

### 3. Exportar validaciones en JSON estructurado

```json
{
  "validation_details": {
    "cuit_empresa": {
      "value": "30-53485961-5",
      "is_valid": true,
      "verifier_digit": {
        "expected": 5,
        "actual": 5,
        "is_correct": true
      }
    },
    "items": [
      {
        "index": 0,
        "calculation": {
          "cantidad": 2,
          "precio_unitario": 1500.00,
          "expected_subtotal": 3000.00,
          "actual_subtotal": 3000.00,
          "difference": 0.00,
          "is_valid": true
        }
      }
    ]
  }
}
```

---

**Fecha**: 2025-11-09  
**Autor**: Asistente AI  
**Estado**: ✅ Validado y documentado

