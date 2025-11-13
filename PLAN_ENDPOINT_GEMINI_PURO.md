# 📋 PLAN: Endpoint 100% Gemini (Sin LlamaExtract)

## 🎯 Objetivo

Crear un nuevo endpoint `/api/invoices/process-gemini/` que realice extracción de facturas argentinas usando **exclusivamente Google Gemini 2.5 Flash**, manteniendo toda la infraestructura de post-procesamiento, validaciones, warnings y estructura de respuesta idéntica al endpoint actual.

---

## 📊 Análisis del Flujo Actual (LlamaExtract + Gemini Retry)

### Pipeline Actual (`/api/invoices/process/`)

```
1. EXTRACCIÓN INICIAL (LlamaExtract)
   ├─ InvoiceExtractionService
   ├─ Schemas Pydantic (ComprobanteArgentino)
   ├─ Output: extracted_data + metadata
   └─ Tiempo: ~5-10s

2. POST-PROCESAMIENTO
   ├─ InvoicePostProcessor.process_with_gemini_retry()
   │  ├─ a. NORMALIZACIÓN (normalize_all)
   │  │    ├─ clean_nullish_recursive
   │  │    ├─ normalize_items
   │  │    ├─ normalize_documento
   │  │    ├─ normalize_partes
   │  │    └─ normalize_fiscalidad (convierte IVA a formato dict)
   │  │
   │  ├─ b. CORRECCIONES (apply_all_corrections)
   │  │    ├─ apply_cuit_auto_correction
   │  │    ├─ apply_date_format_correction
   │  │    ├─ apply_items_correction (intercambios, cálculos)
   │  │    ├─ apply_document_type_correction (validación AFIP)
   │  │    ├─ apply_address_consolidation
   │  │    ├─ apply_fiscal_calculations_correction
   │  │    └─ apply_date_consistency_correction
   │  │
   │  ├─ c. VALIDACIONES (MasterValidator.validate_complete)
   │  │    ├─ CUITValidator (empresa y cliente)
   │  │    ├─ ItemsValidator (cálculos, cantidades, suma)
   │  │    ├─ FiscalValidatorAdvanced (IVA, totales, percepciones)
   │  │    └─ ConfidenceScorer (scoring + alertas + recomendaciones)
   │  │
   │  ├─ d. DECISIÓN GEMINI RETRY
   │  │    ├─ should_retry_extraction() → SI/NO
   │  │    └─ Si SI: retry_extraction_with_gemini()
   │  │         ├─ Contexto: errores + datos originales
   │  │         ├─ Prompt con correcciones
   │  │         └─ Nueva extracción (solo items + fiscalidad)
   │  │
   │  └─ e. COMPARACIÓN Y SELECCIÓN
   │       ├─ Comparar scores: LlamaExtract vs Gemini
   │       └─ Retornar mejor resultado
   │
   └─ Output: processed_data + validation_result + processing_metadata

3. MAPEO A MODELO DJANGO
   ├─ Invoice.save() con todos los campos
   └─ InvoiceItem.objects.create() para cada item

4. RESPUESTA
   └─ legacy_format con metadata completo
```

---

## 🆕 Nuevo Flujo: 100% Gemini (Sin LlamaExtract)

### Pipeline Propuesto (`/api/invoices/process-gemini/`)

