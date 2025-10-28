# 📝 Sistema de Logging Detallado - Validaciones

**Fecha**: 27 de Octubre, 2025  
**Estado**: ✅ Implementado en todos los validadores

---

## 🎯 **OBJETIVO**

Se ha agregado logging exhaustivo a todos los validadores para poder **debuguear y rastrear** cada paso del proceso de validación con lujo de detalles.

---

## 📊 **LOGS POR MÓDULO**

### 1. ✅ **CUITValidator**

**Archivo**: `invoice_extractor/validators/cuit_validator.py`

**Logs agregados**:

```
🆔 [CUITValidator] Iniciando validación de CUIT: '30-71106763-9'
   📝 [CUITValidator] CUIT normalizado: '30-71106763-9' → '30-71106763-9'
   ✅ [CUITValidator] Formato válido
   ❌ [CUITValidator] Dígito verificador incorrecto: esperado 5, encontrado 9
   💡 [CUITValidator] CUIT sugerido: 30-71106763-5
   👤 [CUITValidator] Tipo: juridica (Persona jurídica)
❌ [CUITValidator] CUIT inválido: 1 error(es)
```

**Niveles**:
- `INFO`: Inicio de validación, resultado final
- `DEBUG`: Normalización, formato válido, tipo de persona
- `WARNING`: Formato inválido, dígito verificador incorrecto
- `ERROR`: CUIT vacío, CUIT inválido

---

### 2. ✅ **ItemsValidator**

**Archivo**: `invoice_extractor/validators/items_validator.py`

**Logs agregados**:

```
📦 [ItemsValidator] Iniciando validación de 10 items
   🔧 [ItemsValidator] PASO 1: Corrigiendo cantidades negativas
   ✅ [ItemsValidator] 1 cantidad(es) negativa(s) corregida(s)
   
   🧮 [ItemsValidator] PASO 2: Validando cálculos individuales
   📦 [ItemsValidator] Validando item 'Producto A': cantidad=2.0, precio=$100.00, subtotal=$200.00
   ✅ [ItemsValidator] Todos los cálculos de items son válidos
   
   ➕ [ItemsValidator] PASO 3: Validando suma de items
   ✅ [ItemsValidator] Suma de items válida: $1000.00
   
   🔍 [ItemsValidator] PASO 4: Detectando outliers
   ✅ [ItemsValidator] Sin outliers detectados
   
✅ [ItemsValidator] Validación de items completada exitosamente
```

**Niveles**:
- `INFO`: Inicio, cantidad de items, resultados por paso, resultado final
- `DEBUG`: Detalles de cada paso, validación por item
- `WARNING`: Items con errores de cálculo, outliers detectados
- `ERROR`: Validación fallida, suma incorrecta

---

### 3. ✅ **FiscalValidatorAdvanced**

**Archivo**: `invoice_extractor/validators/fiscal_validator_advanced.py`

**Logs agregados**:

```
💰 [FiscalValidatorAdvanced] Iniciando validación fiscal avanzada
   📋 [FiscalValidatorAdvanced] Ejecutando validación base (FiscalValidator)
   ✅ [FiscalValidatorAdvanced] Validación base completada - Score: 85%
   
   🔍 [FiscalValidatorAdvanced] PASO 1: Validando discriminación de IVA
      ✅ IVA total: $210.00
   
   🧮 [FiscalValidatorAdvanced] PASO 2: Validando cálculo de total
      ✅ Total válido: $1210.00
   
   💸 [FiscalValidatorAdvanced] PASO 3: Validando percepciones y retenciones
      ✅ Percepciones: $50.00, Retenciones: $0.00
   
   🔗 [FiscalValidatorAdvanced] PASO 4: Validando consistencia de impuestos
      ✅ Consistencia fiscal OK
   
✅ [FiscalValidatorAdvanced] Validación completada - Score base: 85%, Score avanzado: 100%, Score combinado: 91%
```

**Niveles**:
- `INFO`: Inicio, resultados de validación base, resultados por paso, score final
- `DEBUG`: Cada paso de validación
- `WARNING`: Inconsistencias detectadas, warnings
- `ERROR`: Errores en IVA, total incorrecto, percepciones/retenciones inválidas

---

### 4. ✅ **MasterValidator**

**Archivo**: `invoice_extractor/validators/master_validator.py`

**Logs agregados**:

