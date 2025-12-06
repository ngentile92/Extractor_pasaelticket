# 🔄 Plan de Refactorización - Extractor de Facturas

**Fecha:** 2024-11-21  
**Estado:** PROPUESTA  
**Prioridad:** Alta

---

## 📊 Resumen Ejecutivo

El repositorio actual presenta **alta complejidad**, **código duplicado**, y **flujos de extracción confusos**. Este plan propone una arquitectura limpia, modular y mantenible.

### Métricas Actuales
| Métrica | Valor |
|---------|-------|
| Archivos Python | ~35 |
| Archivos .md documentación | ~30+ (muchos obsoletos) |
| Servicios de extracción | 4 (LlamaExtract, GeminiExtractor, GeminiCorrector, Orchestrator) |
| Validadores | 8 archivos separados |
| Schemas duplicados | 2 conjuntos (schemas.py + services_gemini_corrector.py) |
| Líneas duplicadas estimadas | ~500+ |

---

## 🚨 Problemas Identificados

### 1. DUPLICACIÓN DE CÓDIGO (Crítico)

#### 1.1 Función `retry_with_exponential_backoff` duplicada
**Ubicaciones:**
- `services_gemini_extractor.py` (líneas 47-119)
- `services_gemini_corrector.py` (líneas 34-106)

**Impacto:** Mantenimiento duplicado, bugs inconsistentes

#### 1.2 Lógica de autenticación Gemini duplicada
**Ubicaciones:**
- `GeminiExtractor._init_genai_client()` (services_gemini_extractor.py)
- `GeminiCorrector._init_genai_client()` (services_gemini_corrector.py)

**Impacto:** 80+ líneas duplicadas

#### 1.3 Mapeo de campos Invoice en views
**Ubicaciones:**
- `views.py` líneas 283-406 (mapeo de documento, partes, fiscalidad)
- `views_gemini.py` líneas 377-500 (exactamente el mismo código)

**Impacto:** 200+ líneas duplicadas

#### 1.4 Schemas Pydantic duplicados
**Ubicaciones:**
- `schemas.py`: ComprobanteArgentino, InvoiceItem, Fiscalidad, etc.
- `services_gemini_corrector.py`: GeminiInvoiceItem, GeminiInvoiceFiscalidad, GeminiInvoiceComplete

**Impacto:** Definiciones inconsistentes, mantenimiento duplicado

---

### 2. COMPLEJIDAD INNECESARIA (Alto)

#### 2.1 Orchestrator "Inteligente" que siempre usa estrategia SIMPLE
```python
# intelligent_orchestrator.py línea 299
# NUEVO: Defaultear a SIMPLE (mejor calidad y más rápido)
self._log_decision("   → Clasificación: SIMPLE (extracción completa en una pasada)")
return 'simple'
```
**Problema:** El orchestrator tiene 650+ líneas de código para estrategias "progresivas" que NUNCA se usan porque siempre retorna 'simple'.

#### 2.2 Sistema de Inferencia Fiscal
- `fiscal_logic_inferencer.py` - inferencia de lógica contable
- `adaptive_fiscal_validator.py` - validación adaptativa

**Problema:** No hay evidencia de que mejoren el score. Añaden complejidad.

#### 2.3 Doble validación fiscal
- `fiscal_validator.py` - validador base
- `fiscal_validator_advanced.py` - validador "avanzado" que hereda del base

**Problema:** Herencia confusa, no está claro cuándo usar cada uno.

---

### 3. ARCHIVOS OBSOLETOS (Medio)

#### 3.1 Documentación .md redundante
```
ARQUITECTURA_MODULAR.md
CAMBIOS_IMPLEMENTADOS.md
CAMBIOS_RETRY_THRESHOLD.md
COMPARACION_ESTRUCTURAS_KEYS.md
ESTADO_SISTEMA_INTELIGENTE.md
ESTADO_VALIDACIONES.md
FIXES_ORCHESTRATOR.md
FIXES_QUICK_SCAN.md
GEMINI_INTELIGENTE_DEFAULT.md
IMPLEMENTACION_GEMINI_ENDPOINT.md
OPTIMIZACION_RETRY.md
PLAN_ENDPOINT_GEMINI_PURO.md
PLAN_INFERENCIA_CONTABLE.md
RESUMEN_CAMBIOS_ESTRUCTURA.md
RESUMEN_CORRECCIONES_APLICADAS.md
RESUMEN_FINAL_CAMBIOS.md
RESUMEN_FINAL.md
RESUMEN_IMPLEMENTACION_MEJORAS.md
RESUMEN_MEJORAS_COMPARACION.md
SISTEMA_EXTRACCION_INTELIGENTE_IMPLEMENTADO.md
SISTEMA_INFERENCIA_CONTABLE_IMPLEMENTADO.md
SISTEMA_RE_EXTRACCION_GEMINI.md
UBICACION_PROMPTS_SCHEMAS.md
```

