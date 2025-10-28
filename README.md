# 🧾 Extractor de Comprobantes Argentinos

Sistema de extracción inteligente de datos de comprobantes fiscales argentinos (facturas, tickets, etc.) usando **LlamaExtract** y **Gemini 2.5 Flash** con validaciones avanzadas y correcciones automáticas.

---

## ✨ Características Principales

### 🎯 **Extracción Inteligente**
- **LlamaExtract** como motor principal de extracción
- **Gemini 2.5 Flash** para re-extracción inteligente cuando se detectan errores matemáticos
- Sistema de validación y scoring automático (0-100%)
- Extracción modular por segmentos (items, partes, fiscalidad, totales, documento)

### 🔍 **Validaciones Avanzadas**
- **CUIT**: Formato, checksum, tipo de persona, auto-corrección
- **Items**: Validación matemática (cantidad × precio = subtotal)
- **Fiscal**: Discriminación de IVA, percepciones, retenciones, totales
- **Confidence Scoring**: Puntuación de calidad con niveles (high, medium, low, critical)

### 🛠️ **Post-Procesamiento**
- Normalización de datos (fechas, CUITs, provincias)
- Correcciones automáticas (CUITs, items, fechas)
- Detección de inconsistencias matemáticas
- Alertas estructuradas para frontend

---

## 🚀 Quick Start

### 1. **Requisitos**
```bash
Python 3.13+
PostgreSQL (opcional, usa SQLite por defecto)
```

### 2. **Instalación**
```bash
# Clonar repositorio
git clone <repo-url>
cd Extractor_pasaelticket

# Crear entorno virtual
python3.13 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. **Configuración**
```bash
# Copiar template de .env
cp env.example .env

# Editar .env y agregar tus API keys:
# - LLAMAAPI_KEY=tu_llama_api_key
# - GOOGLE_AI_API_KEY=tu_google_ai_api_key (opcional, para Gemini)
```

### 4. **Inicializar Base de Datos**
```bash
python manage.py migrate
python manage.py createsuperuser  # Opcional
```

### 5. **Ejecutar Servidor**
```bash
python manage.py runserver
```

El servidor estará disponible en `http://localhost:8000`

---

## 📚 API Endpoints

### **POST /api/invoices/process/**
Procesa un comprobante y extrae sus datos.

**Request:**
```bash
curl -X POST http://localhost:8000/api/invoices/process/ \
  -F 'document=@factura.pdf' \
  -F 'original_filename=factura.pdf'
```

**Parámetros opcionales:**
- `schema_type`: `completo` (default) o `modular`
- `segments`: Array de segmentos (`items`, `partes`, `fiscalidad`, `totales`, `documento`)
- `use_gemini_only`: `true` para usar solo Gemini (útil para testing)

**Response:**
```json
{
  "id": 1,
  "status": "completed",
  "validation_score": "1.0000",
  "data": {
    "documento": { ... },
    "partes": { ... },
    "items": [ ... ],
    "fiscalidad": { ... }
  },
  "raw_extraction": {
    "processing_metadata": {
      "gemini_retry": {
        "used": false,
        "reason": "Score aceptable (100%)"
      }
    }
  }
}
```

### **GET /api/invoices/**
Lista todas las facturas procesadas.

### **GET /api/invoices/{id}/**
Obtiene detalles de una factura específica.

---

## 🧪 Testing

### **Test de Comparación: LlamaExtract vs Gemini**
```bash
python test_gemini_vs_llama.py
```

### **Test de Extracción Modular**
```bash
python test_modular_extraction.py Ejemplo2.jpeg items partes
```

### **Tests Unitarios**
```bash
python manage.py test invoice_extractor
```

---

## 📖 Documentación Adicional

### Extracción Modular
Ver `MODULAR_EXTRACTION.md` para detalles sobre cómo extraer segmentos específicos de facturas.

### Sistema de Re-extracción con Gemini
Ver `SISTEMA_RE_EXTRACCION_GEMINI.md` para entender cómo funciona el sistema inteligente de retry.

### Configuración de Gemini
Ver `CONFIGURACION_GEMINI.md` para instrucciones detalladas de setup.

### Arquitectura Modular
Ver `ARQUITECTURA_MODULAR.md` para diagramas y explicación de la arquitectura.

### Logging Detallado
Ver `LOGGING_DETALLADO.md` para información sobre el sistema de logs.

---

## 🏗️ Estructura del Proyecto

```
Extractor_pasaelticket/
├── invoice_extractor/          # App principal de Django
│   ├── models.py              # Modelos de datos (Invoice, InvoiceItem)
│   ├── schemas.py             # Schemas Pydantic para extracción
│   ├── services.py            # Servicio de extracción con LlamaExtract
│   ├── services_gemini_corrector.py  # Servicio de re-extracción con Gemini
│   ├── views.py               # API endpoints
│   ├── utils/                 # Utilidades de post-procesamiento
│   │   ├── normalization.py   # Normalización de datos
│   │   ├── corrections.py     # Correcciones automáticas
│   │   └── post_processor.py  # Orquestador principal
│   └── validators/            # Validadores especializados
│       ├── cuit_validator.py
│       ├── items_validator.py
│       ├── fiscal_validator.py
│       ├── fiscal_validator_advanced.py
│       ├── confidence_scorer.py
│       └── master_validator.py
├── extractor_project/         # Configuración de Django
├── media/                     # Archivos subidos
├── manage.py
└── requirements.txt
```

---

## 🔧 Scripts Útiles

### **reset_db.sh**
Reinicia la base de datos (útil en desarrollo):
```bash
./reset_db.sh
```

### **setup_env.sh**
Guía interactiva para configurar el `.env`:
```bash
./setup_env.sh
```

### **ejemplo_uso_modular.sh**
Ejemplos de uso de la API modular:
```bash
./ejemplo_uso_modular.sh
```

---

## 🤝 Contribuciones

Ver `CONTRIBUTING.md` para guías de contribución.

---

## 📊 Métricas del Sistema

### Validadores Implementados
- **CUITValidator**: Formato, checksum, auto-corrección
- **ItemsValidator**: Validación matemática, outliers
- **FiscalValidatorAdvanced**: IVA, percepciones, retenciones, totales
- **ConfidenceScorer**: Scoring 0-100% con niveles de confianza
- **MasterValidator**: Orquestador de todos los validadores

### Cobertura
- ✅ Validación de CUITs (formato + checksum)
- ✅ Validación de items (cantidad × precio = subtotal)
- ✅ Validación fiscal avanzada (IVA, percepciones, totales)
- ✅ Auto-corrección de CUITs con dígito verificador incorrecto
- ✅ Auto-corrección de formatos de fecha
- ✅ Normalización de unidades de medida
- ✅ Re-extracción inteligente con Gemini (cuando score < 60%)

---

## 📝 Notas

### Sistema Inteligente de Extracción
El sistema utiliza un enfoque híbrido:
1. **Primera extracción** con LlamaExtract
2. **Validación** automática con MasterValidator
3. **Re-extracción** con Gemini **solo si** score < 60%
4. **Comparación** y selección del mejor resultado

Esto garantiza:
- ✅ Velocidad (LlamaExtract es más rápido)
- ✅ Precisión (Gemini rescata casos complejos)
- ✅ Costo-eficiencia (Gemini solo cuando es necesario)

---

## 📞 Soporte

Para problemas o preguntas, revisar la documentación o crear un issue en el repositorio.

---

## 📄 Licencia

[Especificar licencia]