```
================================================================================
🚀 [MasterValidator] INICIANDO VALIDACIÓN MAESTRA COMPLETA
================================================================================

📋 [MasterValidator] ═══ PASO 1/5: VALIDANDO CUITs ═══
🆔 [CUITValidator] Iniciando validación de CUIT: '30-71106763-9'
   ... (logs de CUITValidator)
   Resultado: 1 error(es), 1 warning(s), 1 alerta(s)

📦 [MasterValidator] ═══ PASO 2/5: VALIDANDO ITEMS ═══
📦 [ItemsValidator] Iniciando validación de 10 items
   ... (logs de ItemsValidator)
   Resultado: 0 error(es), 2 warning(s), 1 corrección(es)

💰 [MasterValidator] ═══ PASO 3/5: VALIDANDO FISCALIDAD ═══
💰 [FiscalValidatorAdvanced] Iniciando validación fiscal avanzada
   ... (logs de FiscalValidatorAdvanced)
   Resultado: 0 error(es), 1 warning(s)

🎯 [MasterValidator] ═══ PASO 4/5: CALCULANDO SCORE DE CONFIABILIDAD ═══
   Score global: 88% (MEDIUM)
   Categorías evaluadas: 7/7
   Categorías aprobadas: 6
   Categorías fallidas: 1

💡 [MasterValidator] ═══ PASO 5/5: GENERANDO RECOMENDACIONES ═══
   3 recomendación(es) generada(s)
   1. ⚠️ Revisar campos con errores antes de procesar
   2. 🆔 Verificar CUIT de empresa en documento original
   3. 📦 Revisar cálculos de items (cantidad × precio = subtotal)

================================================================================
✅ [MasterValidator] VALIDACIÓN COMPLETADA
   ⏱️  Tiempo: 0.15s
   📊 Score: 88% (MEDIUM)
   🚨 Errores: 1
   ⚠️  Warnings: 4
   🔔 Alertas: 4
   🔧 Correcciones: 1
   📝 Recomendaciones: 3
   🔍 Revisión requerida: NO
================================================================================
```

**Niveles**:
- `INFO`: Cabeceras de pasos, resúmenes, resultado final detallado
- `DEBUG`: (delegado a sub-validadores)
- `WARNING`: (delegado a sub-validadores)
- `ERROR`: (delegado a sub-validadores)

---

## 🎨 **FORMATO DE LOGS**

### Emojis por Validador:
- `🆔` CUITValidator
- `📦` ItemsValidator  
- `💰` FiscalValidatorAdvanced
- `🎯` ConfidenceScorer
- `🚀` MasterValidator (inicio)
- `✅` Éxito
- `❌` Error
- `⚠️` Warning
- `📝` Información
- `🔧` Corrección
- `💡` Sugerencia

### Prefijos por Nivel:
- `INFO`: Sin prefijo especial, mensajes importantes
- `DEBUG`: Indentados con espacios `   `
- `WARNING`: Con emoji `⚠️`
- `ERROR`: Con emoji `❌`

---

## 📋 **EJEMPLO DE OUTPUT COMPLETO**

Cuando proceses una factura, verás un log completo como este:

