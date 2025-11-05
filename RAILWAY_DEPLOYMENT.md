# 🚀 Deployment en Railway

Este documento explica cómo deployar el Extractor de Comprobantes Argentinos en Railway.

---

## 📋 Prerequisitos

1. Cuenta en [Railway](https://railway.app/)
2. Repositorio en GitHub con el código
3. API Keys necesarias:
   - **LLAMAAPI_KEY**: Tu API key de LlamaCloud
   - **GOOGLE_API_KEY** o credenciales de Service Account para Gemini

---

## 🔧 Configuración de Variables de Entorno en Railway

### Variables Requeridas

```bash
# Django
SECRET_KEY=<tu-secret-key-segura>
DEBUG=False
ALLOWED_HOSTS=*.railway.app,tu-dominio.com

# LlamaCloud
LLAMAAPI_KEY=llx-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Database (Railway provee automáticamente DATABASE_URL si usas Railway Postgres)
DATABASE_URL=postgresql://...  # Auto-generado por Railway

# CORS
CORS_ALLOWED_ORIGINS=https://tu-frontend.com,https://otro-dominio.com
```

### Variables para Gemini (Opción 1: API Key - Más Simple)

```bash
GOOGLE_API_KEY=AIzaSy...
```

### Variables para Gemini (Opción 2: Service Account - Recomendado para Producción)

Para usar el Service Account en Railway, necesitas convertir el archivo JSON a una variable de entorno:

```bash
# En Railway, crea esta variable con el contenido COMPLETO del archivo JSON:
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"TU_PROJECT_ID",...}
```

**Cómo obtener el contenido del JSON:**

```bash
# En tu máquina local (usa el script helper):
./convert_json_for_railway.sh factura-json-apikeys.json

# O manualmente:
cat factura-json-apikeys.json | tr -d '\n'
```

Copia todo el output y pégalo como el valor de `GOOGLE_SERVICE_ACCOUNT_JSON` en Railway.

**Opcional (para Service Account):**

```bash
GOOGLE_CLOUD_PROJECT=TU_PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1
```

---

## 📁 Archivos Necesarios

### 1. `Procfile` (Para Railway)

Crea un archivo `Procfile` en la raíz del proyecto:

```
web: gunicorn extractor_project.wsgi --log-file -
```

### 2. `runtime.txt` (Opcional)

Especifica la versión de Python:

```
python-3.13.0
```

### 3. Actualizar `requirements.txt`

Asegúrate de tener estas dependencias:

```bash
# Agregar si no están:
gunicorn>=21.2.0
psycopg2-binary>=2.9.9  # Para PostgreSQL
whitenoise>=6.6.0  # Para servir archivos estáticos
```

### 4. Actualizar `settings.py`

```python
# En extractor_project/settings.py

import os
import dj_database_url

# Security
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')

# Database
# Railway provee DATABASE_URL automáticamente si usas Railway Postgres
DATABASES = {
    'default': dj_database_url.config(
        default=os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600
    )
}

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Middleware (agregar WhiteNoise)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← Agregar después de SecurityMiddleware
    # ... resto de middleware
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
}
```

---

## 🚂 Pasos de Deployment en Railway

### 1. Crear Nuevo Proyecto

1. Ve a [Railway](https://railway.app/)
2. Click en **"New Project"**
3. Selecciona **"Deploy from GitHub repo"**
4. Selecciona tu repositorio

### 2. Agregar PostgreSQL (Recomendado)

1. En tu proyecto de Railway, click en **"+ New"**
2. Selecciona **"Database" → "PostgreSQL"**
3. Railway automáticamente creará la variable `DATABASE_URL`

### 3. Configurar Variables de Entorno

1. Click en tu servicio web
2. Ve a **"Variables"**
3. Agrega todas las variables listadas arriba

**Para Gemini con Service Account:**

⚠️ **IMPORTANTE:** Reemplaza los valores con tus credenciales reales.

```bash
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"TU_PROJECT_ID","private_key_id":"TU_PRIVATE_KEY_ID","private_key":"-----BEGIN PRIVATE KEY-----\nTU_PRIVATE_KEY_AQUI\n-----END PRIVATE KEY-----\n","client_email":"TU_SERVICE_ACCOUNT@TU_PROJECT.iam.gserviceaccount.com","client_id":"TU_CLIENT_ID","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"https://www.googleapis.com/robot/v1/metadata/x509/TU_SERVICE_ACCOUNT%40TU_PROJECT.iam.gserviceaccount.com","universe_domain":"googleapis.com"}
```

**O mejor aún, usa el script helper:**

```bash
# Copia tu factura-json-apikeys.json y ejecuta:
./convert_json_for_railway.sh factura-json-apikeys.json
```

Esto generará el valor correcto para pegar en Railway sin exponer tus credenciales.

### 4. Configurar Build & Deploy

Railway detectará automáticamente que es un proyecto Python/Django.

Si necesitas comandos customizados, ve a **"Settings" → "Deploy"**:

**Build Command:**
```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start Command:**
```bash
gunicorn extractor_project.wsgi --log-file -
```

### 5. Deploy

Railway automáticamente hará deploy cuando hagas push a tu rama principal (main/master).

---

## 🔐 Verificar que Gemini Funciona

Una vez deployado, revisa los logs en Railway:

```
✅ Deberías ver:
   🔐 Usando Service Account desde variable de entorno JSON
   ✅ GenAI Client inicializado con Service Account (JSON env var)
```

---

## 📊 Monitoreo

### Ver Logs en Railway

1. Click en tu servicio
2. Ve a **"Deployments"**
3. Click en el deployment activo
4. Ve a **"Logs"**

### Métricas Disponibles

En el Django Admin (`tu-dominio.railway.app/admin`):

- Dashboard con estadísticas de extracción
- % de facturas que usaron Gemini retry
- Tiempo promedio de procesamiento
- Score promedio de validación
- Total facturado

---

## 🐛 Troubleshooting

### Error: "Missing LLAMAAPI_KEY"
- Verifica que `LLAMAAPI_KEY` esté configurada en Railway Variables

### Error: "Error inicializando GenAI Client"
- Si usas API Key: Verifica `GOOGLE_API_KEY`
- Si usas Service Account: Verifica que `GOOGLE_SERVICE_ACCOUNT_JSON` tenga el JSON completo y correcto

### Error: "DisallowedHost"
- Agrega tu dominio de Railway a `ALLOWED_HOSTS`
- Ejemplo: `ALLOWED_HOSTS=*.railway.app,tu-dominio.com`

### Error: Base de datos
- Verifica que `DATABASE_URL` esté configurada
- Si usas Railway Postgres, debe estar automáticamente configurada

### Media files no se guardan
- Railway tiene filesystem efímero
- Considera usar S3, Cloudinary o similar para archivos
- Alternativa: Usar Railway Volumes

---

## 🔄 CI/CD Automático

Railway hace deploy automáticamente cuando:
1. Haces push a la rama configurada (main/master)
2. Detecta cambios en el código

Para desactivar auto-deploy:
- Ve a **"Settings" → "Service" → "Deploy"**
- Desactiva **"Auto Deploy"**

---

## 📝 Checklist de Deployment

- [ ] Variables de entorno configuradas en Railway
- [ ] `GOOGLE_SERVICE_ACCOUNT_JSON` o `GOOGLE_API_KEY` configurada
- [ ] PostgreSQL agregado y `DATABASE_URL` disponible
- [ ] `gunicorn` en requirements.txt
- [ ] `Procfile` creado
- [ ] `settings.py` actualizado para producción
- [ ] `DEBUG=False` en Railway
- [ ] `ALLOWED_HOSTS` configurado correctamente
- [ ] Migraciones ejecutadas: `python manage.py migrate`
- [ ] Static files recolectados: `python manage.py collectstatic`
- [ ] Crear superuser: `python manage.py createsuperuser`

---

## 🚀 Post-Deployment

### Crear Superuser

Desde Railway CLI o usando Railway Shell:

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link al proyecto
railway link

# Abrir shell
railway run python manage.py createsuperuser
```

O desde la interfaz de Railway:
1. Ve a tu servicio
2. Click en **"..."** → **"Shell"**
3. Ejecuta: `python manage.py createsuperuser`

---

## 💡 Tips

1. **Logs**: Siempre revisa los logs para debugging
2. **Variables sensibles**: Nunca commitees `.env` al repo
3. **Gemini**: La opción Service Account es más estable para producción
4. **Backups**: Railway hace backups automáticos de Postgres
5. **Escalado**: Railway permite escalar vertical y horizontalmente según necesites

---

## 📚 Recursos

- [Railway Docs](https://docs.railway.app/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Gunicorn Configuration](https://docs.gunicorn.org/en/stable/configure.html)

---

**¡Tu extractor de facturas está listo en producción!** 🎉



