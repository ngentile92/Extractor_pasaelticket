# 🤖 Plan de Extracción Multi-LLM con Validación Cruzada

**Fecha:** 2024-11-21  
**Estado:** PROPUESTA  
**Prioridad:** Alta

---

## 📋 Objetivo Principal

Implementar un sistema de extracción que:
1. **Extraiga sectores específicos** con LLMs especializados
2. **Chequee errores** con warnings claros y concisos
3. **Compare LlamaExtract vs Gemini** para elegir el mejor resultado
4. **Sea modular** y fácil de mantener

---

## 📊 Análisis: LlamaExtract vs Gemini

### Resultados del Test Actual (2024-11-21)

| Ejemplo | LlamaExtract | Gemini | Ganador | Diferencia |
|---------|--------------|--------|---------|------------|
| Ejemplo1.jpeg | 65% | 80% | **Gemini** | +15pp |
| Ejemplo2.jpeg | 65% | 85% | **Gemini** | +20pp |
| Ejemplo3.jpeg | 65% | 80% | **Gemini** | +15pp |

### Tiempos de Extracción

| Ejemplo | LlamaExtract | Gemini | Más Rápido |
|---------|--------------|--------|------------|
| Ejemplo1.jpeg | 36.6s | 27.6s | **Gemini** (-25%) |
| Ejemplo2.jpeg | 66.0s | 102.5s | LlamaExtract (-35%) |
| Ejemplo3.jpeg | 36.3s | 25.0s | **Gemini** (-31%) |

### Conclusión
- **Gemini** tiene mejor score en todos los casos (+15-20pp)
- **Gemini** es más rápido en facturas simples
- **LlamaExtract** es más rápido en facturas complejas
- **Gemini** debería ser el extractor principal

---

## 🎯 Arquitectura Propuesta: Multi-LLM con Especialización

### Concepto: División por Sectores

En lugar de un LLM que extraiga TODO, usar LLMs especializados:

```
┌─────────────────────────────────────────────────────────────────┐
│                         FACTURA                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  LLM-PARTES     │ │  LLM-ITEMS      │ │  LLM-FISCAL     │
│                 │ │                 │ │                 │
│ • Empresa       │ │ • Tabla items   │ │ • Totales       │
│ • Cliente       │ │ • Códigos       │ │ • IVA           │
│ • CUITs         │ │ • Descripciones │ │ • Percepciones  │
│ • Domicilios    │ │ • Cantidades    │ │ • Retenciones   │
│ • Condición IVA │ │ • Precios       │ │ • Cálculos      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM-VALIDADOR                                 │
│                                                                  │
│  • Verifica consistencia entre secciones                        │
│  • Calcula: Σ items == subtotal_gravado?                        │
│  • Calcula: subtotal + IVA + perc == total?                     │
│  • Genera warnings específicos y claros                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESULTADO FINAL                               │
│  { data, warnings, validation_score }                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementación Propuesta

### Opción A: Extracción Paralela (Recomendada)

```python
# core/extractors/multi_llm.py

