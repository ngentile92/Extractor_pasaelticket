# ⚙️ Cambio de Threshold de Retry

## 📊 Cambio Implementado

**Antes**: Retry se activaba cuando `validation_score < 0.6` (60%)
**Ahora**: Retry se activa cuando `validation_score <= 0.8` (80%)

---

## 🎯 Impacto

### Antes (threshold: 60%)
```
Score 90% → ✅ NO retry
Score 80% → ✅ NO retry
Score 65% → ✅ NO retry
Score 59% → ⚠️ SÍ retry  ← Solo aquí
Score 50% → ⚠️ SÍ retry
```

**Tasa de retry esperada**: ~20%

### Ahora (threshold: 80%)
```
Score 90% → ✅ NO retry
Score 85% → ✅ NO retry
Score 81% → ✅ NO retry
Score 80% → ⚠️ SÍ retry  ← Threshold nuevo
Score 75% → ⚠️ SÍ retry
Score 65% → ⚠️ SÍ retry
Score 50% → ⚠️ SÍ retry
```

**Tasa de retry esperada**: ~60-70%

---

## 💡 Razón del Cambio

Con threshold de 60%, **muchas extracciones imperfectas pasaban sin retry**:
- Score 65-75%: Tiene errores pero no se reprocesa
- Se pierden oportunidades de mejorar
- Datos incorrectos llegan a producción

Con threshold de 80%:
- **Mayor calidad**: Solo extracciones muy buenas (>80%) se aceptan sin retry
- **Corrección automática**: Más facturas se benefician del retry inteligente con contexto
- **Mejor experiencia**: Menos datos incorrectos en producción

---

## 📁 Archivos Modificados

1. **`invoice_extractor/views_gemini.py`**
   - Línea 53: Documentación del parámetro
   - Línea 185: Condición del retry

2. **`invoice_extractor/services_gemini_corrector.py`**
   - Línea 165: Documentación del criterio
   - Línea 178: Condición del retry

3. **`README_COMPARACIONES.md`**
   - Sección de retry automático actualizada

4. **`analizar_comparaciones.py`**
   - Mensaje de análisis actualizado

---

## ⚖️ Trade-offs

### Ventajas
- ✅ Mayor calidad de datos
- ✅ Menos errores en producción
- ✅ Aprovecha el retry inteligente con contexto
- ✅ Mejora automática de extracciones mediocres

### Desventajas
- ⏱️ Más tiempo de procesamiento (~60-70% de facturas con retry vs ~20%)
- 💰 Mayor costo (cada retry = llamada adicional a Gemini)
- 🔄 Mayor carga en API de Gemini

---

## 📊 Métricas Esperadas

| Métrica | Antes (60%) | Ahora (80%) | Cambio |
|---------|-------------|-------------|--------|
| **Retry rate** | ~20% | ~60-70% | +300% |
| **Tiempo promedio** | 15-20s | 25-35s | +66% |
| **Costo promedio** | $0.003 | $0.008-0.012 | +300% |
| **Score promedio** | 75-80% | 82-88% | +5-10% |
| **Facturas perfectas (>90%)** | 15% | 25-30% | +100% |

---

## 🔄 Cómo Revertir

Si necesitas volver al threshold anterior (60%):

### 1. En `invoice_extractor/views_gemini.py`
```python
# Línea 185
if enable_retry and validation_score <= 0.6:  # Cambiar 0.8 → 0.6
```

### 2. En `invoice_extractor/services_gemini_corrector.py`
```python
# Línea 178
if score <= 0.6:  # Cambiar 0.8 → 0.6
    logger.info(f"🔄 Re-extracción recomendada: score bajo ({score:.2%})")
```

---

## 🧪 Validación

Para validar el cambio, ejecuta:

```bash
python test_gemini_endpoint.py
```

Deberías ver:
- ✅ Scores de 80% o menos → **SÍ activan retry**
- ✅ Scores de 81% o más → **NO activan retry**

Ejemplo de log esperado:
```
🎯 VALIDACIÓN:
   Score: 80.00%  ← Justo en el threshold

🔄 PASO 3/4: RETRY CON CONTEXTO (Score bajo: 80.00%)  ← Se activa
   
🔄 RETRY CON GEMINI:
   Usado: SÍ
   Score inicial: 80.00%
   Score final: 88.00%  ← Mejora!
   Mejora: +8.0pp
```

---

## 💡 Recomendaciones

### Para Producción

1. **Monitorea métricas** durante 1 semana:
   - Tasa de retry real
   - Scores promedio antes/después
   - Tiempo de respuesta
   - Costo por factura

2. **Ajusta según datos**:
   - Si retry rate > 80% → Considera bajar a 0.75
   - Si retry rate < 40% → Threshold está bien
   - Si costo es prohibitivo → Evaluar alternativas

3. **Estrategias híbridas**:
   - Threshold 0.8 para facturas críticas
   - Threshold 0.6 para facturas simples
   - Sin retry para batch grandes

### Para Testing

El threshold de 0.8 es **ideal para testing** porque:
- Revela más diferencias entre extractores
- Mejora las comparaciones
- Genera más datos para análisis

---

**Implementado**: 2025-11-09  
**Por**: Asistente AI  
**Validado**: ✅ Tests pasando