```
1. EXTRACCIÓN INICIAL (Gemini 2.5 Flash)
   ├─ GeminiExtractor (NUEVO SERVICIO)
   ├─ Schemas Pydantic (MISMO ComprobanteArgentino)
   ├─ System Instruction: CONTADOR_ARGENTINO
   ├─ Output: extracted_data + metadata
   └─ Tiempo estimado: ~8-15s

2. POST-PROCESAMIENTO (REUTILIZAR 100%)
   ├─ InvoicePostProcessor.process()
   │  ├─ a. NORMALIZACIÓN (normalize_all) ✅ RECICLAR
   │  ├─ b. CORRECCIONES (apply_all_corrections) ✅ RECICLAR
   │  ├─ c. VALIDACIONES (MasterValidator) ✅ RECICLAR
   │  └─ Output: processed_data + validation_result
   │
   └─ NOTA: NO usar process_with_gemini_retry() porque YA usamos Gemini

3. REPROCESAMIENTO CON CONTEXTO (SI HAY ERRORES)
   ├─ Si validation_score < 0.6 o errores críticos:
   │  └─ GeminiExtractor.retry_with_context()
   │       ├─ Prompt enriquecido con errores detectados
   │       ├─ Contexto de primera extracción
   │       └─ Segunda extracción Gemini mejorada
   │
   ├─ Comparar scores (primera vs segunda)
   └─ Seleccionar mejor resultado

4. MAPEO A MODELO DJANGO (REUTILIZAR 100%)
   ├─ Invoice.save() con extraction_method='gemini'
   └─ InvoiceItem.objects.create()

5. RESPUESTA (REUTILIZAR 100%)
   └─ legacy_format idéntico al actual
```

---

## 🧩 Componentes a Crear

### 1. **GeminiExtractor** (NUEVO)
**Archivo**: `invoice_extractor/services_gemini_extractor.py`

**Responsabilidades**:
- Extracción completa (items + partes + documento + fiscalidad) con Gemini
- Usar MISMO schema `ComprobanteArgentino` del actual
- System instruction optimizado para contador argentino
- Manejo de errores y fallbacks
- Retry con contexto enriquecido

**Diferencias con GeminiCorrector actual**:
| Aspecto | GeminiCorrector (actual) | GeminiExtractor (nuevo) |
|---------|--------------------------|-------------------------|
| **Propósito** | Re-extracción parcial (solo items + fiscalidad) | Extracción completa desde cero |
| **Schema** | GeminiInvoiceComplete (simplificado) | ComprobanteArgentino (completo) |
| **Contexto** | Recibe datos previos de LlamaExtract + errores | Sin datos previos, solo el documento |
| **Prompt** | Enfocado en corrección de errores específicos | Extracción general completa |
| **Uso** | Segundo intento después de LlamaExtract | Primer y único método de extracción |

**Métodos principales**:
```python
class GeminiExtractor:
    def __init__(self, api_key=None, service_account_path=None)
    
    def extract_complete(
        self, 
        file_path: str, 
        schema_type: str = 'completo',
        segments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extracción completa con Gemini 2.5 Flash
        
        Returns:
            {
                'success': True,
                'data': {...},  # Estructura idéntica a LlamaExtract
                'metadata': {
                    'extraction_time': float,
                    'schema_type': str,
                    'extractor': 'gemini-2.5-flash',
                    'extraction_method': 'gemini'
                }
            }
        """
    
    def retry_with_context(
        self,
        file_path: str,
        original_data: Dict[str, Any],
        validation_result: Dict[str, Any],
        schema_type: str = 'completo'
    ) -> Optional[Dict[str, Any]]:
        """
        Re-extracción con contexto de errores
        
        Similar a GeminiCorrector.retry_extraction_with_gemini()
        pero con schema completo
        """
    
    def _build_extraction_prompt(
        self, 
        schema_type: str,
        segments: Optional[List[str]] = None
    ) -> str:
        """Construir prompt optimizado para extracción completa"""
    
    def _build_retry_prompt(
        self,
        original_data: Dict[str, Any],
        validation_result: Dict[str, Any]
    ) -> str:
        """Construir prompt para retry con contexto de errores"""
```

**Schema a usar**:
- Importar `ComprobanteArgentino` desde `invoice_extractor.schemas`
- NO crear schemas nuevos
- Soportar extracción modular (igual que LlamaExtract)