class MultiLLMExtractor:
    """
    Extractor que usa múltiples LLMs en paralelo para diferentes secciones.
    """
    
    def __init__(self):
        self.gemini = GeminiExtractor()
        # En el futuro: self.llama = LlamaExtractor()
    
    async def extract_parallel(self, file_path: str) -> Dict[str, Any]:
        """
        Extrae todas las secciones en paralelo.
        
        Beneficios:
        - Menor tiempo total (paralelo vs secuencial)
        - Cada LLM se especializa en una sección
        - Prompts más cortos y enfocados = mejor precisión
        """
        import asyncio
        
        # Lanzar extracciones en paralelo
        tasks = [
            self._extract_section(file_path, 'partes'),
            self._extract_section(file_path, 'items'),
            self._extract_section(file_path, 'documento'),
            self._extract_section(file_path, 'fiscalidad'),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combinar resultados
        combined = self._merge_sections(results)
        
        # Validar consistencia cruzada
        validation = self._validate_cross_section(combined)
        
        return {
            'data': combined,
            'validation': validation,
            'warnings': validation['warnings']
        }
    
    async def _extract_section(
        self, 
        file_path: str, 
        section: str
    ) -> Dict[str, Any]:
        """
        Extrae una sección específica con prompt especializado.
        """
        # Prompts especializados por sección
        prompts = {
            'partes': PROMPT_PARTES,      # Enfocado en CUIT, razón social, etc.
            'items': PROMPT_ITEMS,         # Enfocado en tabla de items
            'documento': PROMPT_DOCUMENTO, # Enfocado en CAE, número, fechas
            'fiscalidad': PROMPT_FISCAL,   # Enfocado en totales e impuestos
        }
        
        return await self.gemini.extract_section(
            file_path=file_path,
            section=section,
            prompt=prompts[section]
        )
```

### Opción B: Extracción + Verificación (Más Robusta)

```python
# core/extractors/verified_extractor.py

class VerifiedExtractor:
    """
    Extractor que usa un LLM para extraer y otro para verificar.
    """
    
    def __init__(self):
        self.extractor = GeminiExtractor()
        self.verifier = GeminiExtractor()  # Mismo modelo, diferente prompt
    
    def extract_and_verify(self, file_path: str) -> Dict[str, Any]:
        """
        Flujo:
        1. Extractor: Extrae todos los datos
        2. Verifier: Revisa los datos y genera warnings
        3. Si hay errores graves: Re-extraer sección problemática
        """
        # PASO 1: Extracción inicial
        extracted = self.extractor.extract(file_path)
        
        # PASO 2: Verificación con otro prompt
        verification = self.verifier.verify(
            file_path=file_path,
            extracted_data=extracted['data']
        )
        
        # PASO 3: Si hay errores, re-extraer
        if verification['has_critical_errors']:
            for section in verification['sections_to_retry']:
                retry_result = self.extractor.extract_section(
                    file_path=file_path,
                    section=section,
                    context=verification['error_context']
                )
                extracted['data'][section] = retry_result
        
        return {
            'data': extracted['data'],
            'warnings': verification['warnings'],
            'validation_score': verification['score']
        }
```

---

## 📝 Prompts Especializados por Sección

### PROMPT_PARTES (Empresa y Cliente)
```
Eres un experto en datos fiscales argentinos.

TU ÚNICA TAREA: Extraer datos de EMPRESA (emisor) y CLIENTE (receptor).

⚠️ ATENCIÓN ESPECIAL AL CUIT:
- Formato: XX-XXXXXXXX-X (11 dígitos)
- El último dígito es verificador
- Si ves "8" o "9" al final, revisa con cuidado (OCR confunde frecuentemente)

CAMPOS A EXTRAER:

EMPRESA (emisor):
- razon_social: nombre legal completo
- cuit: formato XX-XXXXXXXX-X
- condicion_iva: RESPONSABLE INSCRIPTO / MONOTRIBUTO / EXENTO
- domicilio: dirección completa
- provincia: provincia argentina

CLIENTE (receptor):
- razon_social: nombre o "CONSUMIDOR FINAL" si no hay nombre
- cuit: formato XX-XXXXXXXX-X o null si consumidor final
- condicion_iva: condición del cliente
- domicilio: si está disponible

NO EXTRAER: items, totales, impuestos, CAE, fechas.
```

### PROMPT_ITEMS (Tabla de Productos)
```
Eres un experto en lectura de tablas de facturas.

TU ÚNICA TAREA: Extraer la tabla de ITEMS/PRODUCTOS.

📋 ESTRATEGIA DE LECTURA:
1. Identifica los ENCABEZADOS de columnas
2. Lee FILA POR FILA (no columna por columna)
3. Para CADA fila, extrae en orden:
   - codigo (corto, alfanumérico)
   - descripcion (texto descriptivo)
   - cantidad (número positivo)
   - unidad_medida (UN, CJ, KG, etc.)
   - precio_unitario (precio por unidad)
   - subtotal (cantidad × precio)

⚠️ VERIFICACIÓN CRÍTICA:
Para CADA item verifica: cantidad × precio_unitario = subtotal
Si no coincide, REVISA la fila antes de continuar.

❌ NO HAGAS:
- No mezcles datos de diferentes filas
- No dupliques items
- No pongas precios en descripción
- No inventes datos si no son legibles

NO EXTRAER: datos de empresa, cliente, totales generales, IVA.
```

### PROMPT_FISCAL (Totales e Impuestos)
```
Eres un contador argentino especializado en impuestos.

TU ÚNICA TAREA: Extraer TOTALES e IMPUESTOS de la factura.

📊 CAMPOS A EXTRAER:

TOTALES:
- subtotal_gravado: suma de items antes de impuestos
- descuentos: descuentos aplicados (0 si no hay)
- importe_total: total final a pagar

IMPUESTOS:
- iva_21: monto del IVA 21%
- iva_105: monto del IVA 10.5%
- iva_27: monto del IVA 27%
- percepcion_iibb: percepciones de ingresos brutos
- percepcion_iva: percepciones de IVA
- retencion_iva: retenciones de IVA (si hay)
- retencion_ganancias: retenciones de ganancias (si hay)
- impuestos_internos: impuestos internos (si hay)

⚠️ VALIDACIONES:
1. subtotal + IVA + percepciones - retenciones = importe_total
2. Alícuotas válidas: 0%, 2.5%, 5%, 10.5%, 21%, 27%
3. Si leíste 105% → es 10.5% (error de decimal)

NO EXTRAER: items individuales, datos de empresa/cliente.
```

---

## 🔍 Sistema de Warnings Claros

### Estructura de Warning

```python
@dataclass
class ExtractionWarning:
    level: Literal['info', 'warning', 'error', 'critical']
    category: str          # 'cuit', 'item', 'fiscal', 'total'
    field: str             # 'partes.empresa.cuit'
    message: str           # Mensaje claro y conciso
    expected: Any          # Valor esperado (si aplica)
    got: Any               # Valor obtenido
    suggestion: str        # Qué hacer para corregir
    can_auto_fix: bool     # Si se puede corregir automáticamente
```

### Ejemplos de Warnings Claros

```json
{
  "level": "error",
  "category": "item",
  "field": "items[3].subtotal",
  "message": "Subtotal incorrecto: 2 × $1500.00 ≠ $2800.00",
  "expected": 3000.00,
  "got": 2800.00,
  "suggestion": "Verificar cantidad o precio unitario del item",
  "can_auto_fix": true
}
```

```json
{
  "level": "warning",
  "category": "cuit",
  "field": "partes.empresa.cuit",
  "message": "CUIT termina en 9 - verificar último dígito (OCR confunde frecuentemente)",
  "expected": null,
  "got": "30-71234567-9",
  "suggestion": "Revisar visualmente el último dígito en la factura",
  "can_auto_fix": false
}
```

```json
{
  "level": "critical",
  "category": "total",
  "field": "fiscalidad.totales.importe_total",
  "message": "Total calculado ($25000.00) no coincide con declarado ($28000.00)",
  "expected": 25000.00,
  "got": 28000.00,
  "suggestion": "Revisar discriminación de impuestos o subtotal",
  "can_auto_fix": false
}
```

---

## 🏗️ Estructura de Archivos Propuesta

```
invoice_extractor/
├── core/
│   ├── extractors/
│   │   ├── base.py                 # Interfaz común
│   │   ├── gemini.py               # Gemini extractor
│   │   ├── llama.py                # LlamaExtract (fallback)
│   │   └── multi_llm.py            # 🆕 Multi-LLM coordinator
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── partes.py               # 🆕 Prompt especializado
│   │   ├── items.py                # 🆕 Prompt especializado
│   │   ├── documento.py            # 🆕 Prompt especializado
│   │   └── fiscal.py               # 🆕 Prompt especializado
│   │
│   ├── validators/
│   │   ├── cross_section.py        # 🆕 Validación cruzada
│   │   └── warnings_generator.py   # 🆕 Generador de warnings
│   │
│   └── schemas/
│       ├── invoice.py              # Schema completo
│       └── warnings.py             # 🆕 Schema de warnings
```

---

## 📊 Comparación de Enfoques

| Enfoque | Precisión | Velocidad | Complejidad | Costo |
|---------|-----------|-----------|-------------|-------|
| Un solo LLM (actual) | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐ |
| Multi-LLM Paralelo | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Extractor + Verificador | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### Recomendación

**Empezar con "Un solo LLM mejorado"** (Gemini con prompts especializados) y luego evolucionar a "Extractor + Verificador" si se necesita mayor precisión.

---

## 🎯 Plan de Implementación

### FASE 1: Prompts Especializados (3 días)

1. Crear directorio `core/prompts/`
2. Separar prompts actuales en archivos especializados
3. Testear cada prompt por separado
4. Medir mejora en score

### FASE 2: Warnings Mejorados (2 días)

1. Crear `warnings.py` con estructura clara
2. Actualizar validadores para generar warnings estructurados
3. Agregar campo `warnings` a respuesta de API
4. Testear con ejemplos reales

### FASE 3: Extracción por Secciones (3 días)

1. Agregar endpoint `/api/invoices/extract-section/`
2. Implementar extracción modular
3. Implementar combinación de secciones
4. Testear con ejemplos reales

### FASE 4: Verificador (Opcional, 4 días)

1. Crear prompt de verificación
2. Implementar flujo de verificación
3. Implementar re-extracción de secciones problemáticas
4. Testear y medir mejora

---

## 📈 Métricas de Éxito

| Métrica | Actual | Objetivo |
|---------|--------|----------|
| Score promedio | 80% | 90%+ |
| Errores de CUIT | ~10% | <2% |
| Errores de subtotales | ~15% | <5% |
| Warnings claros | No | Sí |
| Tiempo por factura simple | 25-30s | 20s |

---

## 🔗 Próximos Pasos

1. **Aprobar** este plan
2. **Implementar FASE 1** (prompts especializados)
3. **Medir** mejora en score
4. **Decidir** si proceder con FASE 2-4

