# 🚀 Configuración para Railway

## Variables de Entorno Requeridas

Configura estas variables en Railway > Variables:

### 🔐 Autenticación

```bash
# API Keys para clientes (separadas por coma)
# Genera con: python -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEYS=tu-api-key-1,tu-api-key-2
```

### 🤖 Google Gemini

```bash
# Obtener en: https://aistudio.google.com/apikey
GOOGLE_API_KEY=tu-google-api-key
```

### ⚙️ Django

```bash
# Genera con: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=tu-secret-key-unico

# Producción
DEBUG=False
```

### 🌐 CORS (opcional)

```bash
# Si tu frontend está en otro dominio
CORS_ALLOWED_ORIGINS=https://tuapp.com,https://otrodominio.com
```

---

## 📦 Deploy en Railway

### 1. Conectar repositorio

1. Ve a [railway.app](https://railway.app)
2. New Project → Deploy from GitHub repo
3. Selecciona este repositorio

### 2. Agregar PostgreSQL

1. En tu proyecto, click "+ New"
2. Database → PostgreSQL
3. Railway configura `DATABASE_URL` automáticamente

### 3. Configurar variables

1. Click en tu servicio → Variables
2. Agrega las variables listadas arriba

### 4. Configurar Build

Railway detecta Django automáticamente. Si necesitas personalizar:

**Procfile** (ya incluido):
```
web: gunicorn extractor_project.wsgi --bind 0.0.0.0:$PORT
```

**railway.json** (opcional):
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python manage.py migrate && gunicorn extractor_project.wsgi --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

## 🔑 Uso de la API

### Autenticación

Todos los endpoints requieren API Key:

```bash
# Opción 1: Header Authorization
curl -X POST https://tu-app.railway.app/api/invoices-gemini/upload-gemini/ \
  -H "Authorization: Bearer tu-api-key" \
  -F "document=@factura.jpg"

# Opción 2: Header X-API-Key
curl -X POST https://tu-app.railway.app/api/invoices-gemini/upload-gemini/ \
  -H "X-API-Key: tu-api-key" \
  -F "document=@factura.jpg"
```

### Endpoints disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/invoices-gemini/upload-gemini/` | Procesar una factura |
| POST | `/api/invoices-batch/process-batch/` | Procesar múltiples facturas |
| GET | `/api/invoices-gemini/` | Listar facturas procesadas |
| GET | `/api/invoices-gemini/{id}/` | Detalle de una factura |

### Ejemplo con Python

```python
import requests

API_URL = "https://tu-app.railway.app/api/invoices-gemini/upload-gemini/"
API_KEY = "tu-api-key"

with open("factura.jpg", "rb") as f:
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        files={"document": f}
    )

print(response.json())
```

### Ejemplo con JavaScript

```javascript
const formData = new FormData();
formData.append('document', fileInput.files[0]);

const response = await fetch('https://tu-app.railway.app/api/invoices-gemini/upload-gemini/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer tu-api-key'
  },
  body: formData
});

const data = await response.json();
console.log(data);
```

---

## 🔒 Seguridad

- ✅ HTTPS forzado en producción
- ✅ HSTS habilitado
- ✅ Cookies seguras
- ✅ Rate limiting (100 req/hora sin auth)
- ✅ API Keys en variables de entorno

---

## 📊 Monitoreo

Railway provee logs automáticamente:
1. Click en tu servicio
2. Ver "Deployments" → Logs

Para más detalle, ajusta `LOG_LEVEL=DEBUG` temporalmente.