**Problema:** 20+ archivos .md documentando cambios históricos. Difícil encontrar lo relevante.

#### 3.2 Tests fragmentados
- `test_admin_improvements.py`
- `test_gemini_endpoint.py`
- `test_intelligent_extraction.py`
- `test_modular_extraction.py`
- `tests.py`, `tests_cuit_validator.py`, `tests_post_processing.py`

---

### 4. ACOPLAMIENTO ALTO (Alto)

#### 4.1 Views con lógica de negocio
`views.py` y `views_gemini.py` tienen:
- Lógica de extracción
- Lógica de post-procesamiento
- Lógica de mapeo a modelo
- Lógica de validación

**Problema:** Views deberían ser solo controladores HTTP.

#### 4.2 Post-processor muy acoplado
`post_processor.py` importa y usa directamente:
- GeminiCorrector
- FiscalLogicInferencer
- AdaptiveFiscalValidator
- MasterValidator/FiscalValidator

---

### 5. FLUJO DE EXTRACCIÓN CONFUSO (Crítico)

Actualmente hay 4 caminos posibles:
1. **LlamaExtract directo** (`services.py`)
2. **LlamaExtract + GeminiCorrector retry** (`views.py` + `post_processor.py`)
3. **Gemini directo** (`services_gemini_extractor.py`)
4. **Gemini + Orchestrator** (`views_gemini.py` + `intelligent_orchestrator.py`)

**Problema:** No está claro cuál usar, código difícil de seguir.

---

## ✅ PROPUESTA DE ARQUITECTURA LIMPIA

### Nueva Estructura de Carpetas

```
invoice_extractor/
├── core/
│   ├── __init__.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseExtractor (interfaz común)
│   │   ├── llama.py             # LlamaExtractService
│   │   └── gemini.py            # GeminiExtractService (ÚNICO)
│   │
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseValidator
│   │   ├── cuit.py              # CUITValidator
│   │   ├── items.py             # ItemsValidator  
│   │   ├── fiscal.py            # FiscalValidator (CONSOLIDADO)
│   │   └── master.py            # MasterValidator
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── normalizer.py        # Normalización
│   │   ├── corrector.py         # Correcciones automáticas
│   │   └── pipeline.py          # Pipeline unificado
│   │
│   └── schemas/
│       ├── __init__.py
│       ├── invoice.py           # Schema ÚNICO (ComprobanteArgentino)
│       └── segments.py          # SchemaComposer
│
├── api/
│   ├── __init__.py
│   ├── views.py                 # Vista ÚNICA
│   └── serializers.py
│
├── utils/
│   ├── __init__.py
│   ├── retry.py                 # retry_with_exponential_backoff (ÚNICO)
│   ├── image.py                 # Preprocesamiento de imágenes
│   └── gemini_auth.py           # Autenticación Gemini (ÚNICO)
│
├── models.py
├── admin.py
├── apps.py
└── urls.py
```

### Diagrama de Flujo Simplificado

```
┌─────────────────────────────────────────────────────────────────┐
│                         API REQUEST                              │
│                    POST /api/invoices/process                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      1. PREPROCESAMIENTO                         │
│  • Validar archivo                                               │
│  • Preprocesar imagen (si aplica)                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       2. EXTRACCIÓN                              │
│  ┌────────────────────┐  ┌────────────────────┐                 │
│  │  GeminiExtractor   │  │  LlamaExtractor    │  (elegir uno)   │
│  │  (por defecto)     │  │  (fallback)        │                 │
│  └────────────────────┘  └────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   3. PIPELINE DE PROCESAMIENTO                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Normalizer   │─▶│ Corrector    │─▶│ Validator    │          │
│  │              │  │              │  │              │          │
│  │ • Limpieza   │  │ • CUITs      │  │ • Master     │          │
│  │ • Formatos   │  │ • Alícuotas  │  │   Validator  │          │
│  │ • Nullish    │  │ • Matemática │  │ • Score      │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      4. RETRY (opcional)                         │
│  Si score < 0.7 → Re-extraer con contexto de errores            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        5. RESPUESTA                              │
│  { data, metadata, validation_score }                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 TAREAS DE IMPLEMENTACIÓN

### FASE 1: Consolidación de Utilidades (1-2 días)

| ID | Tarea | Prioridad | Complejidad |
|----|-------|-----------|-------------|
| 1.1 | Crear `utils/retry.py` con función única | Alta | Baja |
| 1.2 | Crear `utils/gemini_auth.py` con autenticación única | Alta | Baja |
| 1.3 | Mover preprocesamiento a `utils/image.py` | Media | Baja |
| 1.4 | Eliminar duplicados de services_gemini_*.py | Alta | Media |

**Detalle 1.1 - utils/retry.py:**
```python
# utils/retry.py
"""Utilidad para retry con exponential backoff"""