**System Instruction**:
```python
SYSTEM_INSTRUCTION_CONTADOR_COMPLETO = """
Eres un contador público argentino certificado con 25+ años de experiencia.

🏛️ NORMATIVA ARGENTINA:
- Régimen de facturación electrónica AFIP
- Códigos de comprobantes: 001=Factura A, 006=Factura B, 011=Factura C, etc.
- Condiciones fiscales: Responsable Inscripto, Monotributo, Exento, Consumidor Final
- Impuestos: IVA (21%, 10.5%, 27%, 5%, 2.5%), Percepciones IIBB, Impuestos Internos

🔧 CORRECCIÓN OCR:
- Corrige errores típicos: ø→é, rn→m, 0→O, 6→G, S→5, l→I
- CUIT SIEMPRE formato XX-XXXXXXXX-X (con guiones)
- Números: separa miles con puntos, decimales con coma

⚖️ PRECISIÓN MATEMÁTICA CRÍTICA:
- CADA item: cantidad × precio_unitario = subtotal
- SUMA items: Σ(subtotal) = subtotal_gravado
- TOTAL: subtotal_gravado + IVA + percepciones = importe_total
- Verifica TODOS los cálculos

🎯 EXTRACCIÓN COMPLETA:
1. ITEMS: Extrae TODOS los items (cada fila = 1 item)
2. PARTES: Extrae datos de empresa y cliente (razón social, CUIT, domicilio, etc.)
3. DOCUMENTO: Tipo comprobante, número, CAE, fechas, moneda
4. FISCALIDAD: Subtotales, IVA discriminado, percepciones, total

⚠️ REGLAS CRÍTICAS:
- NO inventes datos - si no está claro, devuelve null
- NO dupliques items - cada fila es única
- Lee COLUMNA POR COLUMNA de izquierda a derecha
- Verifica TODOS los cálculos matemáticos
"""
```

---

### 2. **InvoiceGeminiViewSet** (NUEVO)
**Archivo**: `invoice_extractor/views_gemini.py`

**Endpoint**: `POST /api/invoices/process-gemini/`

**Estructura**:
```python
class InvoiceGeminiViewSet(viewsets.ViewSet):
    """
    ViewSet para procesamiento 100% Gemini
    """
    parser_classes = (MultiPartParser, FormParser)
    
    @action(detail=False, methods=['post'], url_path='process-gemini')
    def upload_gemini(self, request):
        """
        Procesar factura con Gemini 2.5 Flash exclusivamente
        
        Parámetros (idénticos al endpoint actual):
        - document: archivo (PDF, JPG, PNG)
        - schema_type: 'completo', 'simplificado', 'modular'
        - segments: lista de segmentos (si schema_type='modular')
        - enable_retry: bool (default: True) - habilitar retry con contexto
        
        Response: Idéntico al endpoint actual
        """
```

**Flujo interno**:
```python
# 1. Crear registro Invoice
invoice = Invoice.objects.create(document=document, status='processing')

# 2. Extraer con Gemini
gemini_extractor = GeminiExtractor()
result = gemini_extractor.extract_complete(
    file_path=invoice.document.path,
    schema_type=schema_type,
    segments=segments
)

if not result['success']:
    raise Exception(result['error'])

extracted = result['data']
metadata = result['metadata']

# 3. Post-procesar (REUTILIZAR InvoicePostProcessor)
processor = InvoicePostProcessor(
    use_master_validator=True,
    enable_gemini_retry=False  # ❌ NO usar retry porque YA es Gemini
)
post_processing_result = processor.process(extracted)

# 4. Retry con contexto SI hay errores críticos (OPCIONAL)
enable_retry = request.data.get('enable_retry', 'true').lower() == 'true'
validation_score = post_processing_result['validation_result']['validation_score']

if enable_retry and validation_score < 0.6:
    logger.warning(f"🔄 Score bajo ({validation_score:.2%}), reintentando con contexto...")
    
    retry_extracted = gemini_extractor.retry_with_context(
        file_path=invoice.document.path,
        original_data=extracted,
        validation_result=post_processing_result['validation_result'],
        schema_type=schema_type
    )
    
    if retry_extracted:
        # Procesar segunda extracción
        retry_result = processor.process(retry_extracted)
        retry_score = retry_result['validation_result']['validation_score']
        
        # Comparar y elegir mejor
        if retry_score > validation_score:
            logger.info(f"✅ Retry mejoró score: {validation_score:.2%} → {retry_score:.2%}")
            post_processing_result = retry_result
            post_processing_result['processing_metadata']['gemini_retry'] = {
                'was_retried': True,
                'first_score': validation_score,
                'second_score': retry_score,
                'improvement': (retry_score - validation_score) * 100,
                'method_used': 'gemini'
            }

# 5. Mapear a Invoice model (REUTILIZAR código existente)
processed_data = post_processing_result['processed_data']
validation_result = post_processing_result['validation_result']

invoice.extraction_method = 'gemini'
invoice.gemini_retry_used = post_processing_result['processing_metadata'].get('gemini_retry', {}).get('was_retried', False)
# ... resto del mapeo idéntico

# 6. Retornar legacy_format (REUTILIZAR)
legacy_format = {
    **processed_data,
    'metadata': {...}  # Idéntico al actual
}

return Response({
    'id': invoice.id,
    'status': 'completed',
    'message': 'Invoice processed successfully with Gemini',
    'data': legacy_format
})
```