```
================================================================================
🚀 [MasterValidator] INICIANDO VALIDACIÓN MAESTRA COMPLETA
================================================================================

📋 [MasterValidator] ═══ PASO 1/5: VALIDANDO CUITs ═══
🆔 [CUITValidator] Iniciando validación de CUIT: '30-52539008-5'
   📝 [CUITValidator] CUIT normalizado: '30-52539008-5' → '30-52539008-5'
   ✅ [CUITValidator] Formato válido
   ✅ [CUITValidator] Dígito verificador correcto: 5
   👤 [CUITValidator] Tipo: juridica (Persona jurídica)
✅ [CUITValidator] CUIT válido: 30-52539008-5

🆔 [CUITValidator] Iniciando validación de CUIT: None
❌ [CUITValidator] CUIT vacío o None
   Resultado: 1 error(es), 0 warning(s), 1 alerta(s)

📦 [MasterValidator] ═══ PASO 2/5: VALIDANDO ITEMS ═══
📦 [ItemsValidator] Iniciando validación de 12 items
   🔧 [ItemsValidator] PASO 1: Corrigiendo cantidades negativas
   ✅ [ItemsValidator] 1 cantidad(es) negativa(s) corregida(s)
   🧮 [ItemsValidator] PASO 2: Validando cálculos individuales
   📦 [ItemsValidator] Validando item 'MONSTER GREEN': cantidad=2.0, precio=$8096.12, subtotal=$16192.24
   📦 [ItemsValidator] Validando item '100972': cantidad=8.0, precio=$3747.15, subtotal=$29977.20
   ... (más items)
   ✅ [ItemsValidator] Todos los cálculos de items son válidos
   ➕ [ItemsValidator] PASO 3: Validando suma de items
   ✅ [ItemsValidator] Suma de items válida: $186824.69
   🔍 [ItemsValidator] PASO 4: Detectando outliers
   ✅ [ItemsValidator] Sin outliers detectados
✅ [ItemsValidator] Validación de items completada exitosamente
   Resultado: 0 error(es), 0 warning(s), 1 corrección(es)

💰 [MasterValidator] ═══ PASO 3/5: VALIDANDO FISCALIDAD ═══
💰 [FiscalValidatorAdvanced] Iniciando validación fiscal avanzada
   📋 [FiscalValidatorAdvanced] Ejecutando validación base (FiscalValidator)
   ✅ [FiscalValidatorAdvanced] Validación base completada - Score: 85%
   🔍 [FiscalValidatorAdvanced] PASO 1: Validando discriminación de IVA
      ✅ IVA total: $31956.48
   🧮 [FiscalValidatorAdvanced] PASO 2: Validando cálculo de total
      ❌ Total incorrecto: calculado $220211.84 vs declarado $193591.03 (diff: $26620.81)
   💸 [FiscalValidatorAdvanced] PASO 3: Validando percepciones y retenciones
      ✅ Percepciones: $8081.72, Retenciones: $0.00
   🔗 [FiscalValidatorAdvanced] PASO 4: Validando consistencia de impuestos
      ✅ Consistencia fiscal OK
✅ [FiscalValidatorAdvanced] Validación completada - Score base: 85%, Score avanzado: 75%, Score combinado: 81%
❌ [FiscalValidatorAdvanced] 1 error(es) totales
   Resultado: 1 error(es), 2 warning(s)

🎯 [MasterValidator] ═══ PASO 4/5: CALCULANDO SCORE DE CONFIABILIDAD ═══
   Score global: 72% (LOW)
   Categorías evaluadas: 7/7
   Categorías aprobadas: 5
   Categorías fallidas: 2

💡 [MasterValidator] ═══ PASO 5/5: GENERANDO RECOMENDACIONES ═══
   4 recomendación(es) generada(s)
   1. ⚠️ Revisar campos con errores antes de procesar
   2. 🆔 Verificar CUIT de cliente en documento original
   3. 🧮 Revisar cálculo de total (subtotal + IVA + percepciones - retenciones)
   4. 📦 1 item(s) con cantidad negativa corregidos automáticamente

================================================================================
✅ [MasterValidator] VALIDACIÓN COMPLETADA
   ⏱️  Tiempo: 0.18s
   📊 Score: 72% (LOW)
   🚨 Errores: 2
   ⚠️  Warnings: 2
   🔔 Alertas: 3
   🔧 Correcciones: 1
   📝 Recomendaciones: 4
   🔍 Revisión requerida: SÍ
================================================================================
```

---

## 🔧 **CONFIGURACIÓN DE LOGGING**

Para ver todos estos logs, asegúrate de tener configurado el logging en Django:

### En `settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/validation.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'invoice_extractor.validators': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',  # Cambiar a INFO en producción
            'propagate': False,
        },
    },
}
```

### Para ver solo logs importantes (producción):
```python
'level': 'INFO',  # Solo INFO, WARNING, ERROR
```

### Para debugging completo (desarrollo):
```python
'level': 'DEBUG',  # Incluye todos los detalles
```

---

## 📊 **RESUMEN**

| Módulo | Logs Agregados | Niveles Usados |
|--------|----------------|----------------|
| CUITValidator | 8+ mensajes | INFO, DEBUG, WARNING, ERROR |
| ItemsValidator | 15+ mensajes | INFO, DEBUG, WARNING, ERROR |
| FiscalValidatorAdvanced | 12+ mensajes | INFO, DEBUG, WARNING, ERROR |
| MasterValidator | 25+ mensajes | INFO |
| **TOTAL** | **60+ mensajes** | **Todos** |

---

## ✅ **BENEFICIOS**

1. ✅ **Debugging fácil**: Ver exactamente dónde falla una validación
2. ✅ **Trazabilidad**: Seguir el flujo completo de validación
3. ✅ **Métricas**: Tiempos de procesamiento por paso
4. ✅ **Auditoría**: Log completo de cada factura procesada
5. ✅ **Desarrollo**: Entender comportamiento del sistema
6. ✅ **Producción**: Detectar problemas rápidamente

---

## 🚀 **USO**

Ahora cuando proceses una factura con:

```bash
curl -X POST http://localhost:8000/api/invoices/process/ \
  -F "document=@Ejemplo2.jpeg"
```

Verás en la consola del servidor un log completo con todos los detalles del proceso de validación.

**¡El sistema de logging está listo para producción!** 🎉

