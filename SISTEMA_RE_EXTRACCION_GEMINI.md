# 🤖 Sistema de Re-extracción Inteligente con Gemini 2.5 Flash

**Fecha**: 27 de Octubre, 2025  
**Estado**: ✅ IMPLEMENTADO Y LISTO

---

## 🎯 **OBJETIVO**

Cuando la primera extracción (LlamaExtract) tiene errores matemáticos significativos, el sistema **automáticamente** re-intenta la extracción usando **Google Gemini 2.5 Flash** con contexto específico de los errores detectados, mejorando la precisión final.

---

## 🚀 **FLUJO AUTOMÁTICO**

```
┌─────────────────────────────────────────────────┐
│ 1. Usuario sube factura                         │
│    POST /api/invoices/upload/                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ 2. EXTRACCIÓN INICIAL (LlamaExtract)            │
│    • Schema optimizado                          │
│    • Instrucciones detalladas                   │
│    • Extracción completa                        │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│ 3. POST-PROCESAMIENTO (1ra vez)                 │
│    • Normalización de datos                     │
│    • Correcciones automáticas:                  │
│      - CUITs (con checksum)                     │
│      - Fechas → DD/MM/YYYY                      │
│      - Items (descripción vs precio)            │
│      - Unidades de medida (outliers)            │
│    • Validaciones (CUIT, Items, Fiscal)         │
│    • Cálculo de score                           │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
            ┌──────────────┐
            │ Score < 60%  │    ❓ DECISIÓN AUTOMÁTICA
            │ O >= 3 errors│
            │ O >= 2 math  │
            └──┬───────┬───┘
         NO    │       │    SÍ
               │       │
    ┌──────────┘       └─────────────────┐
    │                                     │
    ▼                                     ▼
┌─────────────────┐    ┌────────────────────────────────────┐
│ 4a. RETORNAR    │    │ 4b. 🤖 RE-EXTRACCIÓN CON GEMINI    │
│     RESULTADO   │    │                                     │
│     ✅ OK        │    │  • Sube factura a Gemini File API  │
└─────────────────┘    │  • Genera prompt con errores       │
                       │  • System instruction: Contador ARG│
                       │  • Schema estructurado (Pydantic)  │
                       │  • Extrae items + fiscalidad       │
                       └──────────────┬─────────────────────┘
                                      │
                                      ▼
                       ┌────────────────────────────────────┐
                       │ 5. POST-PROCESAMIENTO (2da vez)    │
                       │    • Procesar nueva extracción     │
                       │    • Calcular nuevo score          │
                       └──────────────┬─────────────────────┘
                                      │
                                      ▼
                       ┌────────────────────────────────────┐
                       │ 6. ⚖️ COMPARAR RESULTADOS           │
                       │    • LlamaExtract: Score X%        │
                       │    • Gemini: Score Y%              │
                       │    • Elegir LA MEJOR               │
                       └──────────────┬─────────────────────┘
                                      │
                                      ▼
                       ┌────────────────────────────────────┐
                       │ 7. RETORNAR GANADOR                │
                       │    • Metadata incluye comparación  │
                       │    • Log completo de decisión      │
                       └────────────────────────────────────┘
```

---

## 🔧 **COMPONENTES IMPLEMENTADOS**

### 1. **GeminiCorrector** (`services_gemini_corrector.py`)

```python
class GeminiCorrector:
    """
    Corrector inteligente usando Gemini 2.5 Flash
    """
    
    def __init__(self):
        # Inicializa con:
        # - API Key de Google (GOOGLE_API_KEY env var)
        # - Service Account (GOOGLE_APPLICATION_CREDENTIALS)
        # - Application Default Credentials (ADC)
        pass
    
    def should_retry_extraction(self, validation_result):
        """
        Decide si vale la pena re-extraer:
        ✅ Score < 60%
        ✅ >= 3 errores totales
        ✅ >= 2 errores matemáticos
        """
        pass
    
    def build_correction_prompt(self, original_data, validation_result):
        """
        Genera prompt enriquecido con contexto:
        • Lista de errores detectados
        • Instrucciones específicas según tipo de error
        • Énfasis en precisión matemática
        """
        pass
    
    def retry_extraction_with_gemini(self, file_path, original_data, validation_result):
        """
        Re-extrae usando Gemini 2.5 Flash:
        • Sube documento a File API
        • Genera prompt con errores
        • Usa schema Pydantic estructurado
        • Retorna items + fiscalidad corregidos
        """
        pass
```