---

### 3. **Ruta URL** (MODIFICAR)
**Archivo**: `invoice_extractor/urls.py`

**Agregar**:
```python
from .views_gemini import InvoiceGeminiViewSet

urlpatterns = [
    # ... rutas existentes
    path('invoices/process-gemini/', 
         InvoiceGeminiViewSet.as_view({'post': 'upload_gemini'}), 
         name='invoice-process-gemini'),
]
```

---

## ♻️ Componentes a Reutilizar (100%)

### ✅ Post-Procesamiento
| Componente | Archivo | Reutilización |
|------------|---------|---------------|
| `InvoicePostProcessor.process()` | `utils/post_processor.py` | ✅ 100% |
| `normalize_all()` | `utils/normalization.py` | ✅ 100% |
| `apply_all_corrections()` | `utils/corrections.py` | ✅ 100% |
| `MasterValidator.validate_complete()` | `validators/master_validator.py` | ✅ 100% |
| `CUITValidator` | `validators/cuit_validator.py` | ✅ 100% |
| `ItemsValidator` | `validators/items_validator.py` | ✅ 100% |
| `FiscalValidatorAdvanced` | `validators/fiscal_validator_advanced.py` | ✅ 100% |
| `ConfidenceScorer` | `validators/confidence_scorer.py` | ✅ 100% |

### ✅ Schemas
| Schema | Archivo | Reutilización |
|--------|---------|---------------|
| `ComprobanteArgentino` | `schemas.py` | ✅ 100% |
| `ComprobanteSimplificado` | `schemas.py` | ✅ 100% |
| `SchemaComposer` | `schemas.py` | ✅ 100% |
| Todos los schemas anidados (Items, Partes, Documento, etc.) | `schemas.py` | ✅ 100% |

### ✅ Modelos Django
| Modelo | Archivo | Reutilización |
|--------|---------|---------------|
| `Invoice` | `models.py` | ✅ 100% (solo cambiar `extraction_method='gemini'`) |
| `InvoiceItem` | `models.py` | ✅ 100% |

### ✅ Código de Mapeo
Todo el código de mapeo de `processed_data` → Django models en `views.py` líneas 261-383 se reutiliza **idénticamente**.

---

## 🔄 Comparación: Flujo Actual vs Gemini Puro

| Aspecto | Flujo Actual (LlamaExtract + Gemini Retry) | Flujo Gemini Puro (Nuevo) |
|---------|---------------------------------------------|---------------------------|
| **Extracción inicial** | LlamaExtract (5-10s) | Gemini 2.5 Flash (8-15s) |
| **Normalización** | ✅ InvoicePostProcessor.process() | ✅ MISMO |
| **Correcciones** | ✅ apply_all_corrections() | ✅ MISMO |
| **Validaciones** | ✅ MasterValidator | ✅ MISMO |
| **Retry con contexto** | GeminiCorrector (solo items + fiscalidad) | GeminiExtractor (completo) |
| **Decisión de retry** | `should_retry_extraction()` | MISMO criterio (score < 0.6) |
| **Comparación de scores** | LlamaExtract vs Gemini | Gemini 1 vs Gemini 2 |
| **Mapeo a Django** | ✅ Invoice + InvoiceItem | ✅ MISMO |
| **Respuesta** | ✅ legacy_format | ✅ MISMO |

