# 🔐 Configuración de Google Gemini para Re-extracción

**Fecha**: 27 de Octubre, 2025

---

## 🎯 **PROBLEMA ACTUAL**

El sistema detecta que necesita re-extraer con Gemini (score < 60%), pero falla con:

```
❌ Error inicializando GenAI Client: Missing key inputs argument!
```

**Causa**: Falta configurar las credenciales de Google Gemini.

---

## ✅ **SOLUCIÓN RECOMENDADA: API Key** (más simple)

### Paso 1: Obtener API Key de Google AI Studio

1. Ve a: **https://aistudio.google.com/apikey**
2. Inicia sesión con tu cuenta de Google
3. Clic en **"Create API Key"**
4. Copia la API Key (empieza con `AIzaSy...`)

### Paso 2: Agregar al `.env`

```bash
# Editar .env
nano .env

# Agregar esta línea:
GOOGLE_API_KEY=AIzaSy...tu-api-key-aqui...
```

### Paso 3: Reiniciar el servidor

```bash
# Matar proceso actual
lsof -ti:8000 | xargs kill -9

# Reiniciar
source venv/bin/activate
python manage.py runserver
```

---

## 🧪 **VERIFICAR QUE FUNCIONA**

### Subir factura de prueba:

```bash
curl -X POST http://127.0.0.1:8000/api/invoices/process/ \
  -F "document=@Ejemplo2.jpeg"
```

### Buscar en el log del servidor:

```
✅ ÉXITO - Deberías ver:
   🔐 Usando Google API Key: AIzaSy...
   ✅ GenAI Client inicializado con API Key
   
   Y luego (si score < 60%):
   🔄 RE-EXTRACCIÓN CON GEMINI (errores matemáticos detectados)
   📤 Subiendo JPEG con File API: Ejemplo2.jpeg
   ✅ Archivo subido y cached
   🚀 Llamando a Gemini 2.5 Flash con schema estructurado...
   ✅ Gemini extrajo X items correctamente
   
   ⚖️ COMPARACIÓN DE RESULTADOS
      LlamaExtract: XX% (X errores)
      Gemini:       YY% (Y errores)
   ✅ GEMINI GANÓ! Mejora: +ZZ.Zpp
```

```
❌ FALLA - Si sigues viendo:
   ❌ Error inicializando GenAI Client: Missing key inputs argument!
   
   → Verificar que el .env tenga GOOGLE_API_KEY correctamente configurado
   → Verificar que reiniciaste el servidor después de agregar la key
```

---

## 🔧 **ALTERNATIVA: Service Account** (para producción con Vertex AI)

Si prefieres usar el Service Account que ya tienes (`factura-json-apikeys.json`):

### Paso 1: Habilitar Vertex AI API

1. Ve a: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
2. Selecciona tu proyecto de Google Cloud
3. Clic en **"ENABLE"**

### Paso 2: Configurar `.env`

Agrega la ruta a tu archivo de credenciales:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/tu-service-account-key.json
```

### Paso 3: Agregar location (opcional)

```bash
# Agregar al .env (opcional, default es us-central1)
GOOGLE_CLOUD_LOCATION=us-central1
```

### Paso 4: Reiniciar servidor

```bash
lsof -ti:8000 | xargs kill -9
source venv/bin/activate
python manage.py runserver
```

### Log esperado con Service Account:

```
🔐 Usando Vertex AI con Service Account: .../tu-service-account-key.json
   Project ID: tu-project-id
✅ GenAI Client inicializado con Vertex AI (location: us-central1)
```

---

## 📊 **MÉTRICAS DE MEJORA**

Cuando Gemini esté funcionando, verás mejoras como:

### Antes (solo LlamaExtract):
```json
{
  "validation_score": "0.4500",  // 45%
  "validation_errors": [
    "Subtotal incorrecto: cantidad (8.0) × precio ($6598.35) = $52786.80, pero declarado $39590.10",
    "Subtotal incorrecto: cantidad (6.0) × precio ($6837.02) = $41022.12, pero declarado $27318.08",
    // ... 6 errores más
  ]
}
```

### Después (con Gemini retry):
```json
{
  "validation_score": "0.8900",  // 89% ✅ (+44pp)
  "validation_errors": [
    "Formato de fecha inválido",
    // Solo 1-2 errores menores
  ],
  "processing_metadata": {
    "gemini_retry": {
      "was_retried": true,
      "first_score": 0.45,
      "second_score": 0.89,
      "improvement": 44.0,  // ✅ Mejora de 44 puntos porcentuales
      "method_used": "gemini"
    }
  }
}
```

---

## 🎯 **RECOMENDACIÓN**

**Para desarrollo local**: Usa **API Key** (más rápido y simple)
**Para producción**: Usa **Service Account con Vertex AI** (más seguro y escalable)

---

## 💡 **PRÓXIMOS PASOS**

1. ✅ Configurar `GOOGLE_API_KEY` en `.env`
2. ✅ Reiniciar servidor
3. ✅ Subir `Ejemplo2.jpeg` para probar
4. ✅ Verificar logs y mejora en score
5. 📊 Monitorear % de facturas que necesitan Gemini retry

---

## 🆘 **TROUBLESHOOTING**

### Error: "API key not valid"
- Verificar que copiaste la key completa
- Generar una nueva key en AI Studio

### Error: "Vertex AI API not enabled"
- Habilitar API en: https://console.cloud.google.com/apis/library/aiplatform.googleapis.com
- Esperar 1-2 minutos para propagación

### Error: "Permission denied"
- Service Account debe tener rol: `Vertex AI User`
- Agregar rol en: https://console.cloud.google.com/iam-admin/iam

---

**¡Configura GOOGLE_API_KEY y estarás listo!** 🚀