### 2. **InvoicePostProcessor** (actualizado)

```python
class InvoicePostProcessor:
    def __init__(self, enable_gemini_retry=True):
        """Inicializa con GeminiCorrector habilitado"""
        if enable_gemini_retry:
            self.gemini_corrector = GeminiCorrector()
    
    def process_with_gemini_retry(self, extracted_data, file_path):
        """
        Flujo completo:
        1. Procesar LlamaExtract
        2. Evaluar score
        3. Re-extraer con Gemini si es necesario
        4. Comparar y elegir mejor
        """
        pass
```

### 3. **Views** (Django API - actualizado)

```python
def upload(self, request):
    # ...
    processor = InvoicePostProcessor(enable_gemini_retry=True)
    result = processor.process_with_gemini_retry(
        extracted_data=extracted,
        file_path=file_path  # ✅ Path disponible para Gemini
    )
    # ...
```

---

## 📋 **EJEMPLO DE PROMPT ENRIQUECIDO**

Cuando Gemini re-extrae, recibe este contexto:

```
🚨 ATENCIÓN: La extracción automática anterior tuvo ERRORES MATEMÁTICOS.

📋 ERRORES DETECTADOS EN LA PRIMERA EXTRACCIÓN:
  1. Subtotal incorrecto: cantidad (8.0) × precio ($6598.35) = $52786.80, pero declarado $39590.10 (diff: $13196.70, 33.33%)
  2. Subtotal incorrecto: cantidad (6.0) × precio ($6837.02) = $41022.12, pero declarado $27318.08 (diff: $13704.04, 50.16%)
  3. Suma de items no coincide: suma $144308.97 vs total declarado $152173.71 (diff: $7864.74, 5.17%)

============================================================
📸 NUEVA EXTRACCIÓN - INSTRUCCIONES CRÍTICAS:
============================================================

🔍 TABLA DE ITEMS:
1. Revisa CUIDADOSAMENTE cada FILA de la tabla de items
2. Cada FILA = UN item (NO dupliques items)
3. Para CADA item verifica: cantidad × precio_unitario = subtotal
4. NO pongas precios en 'descripcion' - solo texto descriptivo
5. NO pongas descripciones largas en 'codigo' - solo códigos cortos
6. Si un código o precio no está claro, déjalo vacío (null) - NO ADIVINES

💰 CÁLCULOS FISCALES:
7. Verifica que la SUMA de todos los subtotals = subtotal_gravado
8. Calcula correctamente: subtotal_gravado + IVA + percepciones = importe_total
9. Lee TODOS los impuestos del pie de factura (IVA, IIBB, Imp. Internos)

⚠️ ERRORES COMUNES A EVITAR:
  ❌ Verifica CADA multiplicación: cantidad × precio = subtotal
  ❌ Suma TODOS los items (no dejes ninguno fuera)

✅ EXTRAE NUEVAMENTE con EXTREMA PRECISIÓN en los cálculos matemáticos.
✅ Si un campo no es legible, déjalo vacío (null) - NUNCA inventes datos.
```

---

## 🔐 **CONFIGURACIÓN REQUERIDA**

### Opción A: API Key (más simple)

```bash
# .env
GOOGLE_API_KEY=AIzaSy...
```

### Opción B: Service Account (recomendado para producción)

```bash
# .env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account-key.json
```

El sistema intentará ambos métodos automáticamente.

---

## 📊 **EJEMPLO DE SALIDA**

### Caso con Re-extracción:

```json
{
  "id": 25,
  "status": "completed",
  "data": {
    "raw_extraction": {
      "processing_metadata": {
        "gemini_retry": {
          "was_retried": true,
          "first_score": 0.45,
          "second_score": 0.89,
          "improvement": 44.0,
          "method_used": "gemini"
        }
      }
    },
    "validation_score": "0.8900"
  }
}
```

### Log en consola:

