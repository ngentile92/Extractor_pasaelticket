#!/bin/bash

# Script para convertir factura-json-apikeys.json a formato Railway
# Uso: ./convert_json_for_railway.sh

echo "=========================================="
echo "🚂 Convertidor JSON para Railway"
echo "=========================================="
echo ""

if [ ! -f "factura-json-apikeys.json" ]; then
    echo "❌ Error: No se encontró factura-json-apikeys.json"
    echo "   Asegúrate de estar en el directorio del proyecto"
    exit 1
fi

echo "📋 Contenido del archivo (comprimido):"
echo ""
echo "GOOGLE_SERVICE_ACCOUNT_JSON="
cat factura-json-apikeys.json | tr -d '\n' | tr -d ' '
echo ""
echo ""

echo "=========================================="
echo "✅ Copia todo desde 'GOOGLE_SERVICE_ACCOUNT_JSON=' hacia arriba"
echo "   (incluye el '=' y todo el JSON sin espacios)"
echo ""
echo "📝 En Railway:"
echo "   1. Ve a tu proyecto → Variables"
echo "   2. Agregar variable:"
echo "      Name: GOOGLE_SERVICE_ACCOUNT_JSON"
echo "      Value: <pega aquí todo el JSON sin saltos de línea>"
echo "   3. Guarda y redeploy"
echo "=========================================="