---

## 📝 Plan de Implementación

### Fase 1: Crear GeminiExtractor
**Tareas**:
1. Crear `invoice_extractor/services_gemini_extractor.py`
2. Implementar `GeminiExtractor.__init__()` (reutilizar lógica de autenticación de `GeminiCorrector`)
3. Implementar `GeminiExtractor.extract_complete()`:
   - Subir archivo con File API
   - Construir prompt de extracción completa
   - Llamar a Gemini con schema `ComprobanteArgentino`
   - Parsear respuesta y retornar en formato compatible
4. Implementar `GeminiExtractor.retry_with_context()`:
   - Similar a `GeminiCorrector.retry_extraction_with_gemini()`
   - Usar schema completo
   - Prompt enriquecido con errores

**Código reutilizable de GeminiCorrector**:
- `_init_genai_client()` → ✅ Copiar tal cual
- `_upload_file_with_cache()` → ✅ Copiar tal cual
- `build_correction_prompt()` → ⚠️ Adaptar para extracción completa
- `retry_extraction_with_gemini()` → ⚠️ Adaptar para schema completo

**Tests**:
- Test de extracción completa con Ejemplo1.jpeg
- Test de retry con contexto
- Comparar output con LlamaExtract (misma estructura)

---

### Fase 2: Crear Endpoint views_gemini.py
**Tareas**:
1. Crear `invoice_extractor/views_gemini.py`
2. Implementar `InvoiceGeminiViewSet.upload_gemini()`:
   - Validar request (reutilizar `InvoiceUploadSerializer`)
   - Crear registro `Invoice`
   - Llamar a `GeminiExtractor.extract_complete()`
   - Post-procesar con `InvoicePostProcessor.process()`
   - Implementar lógica de retry opcional
   - Mapear a Django models (copiar código de `views.py`)
   - Construir `legacy_format` (copiar código de `views.py`)
   - Retornar Response

**Código reutilizable de views.py**:
- Líneas 85-107: Validación y parámetros → ✅ Copiar
- Líneas 108-113: Crear Invoice → ✅ Copiar
- Líneas 261-383: Mapeo a Django models → ✅ Copiar 100%
- Líneas 192-228: Construcción de legacy_format → ✅ Copiar 100%

---

### Fase 3: Agregar Ruta
**Tareas**:
1. Modificar `invoice_extractor/urls.py`
2. Agregar path para `process-gemini`
3. Importar `InvoiceGeminiViewSet`

---

### Fase 4: Testing y Documentación
**Tareas**:
1. Test con facturas de ejemplo (Ejemplo1.jpeg, Ejemplo2.jpeg, Ejemplo3.jpeg)
2. Comparar resultados con endpoint actual
3. Verificar que `legacy_format` es idéntico
4. Verificar que metadata incluye `extraction_method='gemini'`
5. Documentar endpoint en `API_USAGE_GUIDE.md`
6. Crear ejemplos curl

---

## 🧪 Tests a Realizar

### Test 1: Extracción Completa
```bash
curl -X POST http://localhost:8000/api/invoices/process-gemini/ \
  -F "document=@Ejemplo1.jpeg" \
  -F "schema_type=completo"
```

**Verificar**:
- ✅ Response tiene estructura idéntica al endpoint actual
- ✅ `data.items` tiene todos los items
- ✅ `data.partes.empresa` y `data.partes.cliente` completos
- ✅ `data.documento` completo
- ✅ `data.fiscalidad` completo
- ✅ `data.metadata.extraction.extraction_method == 'gemini-2.5-flash'`
- ✅ `validation_score` calculado correctamente

### Test 2: Retry con Contexto
```bash
# Usar factura con errores conocidos
curl -X POST http://localhost:8000/api/invoices/process-gemini/ \
  -F "document=@factura_con_errores.jpeg" \
  -F "schema_type=completo" \
  -F "enable_retry=true"
```