```
================================================================================
🎯 PROCESAMIENTO INICIAL (LlamaExtract)
================================================================================
📊 Score inicial: 45%
❌ Errores iniciales: 9

================================================================================
🔄 RE-EXTRACCIÓN CON GEMINI (errores matemáticos detectados)
================================================================================
📤 Subiendo JPEG con File API: Ejemplo2.jpeg
✅ Archivo subido y cached: a3f5b2c1... (JPEG)
📝 Prompt de corrección generado (1247 chars)
🚀 Llamando a Gemini 2.5 Flash con schema estructurado...
✅ Gemini extrajo 10 items correctamente
🎉 RE-EXTRACCIÓN COMPLETADA CON GEMINI

================================================================================
🎯 PROCESAMIENTO DE EXTRACCIÓN GEMINI
================================================================================
📊 Score con Gemini: 89%
❌ Errores con Gemini: 2

================================================================================
⚖️ COMPARACIÓN DE RESULTADOS
================================================================================
   LlamaExtract: 45% (9 errores)
   Gemini:       89% (2 errores)
✅ GEMINI GANÓ! Mejora: +44.0pp
================================================================================
```

---

## ⚡ **VENTAJAS**

### 1. **Automático**
- No requiere intervención manual
- Decisión inteligente basada en métricas

### 2. **Transparente**
- Log completo de decisiones
- Metadata incluye comparación
- Ambos resultados disponibles

### 3. **Económico**
- Solo re-extrae cuando es necesario (score < 60%)
- Gemini 2.5 Flash es muy económico

### 4. **Robusto**
- Fallback a LlamaExtract si Gemini falla
- Cache de archivos subidos
- Manejo de errores completo

---

## 🎯 **CRITERIOS DE RE-EXTRACCIÓN**

El sistema re-extrae automáticamente si:

1. **Score de confiabilidad < 60%**
2. **≥ 3 errores de validación**
3. **≥ 2 errores matemáticos** (subtotales, sumas, totales incorrectos)

---

## 🧪 **TESTING**

### Test simple:

```bash
# Subir una factura con errores matemáticos
curl -X POST http://localhost:8000/api/invoices/upload/ \
  -F "document=@Ejemplo2.jpeg"

# Revisar el log en consola del servidor
# Buscar: "🔄 RE-EXTRACCIÓN CON GEMINI"
```

### Test con archivo problemático conocido:

```python
# Usar Ejemplo2.jpeg (que tiene errores matemáticos conocidos)
# El sistema debería:
# 1. Extraer con LlamaExtract (score ~45%)
# 2. Detectar errores
# 3. Re-extraer con Gemini (score ~85%)
# 4. Elegir Gemini
```

---

## 📈 **MÉTRICAS ESPERADAS**

### Sin re-extracción (antes):
```
Factura compleja con errores:
- Score: 45%
- Errores: 9
- Tiempo: 15s
```

### Con re-extracción Gemini (ahora):
```
Factura compleja con errores:
- Score inicial (LlamaExtract): 45%
- Score final (Gemini): 89%
- Mejora: +44pp
- Tiempo total: ~25s (extra 10s por Gemini)
```

---

## 🚀 **ESTADO ACTUAL**

### ✅ Completamente implementado:

1. **GeminiCorrector** con:
   - Autenticación (API Key / Service Account / ADC)
   - Upload con cache
   - Prompt enriquecido con errores
   - System instruction optimizada
   - Schema estructurado (Pydantic)

2. **InvoicePostProcessor** con:
   - Método `process_with_gemini_retry`
   - Comparación automática
   - Selección del mejor resultado
   - Metadata completa

3. **Views** actualizadas para:
   - Pasar `file_path` a post-processor
   - Habilitar Gemini retry por defecto

4. **Correcciones automáticas**:
   - ✅ CUITs con checksum
   - ✅ Fechas a formato DD/MM/YYYY
   - ✅ Items (códigos vs descripciones)
   - ✅ Unidades de medida (outliers)

---

## 💡 **PRÓXIMOS PASOS (OPCIONAL)**

1. **A/B Testing**:
   - Medir precisión promedio LlamaExtract vs Gemini
   - Optimizar umbral de re-extracción (actualmente 60%)

2. **Dashboard**:
   - Métricas de re-extracción en admin Django
   - % de facturas que necesitaron Gemini
   - Mejora promedio en score

3. **Costo optimization**:
   - Monitorear costos Gemini
   - Ajustar criterios de re-extracción según ROI

---

## 🎉 **CONCLUSIÓN**

El sistema ahora tiene un **mecanismo automático de auto-corrección inteligente**:

1. **Primera línea de defensa**: LlamaExtract (rápido, especializado)
2. **Segunda línea (cuando falla)**: Gemini 2.5 Flash (contexto de errores, más preciso)
3. **Decisión automática**: Siempre elige el mejor resultado

**El usuario recibe el mejor resultado posible sin intervención manual.** ✅

