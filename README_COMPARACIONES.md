# 📊 Sistema de Comparación: LlamaExtract vs Gemini

## 🎯 Objetivo

Este sistema compara automáticamente las extracciones de facturas entre **LlamaExtract** y **Gemini 2.5 Flash**, generando reportes detallados que te permiten:

1. Ver diferencias campo por campo
2. Revisar manualmente cuál tuvo razón
3. Mejorar los prompts y validaciones
4. Evaluar cuál extractor usar en producción

---

## 🔄 Flujo de Retry Automático

**Ambos endpoints usan retry automático cuando `validation_score <= 0.8`**:

### LlamaExtract (`/api/invoices/process/`)
```
1. Extracción inicial con LlamaExtract
2. Post-procesamiento + Validación → Score
3. Si score <= 80% → Retry con Gemini + contexto de errores
4. Devolver mejor resultado
```

### Gemini Puro (`/api/invoices-gemini/upload-gemini/`)
```
1. Extracción inicial con Gemini 2.5 Flash
2. Post-procesamiento + Validación → Score
3. Si score <= 80% → Retry con Gemini + contexto de errores
4. Devolver mejor resultado
```

**Ejemplos del test**:
- Score 85% → ✅ NO retry (score > 80%)
- Score 80% → ⚠️ SÍ retry (score <= 80%)
- Score 65% → ⚠️ SÍ retry (score <= 80%)
- Score 50% → ⚠️ SÍ retry (score <= 80%)

---

## 📁 Estructura de Archivos Generados

Cuando ejecutas `python test_gemini_endpoint.py`, se crea el directorio `comparaciones_gemini_vs_llama/` con:

```
comparaciones_gemini_vs_llama/
├── llama_Ejemplo1_20251109_140505.json       # Respuesta completa de LlamaExtract
├── gemini_Ejemplo1_20251109_140505.json      # Respuesta completa de Gemini
├── comparacion_Ejemplo1_20251109_140505.md   # Reporte de diferencias
├── llama_Ejemplo2_20251109_141020.json
├── gemini_Ejemplo2_20251109_141020.json
└── comparacion_Ejemplo2_20251109_141020.md
```

### 📄 Archivos JSON

Contienen **la respuesta completa del endpoint**, incluyendo:

```json
{
  "id": 123,
  "status": "completed",
  "message": "Invoice processed successfully",
  "data": {
    "items": [...],
    "documento": {...},
    "partes": {...},
    "fiscalidad": {...},
    "metadata": {
      "validation": {
        "validation_score": 0.80,
        "confidence_level": "medium",
        "has_validation_errors": false,
        "requires_review": false
      },
      "extraction": {
        "extraction_time": 18.5,
        "extraction_method": "llamaextract",
        "schema_type": "completo"
      },
      "gemini_retry": {
        "used": false
      }
    }
  }
}
```

**Ventajas**:
- ✅ Evidencia completa de cada extracción
- ✅ Puedes inspeccionar manualmente sin re-ejecutar
- ✅ Incluye metadata de tiempos, retry, validaciones
- ✅ Formato JSON estándar para análisis programático

### 📊 Archivo Markdown (Reporte)

El reporte `.md` compara los JSONs **campo por campo** y muestra:

1. **Scores y tiempos**: Comparación de métricas
2. **Items**: Diferencias en productos extraídos
3. **Documento**: Diferencias en tipo, número, fechas, etc.
4. **Partes**: Diferencias en empresa y cliente
5. **Fiscalidad**: Diferencias en totales, IVA, percepciones, etc.

---

## 🔍 Cómo Interpretar los Reportes

### Paso 1: Revisar el Resumen

```markdown
## 📋 Resumen

**Total de diferencias encontradas**: 8

⚠️ Se encontraron **8 diferencias** entre las extracciones. Revisa los detalles a continuación.
```

Si hay 0 diferencias = **¡Extracción idéntica!** ✅

### Paso 2: Revisar Scores

```markdown
## 🎯 Scores de Validación

| Extractor | Score | Nivel |
|-----------|-------|-------|
| LlamaExtract | 80.0% | MEDIUM |
| Gemini | 65.0% | LOW |
```

**Score más alto ≠ Necesariamente correcto**. El score es una heurística, puede tener falsos positivos/negativos.

### Paso 3: Revisar Diferencias por Sección

#### Ejemplo: Items

```markdown
## 📦 Items

### 📦 Item 1

**descripcion**
  - LlamaExtract: `COMBO HAMBURGUESA GRANDE`
  - Gemini: `COMBO HAMBURGESA GRANDE`

**precio_unitario**
  - LlamaExtract: `20082.64`
  - Gemini: `20082.00`
```