**Verificar**:
- ✅ Primera extracción tiene score < 0.6
- ✅ Se dispara retry automático
- ✅ Segunda extracción tiene score > primera
- ✅ `data.metadata.gemini_retry.used == true`
- ✅ `data.metadata.gemini_retry.improvement > 0`

### Test 3: Extracción Modular
```bash
curl -X POST http://localhost:8000/api/invoices/process-gemini/ \
  -F "document=@Ejemplo2.jpeg" \
  -F "schema_type=modular" \
  -F "segments[]=items" \
  -F "segments[]=fiscalidad"
```

**Verificar**:
- ✅ Solo `items` y `fiscalidad` en respuesta
- ✅ `partes` y `documento` ausentes o vacíos

### Test 4: Comparación con LlamaExtract
```python
# Script de comparación
import requests

files = ['Ejemplo1.jpeg', 'Ejemplo2.jpeg', 'Ejemplo3.jpeg']
for file in files:
    # Endpoint actual
    r1 = requests.post('http://localhost:8000/api/invoices/process/', 
                       files={'document': open(file, 'rb')})
    
    # Endpoint Gemini
    r2 = requests.post('http://localhost:8000/api/invoices/process-gemini/', 
                       files={'document': open(file, 'rb')})
    
    # Comparar estructuras
    assert set(r1.json()['data'].keys()) == set(r2.json()['data'].keys())
    
    # Comparar scores
    score1 = r1.json()['data']['metadata']['validation']['validation_score']
    score2 = r2.json()['data']['metadata']['validation']['validation_score']
    
    print(f"{file}: LlamaExtract={score1:.2%}, Gemini={score2:.2%}")
```

---

## 📊 Métricas a Medir

| Métrica | LlamaExtract Actual | Gemini Puro Esperado |
|---------|---------------------|----------------------|
| **Tiempo de extracción** | 5-10s | 8-15s |
| **Tiempo total (con post-proc)** | 8-15s | 12-20s |
| **Validation score promedio** | 0.85-0.95 | 0.80-0.95 (esperado similar) |
| **Tasa de retry** | ~20% | ~25% (esperado ligeramente mayor) |
| **Costo por request** | $0.002-0.005 | $0.01-0.02 (mayor, pero sin LlamaAPI) |
| **Precisión en items** | 95% | 90-95% (esperado similar) |
| **Precisión en fiscalidad** | 92% | 90-95% (esperado similar) |

---

## ⚙️ Variables de Entorno

**Agregar a `env.example`**:
```bash
# ============================================================================
# GEMINI EXTRACTION (Alternative to LlamaExtract)
# ============================================================================

# Opción 1: API Key (desarrollo)
GOOGLE_API_KEY=your_google_ai_api_key_here

# Opción 2: Service Account (producción/Railway)
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# Configuración opcional
GEMINI_MODEL_NAME=gemini-2.5-flash
GEMINI_TEMPERATURE=0.0
GEMINI_MAX_OUTPUT_TOKENS=16384
GEMINI_ENABLE_RETRY=true
```

---

## 🎁 Ventajas del Nuevo Endpoint

### ✅ Ventajas Técnicas
1. **Sin dependencia de LlamaExtract**: No necesita LLAMAAPI_KEY
2. **Reutiliza 100% del post-procesamiento**: Mismo código probado
3. **Mismo formato de salida**: Totalmente compatible con frontend/clientes
4. **Retry inteligente**: Segunda oportunidad con contexto de errores
5. **Modularidad**: Mantiene soporte para extracción segmentada

### ✅ Ventajas de Negocio
1. **Flexibilidad de proveedor**: Alternativa a LlamaCloud
2. **Potencial mejor precisión**: Gemini 2.5 Flash es muy potente
3. **Un solo proveedor**: Todo con Google (si se usa GCP para deploy)
4. **Testing A/B**: Comparar fácilmente LlamaExtract vs Gemini

### ✅ Casos de Uso
- **Backup**: Si LlamaExtract tiene downtime
- **Testing**: Probar cuál da mejores resultados por tipo de factura
- **Migración**: Transición gradual de LlamaExtract a Gemini
- **Costo**: Evaluar qué es más económico a largo plazo

