#!/bin/bash
# Script para resetear la base de datos de desarrollo

echo "🗑️  Eliminando base de datos SQLite existente..."
rm -f db.sqlite3

echo "🗑️  Eliminando migraciones anteriores..."
rm -f invoice_extractor/migrations/0*.py

echo "✅ Base de datos eliminada. Ahora ejecuta:"
echo ""
echo "   python manage.py makemigrations"
echo "   python manage.py migrate"
echo "   python manage.py createsuperuser  # (opcional)"
echo ""