import time
import logging
from google.genai import errors

logger = logging.getLogger(__name__)

def retry_with_exponential_backoff(
    func,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0
):
    """
    Ejecuta función con retry automático para errores 429.
    
    Args:
        func: Función a ejecutar (callable sin argumentos)
        max_retries: Número máximo de reintentos
        initial_delay: Delay inicial en segundos
        exponential_base: Base para cálculo exponencial
        max_delay: Delay máximo en segundos
    
    Returns:
        Resultado de la función
    
    Raises:
        La última excepción si todos los reintentos fallan
    """
    # ... implementación única ...
```

---

### FASE 2: Unificación de Schemas (1 día)

| ID | Tarea | Prioridad | Complejidad |
|----|-------|-----------|-------------|
| 2.1 | Unificar schemas en `core/schemas/invoice.py` | Alta | Media |
| 2.2 | Eliminar GeminiInvoice* de services_gemini_corrector.py | Alta | Baja |
| 2.3 | Actualizar referencias en todos los archivos | Alta | Media |

**Schema único propuesto:**
```python
# core/schemas/invoice.py
"""Schema único para facturas argentinas"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class InvoiceItem(BaseModel):
    """Item de factura - definición única"""
    codigo: Optional[str] = Field(None, max_length=20)
    descripcion: str = Field(..., max_length=500)
    cantidad: float = Field(..., gt=0)
    unidad_medida: Optional[str] = Field(None, max_length=10)
    precio_unitario: float = Field(..., ge=0)
    subtotal: float = Field(..., ge=0)

class InvoiceFiscalidad(BaseModel):
    """Datos fiscales - definición única"""
    subtotal_gravado: float = Field(..., ge=0)
    iva: Dict[str, float] = Field(default_factory=dict)
    percepciones: Dict[str, float] = Field(default_factory=dict)
    retenciones: Dict[str, float] = Field(default_factory=dict)
    importe_total: float = Field(..., ge=0)

# ... etc
```

---

### FASE 3: Consolidación de Extractores (2-3 días)

| ID | Tarea | Prioridad | Complejidad |
|----|-------|-----------|-------------|
| 3.1 | Crear `core/extractors/base.py` con interfaz común | Alta | Media |
| 3.2 | Crear `core/extractors/gemini.py` (único) | Alta | Alta |
| 3.3 | Simplificar `core/extractors/llama.py` | Media | Media |
| 3.4 | Eliminar services_gemini_corrector.py | Alta | Media |
| 3.5 | Eliminar intelligent_orchestrator.py | Media | Baja |

**Interfaz base propuesta:**
```python
# core/extractors/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

class BaseExtractor(ABC):
    """Interfaz común para todos los extractores"""
    
    @abstractmethod
    def extract(
        self,
        file_path: str,
        segments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extrae datos de una factura.
        
        Args:
            file_path: Ruta al archivo
            segments: Segmentos a extraer (None = todos)
        
        Returns:
            {
                'success': bool,
                'data': dict,
                'metadata': dict,
                'error': str (opcional)
            }
        """
        pass
    
    @abstractmethod
    def retry_with_context(
        self,
        file_path: str,
        original_data: Dict[str, Any],
        validation_errors: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Re-extrae con contexto de errores"""
        pass
```

---

### FASE 4: Simplificación de Validadores (2 días)

| ID | Tarea | Prioridad | Complejidad |
|----|-------|-----------|-------------|
| 4.1 | Consolidar fiscal_validator*.py en uno solo | Alta | Media |
| 4.2 | Eliminar adaptive_fiscal_validator.py | Media | Baja |
| 4.3 | Eliminar fiscal_logic_inferencer.py | Media | Baja |
| 4.4 | Simplificar MasterValidator | Media | Media |

**Validadores consolidados:**
```
validators/
├── cuit.py           # Validación de CUIT (mantener)
├── items.py          # Validación de items (mantener)
├── fiscal.py         # Validación fiscal (CONSOLIDAR)
├── confidence.py     # Cálculo de score (mantener)
└── master.py         # Orquestador (SIMPLIFICAR)
```

---

### FASE 5: Unificación de Views (2 días)

| ID | Tarea | Prioridad | Complejidad |
|----|-------|-----------|-------------|
| 5.1 | Crear servicio de mapeo a modelo | Alta | Media |
| 5.2 | Unificar views.py y views_gemini.py | Alta | Alta |
| 5.3 | Extraer lógica de negocio de views | Alta | Alta |
| 5.4 | Eliminar views_batch.py si no se usa | Baja | Baja |

**Estructura propuesta:**
```python
# api/views.py
"""Vista única para procesamiento de facturas"""

class InvoiceViewSet(viewsets.ModelViewSet):
    
    @action(detail=False, methods=['post'], url_path='process')
    def process(self, request):
        """
        Procesar factura.
        
        Parámetros opcionales:
        - extractor: 'gemini' (default) o 'llama'
        - segments: lista de segmentos a extraer
        - enable_retry: True/False
        """
        # 1. Validar request
        document = self._validate_request(request)
        
        # 2. Crear registro
        invoice = Invoice.objects.create(...)
        
        # 3. Procesar (delegado a servicio)
        result = InvoiceProcessingService.process(
            file_path=invoice.document.path,
            extractor=request.data.get('extractor', 'gemini'),
            segments=request.data.get('segments'),
            enable_retry=request.data.get('enable_retry', True)
        )
        
        # 4. Guardar resultado
        self._save_to_model(invoice, result)
        
        # 5. Responder
        return Response(result)
```

---

### FASE 6: Limpieza de Documentación (1 día)

| ID | Tarea | Prioridad | Complejidad |
|----|-------|-----------|-------------|
| 6.1 | Archivar .md obsoletos en carpeta `docs/archive/` | Media | Baja |
| 6.2 | Crear README.md actualizado | Alta | Media |
| 6.3 | Crear ARCHITECTURE.md con nuevo diseño | Media | Media |
| 6.4 | Documentar API en API_REFERENCE.md | Media | Media |

**Archivos a mantener:**
```
README.md           # Actualizado
ARCHITECTURE.md     # Nuevo: describe el diseño
API_REFERENCE.md    # Nuevo: documenta endpoints
CONTRIBUTING.md     # Actualizado
DEPLOYMENT.md       # Renombrar de RAILWAY_DEPLOYMENT.md
env.example         # Mantener
```

**Archivos a archivar (mover a docs/archive/):**
```
Todos los .md de cambios históricos y fixes específicos
```

---

### FASE 7: Consolidación de Tests (1-2 días)

| ID | Tarea | Prioridad | Complejidad |
|----|-------|-----------|-------------|
| 7.1 | Crear test suite unificado | Media | Media |
| 7.2 | Eliminar tests fragmentados | Baja | Baja |
| 7.3 | Añadir tests de integración | Media | Alta |

**Estructura de tests propuesta:**
```
tests/
├── __init__.py
├── conftest.py              # Fixtures comunes
├── unit/
│   ├── test_extractors.py   # Tests de extractores
│   ├── test_validators.py   # Tests de validadores
│   └── test_processors.py   # Tests de procesadores
├── integration/
│   ├── test_api.py          # Tests de API endpoints
│   └── test_pipeline.py     # Tests end-to-end
└── fixtures/
    ├── Ejemplo1.jpeg
    ├── Ejemplo2.jpeg
    └── expected_results/
```

---

## 📅 CRONOGRAMA PROPUESTO

| Fase | Duración | Dependencias |
|------|----------|--------------|
| FASE 1: Utilidades | 1-2 días | - |
| FASE 2: Schemas | 1 día | FASE 1 |
| FASE 3: Extractores | 2-3 días | FASE 1, 2 |
| FASE 4: Validadores | 2 días | FASE 2 |
| FASE 5: Views | 2 días | FASE 3, 4 |
| FASE 6: Documentación | 1 día | FASE 5 |
| FASE 7: Tests | 1-2 días | FASE 5 |

**Total estimado: 10-13 días de trabajo**

---

## 🎯 BENEFICIOS ESPERADOS

### Reducción de Código
- **Antes:** ~35 archivos Python, ~8000+ líneas
- **Después:** ~20 archivos Python, ~4000 líneas
- **Reducción:** ~50%

### Mejora de Mantenibilidad
- Un único lugar para cada funcionalidad
- Interfaces claras entre componentes
- Tests más fáciles de escribir

### Mejora de Performance
- Eliminar código muerto (orchestrator progresivo)
- Eliminar validaciones redundantes
- Menos pasos en el pipeline

### Mejor DX (Developer Experience)
- Estructura clara y predecible
- Documentación actualizada
- Flujo de extracción único y documentado

---

## ⚠️ RIESGOS Y MITIGACIÓN

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Regresiones | Media | Alto | Tests exhaustivos antes/después |
| Cambios en API | Media | Medio | Mantener compatibilidad backward |
| Pérdida de funcionalidad | Baja | Alto | Documentar toda funcionalidad actual |

---

## 📝 PRÓXIMOS PASOS

1. **Revisar y aprobar** este plan
2. **Crear rama** `refactor/clean-architecture`
3. **Implementar fase por fase** con PRs pequeños
4. **Test exhaustivo** en cada fase
5. **Merge gradual** a main

---

## 🔗 REFERENCIAS

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Django Best Practices](https://docs.djangoproject.com/en/4.2/misc/design-philosophies/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)