---

## 🚀 Criterios de Éxito

### Fase 1 (GeminiExtractor)
- ✅ Extrae estructura completa idéntica a LlamaExtract
- ✅ Parsea correctamente todos los campos
- ✅ Retry con contexto mejora el score en casos con errores
- ✅ Maneja PDFs e imágenes correctamente

### Fase 2 (Endpoint)
- ✅ Response 100% compatible con endpoint actual
- ✅ Post-procesamiento funciona sin modificaciones
- ✅ Mapeo a Django models funciona sin modificaciones
- ✅ Metadata incluye información de Gemini

### Fase 3 (Testing)
- ✅ Validation scores comparables con LlamaExtract (±5%)
- ✅ Tiempos de respuesta aceptables (<20s para 90% de requests)
- ✅ Cero errores de parsing de schemas
- ✅ Admin panel muestra datos correctamente

---

## 📚 Documentación a Crear

1. **API_USAGE_GUIDE.md** (actualizar):
   - Nuevo endpoint `/api/invoices/process-gemini/`
   - Ejemplos curl
   - Comparación con endpoint actual
   - Cuándo usar cada uno

2. **GEMINI_EXTRACTOR.md** (nuevo):
   - Arquitectura del GeminiExtractor
   - System instructions
   - Prompts de extracción y retry
   - Manejo de errores
   - Configuración

3. **RAILWAY_DEPLOYMENT.md** (actualizar):
   - Variables de entorno para Gemini
   - Configuración de Service Account
   - Testing de ambos endpoints

---

## ⏱️ Estimación de Tiempo

| Fase | Tareas | Tiempo Estimado |
|------|--------|-----------------|
| **Fase 1** | GeminiExtractor | 4-6 horas |
| **Fase 2** | Endpoint views_gemini.py | 2-3 horas |
| **Fase 3** | Rutas y configuración | 1 hora |
| **Fase 4** | Testing exhaustivo | 3-4 horas |
| **Fase 5** | Documentación | 2 horas |
| **TOTAL** | | **12-16 horas** |

---

## ✅ Checklist Final

### Código
- [ ] `services_gemini_extractor.py` creado y testeado
- [ ] `views_gemini.py` creado y testeado
- [ ] `urls.py` actualizado
- [ ] Tests unitarios para GeminiExtractor
- [ ] Tests de integración para endpoint

### Funcionalidad
- [ ] Extracción completa funciona
- [ ] Retry con contexto funciona
- [ ] Post-procesamiento reutilizado 100%
- [ ] Validaciones funcionan correctamente
- [ ] Response idéntico al endpoint actual

### Documentación
- [ ] API_USAGE_GUIDE.md actualizado
- [ ] GEMINI_EXTRACTOR.md creado
- [ ] RAILWAY_DEPLOYMENT.md actualizado
- [ ] Ejemplos curl documentados
- [ ] env.example actualizado

### Deploy
- [ ] Variables de entorno configuradas en Railway
- [ ] Ambos endpoints funcionan en producción
- [ ] Logs de Gemini visibles en Railway
- [ ] Admin panel muestra extraction_method correctamente

---

## 🎯 Resumen Ejecutivo

Este plan crea un **endpoint alternativo 100% Gemini** que:

1. **NO toca código existente**: Todo el post-procesamiento se reutiliza tal cual
2. **Mantiene compatibilidad total**: Mismo formato de respuesta
3. **Agrega flexibilidad**: Dos opciones de extracción (LlamaExtract vs Gemini)
4. **Es modular y limpio**: Código separado, fácil de mantener
5. **Permite comparación**: Testing A/B entre proveedores
6. **Reduce dependencias**: Alternativa a LlamaCloud

**Decisión de arquitectura clave**: En lugar de modificar el flujo actual, crear un endpoint paralelo permite:
- Transición gradual sin riesgo
- Testing lado a lado
- Rollback instantáneo si hay problemas
- Eventualmente deprecar uno de los dos según resultados

**Próximo paso**: Aprobar este plan y proceder con Fase 1 (GeminiExtractor).