### Paso 4: Verificar con la Factura Original

1. Abre la factura original (`Ejemplo1.jpeg`)
2. Busca el campo en cuestión
3. Determina cuál extractor leyó correctamente
4. Anota patrones de errores

---

## 🎨 Cómo Usar el Sistema

### Test Completo

```bash
# Asegúrate de que el servidor Django esté corriendo
python manage.py runserver

# En otra terminal, ejecuta el test
python test_gemini_endpoint.py
```

Esto ejecutará:
1. ✅ Test de extracción completa con Gemini
2. ✅ Comparación con LlamaExtract (genera reportes)
3. ✅ Test de extracción modular

### Test Solo Comparación

Puedes llamar directamente a la función de comparación:

```python
from test_gemini_endpoint import compare_with_llamaextract

# Comparar una factura específica
compare_with_llamaextract("Ejemplo3.jpeg")
```

---

## 📊 Análisis de Diferencias Comunes

### 1. Errores de OCR

**Gemini** tiende a corregir automáticamente:
- `HAMBURGESA` → `HAMBURGUESA` ✅
- `30-53485961-8` → `30-53485961-5` (dígito verificador CUIT) ✅

**LlamaExtract** extrae lo que ve:
- Más literal, menos "inteligente"
- Mejor para documentos con calidad perfecta

### 2. Diferencias en Números

```markdown
**precio_unitario**
  - LlamaExtract: `20082.64`
  - Gemini: `20082.00`
```

**¿Cuál es correcto?** → Revisa la factura original.

Posibles causas:
- OCR leyó `.64` pero es `.00`
- Gemini redondeó incorrectamente
- Formato de moneda ambiguo

### 3. Campos Opcionales/Vacíos

```markdown
**cae**
  - LlamaExtract: `null`
  - Gemini: `null`
```

Si ambos son `null`, no es una diferencia real (el campo no existe en la factura).

### 4. Formatos de Fecha

```markdown
**fecha_emision**
  - LlamaExtract: `2025-09-09`
  - Gemini: `09/09/2025`
```

Ambos son correctos, solo formato diferente. El post-procesador debería normalizar esto.

---

## 🔧 Mejorando los Extractores

### Si Gemini falla consistentemente en algo:

1. Revisa `services_gemini_extractor.py` → `SYSTEM_INSTRUCTION_CONTADOR_COMPLETO`
2. Agrega ejemplos específicos al prompt
3. Ajusta la temperatura (actualmente 0.0)

### Si LlamaExtract falla:

1. Revisa `schemas.py` → Esquemas Pydantic
2. Ajusta descripciones de campos
3. Agrega ejemplos en los docstrings

### Si ambos fallan:

1. Problema con validaciones → `validators/`
2. Problema con normalización → `utils/normalization.py`
3. Problema con correcciones → `utils/corrections.py`

---

## 📈 Métricas para Decidir

### Cuándo usar LlamaExtract:

- ✅ Velocidad importante (5-20s)
- ✅ Facturas estándar/simples
- ✅ Mejor costo (~$0.003/factura)
- ✅ Estabilidad probada

### Cuándo usar Gemini:

- ✅ Facturas complejas/no estándar
- ✅ Necesitas corrección automática de OCR
- ✅ Layout irregular
- ✅ Backup si LlamaExtract falla

### Estrategia Híbrida (Recomendada):

1. **Default**: LlamaExtract
2. **Si score < 60%**: Retry con Gemini
3. **Facturas críticas**: Procesar con ambos, comparar, elegir el de mayor score

---

## 🚀 Próximos Pasos

1. **Analiza los reportes generados** de tus facturas reales
2. **Identifica patrones** de errores
3. **Mejora los prompts/schemas** según los patrones
4. **Re-ejecuta tests** para validar mejoras
5. **Decide qué extractor usar** en producción

---

## 💡 Tips

- Los reportes MD se pueden abrir en cualquier editor que soporte Markdown
- Los JSONs se pueden analizar con `jq`, Python, o cualquier herramienta JSON
- Usa `git diff` para comparar JSONs si quieres ver diferencias visuales
- Guarda los reportes de facturas problemáticas para análisis posterior

---

**¿Preguntas?** Revisa la documentación en:
- `API_USAGE_GUIDE.md` - Uso de los endpoints
- `IMPLEMENTACION_GEMINI_ENDPOINT.md` - Detalles técnicos del endpoint Gemini
- `PLAN_ENDPOINT_GEMINI_PURO.md` - Arquitectura y decisiones de diseño

