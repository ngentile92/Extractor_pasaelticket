#!/usr/bin/env python
"""
Test script for modular invoice extraction

This script demonstrates how to use the modular extraction feature
to extract only specific segments from an invoice document.

Usage:
    python test_modular_extraction.py <file_path> [segments...]

Examples:
    # Extract everything (default)
    python test_modular_extraction.py invoice.pdf

    # Extract only items and documento
    python test_modular_extraction.py invoice.pdf items documento

    # Extract only partes
    python test_modular_extraction.py invoice.pdf partes

    # Extract fiscalidad and documento
    python test_modular_extraction.py invoice.pdf fiscalidad documento
"""

import os
import sys
import json
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'extractor_project.settings')
import django
django.setup()

from invoice_extractor.services import InvoiceExtractionService
from invoice_extractor.schemas import SchemaComposer


def print_available_segments():
    """Print available segments"""
    segments = SchemaComposer.get_available_segments()
    print("📋 Available segments:")
    print("  - items: Line items / productos")
    print("  - partes: Emisor y receptor y sus datos")
    print("  - documento: Datos del documento en sí")
    print("  - fiscalidad: Totales e impuestos (includes totales)")
    print("  - totales: Totales varios (solo si fiscalidad no está incluida)")
    print()


def test_extraction(file_path: str, segments: list = None):
    """
    Test invoice extraction with specified segments
    
    Args:
        file_path: Path to the invoice document
        segments: List of segments to extract (None = extract all)
    """
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return
    
    # Determine schema type
    if segments and segments != ['all']:
        schema_type = 'modular'
        print(f"🔧 Using MODULAR extraction with segments: {segments}")
    else:
        schema_type = 'completo'
        segments = None
        print("🔧 Using COMPLETE extraction (all segments)")
    
    print(f"📄 Processing file: {file_path}")
    print()
    
    # Initialize service
    service = InvoiceExtractionService(schema_type=schema_type, segments=segments)
    
    # Extract data
    print("⏳ Extracting data...")
    result = service.extract_invoice_data(file_path)
    
    if result['success']:
        print("✅ Extraction successful!")
        print()
        
        # Print metadata
        metadata = result.get('metadata', {})
        print("📊 Metadata:")
        print(f"  - Extraction time: {metadata.get('extraction_time', 0):.2f} seconds")
        print(f"  - Schema type: {metadata.get('schema_type', 'N/A')}")
        print(f"  - Agent name: {metadata.get('agent_name', 'N/A')}")
        if 'segments' in metadata:
            print(f"  - Segments extracted: {', '.join(metadata['segments'])}")
        print()
        
        # Print extracted data structure
        data = result.get('data', {})
        print("📦 Extracted data structure:")
        for key in data.keys():
            print(f"  ✓ {key}")
        print()
        
        # Print sample of each segment
        print("📝 Sample data:")
        print()
        
        if 'items' in data:
            items = data['items']
            print(f"  🛒 ITEMS ({len(items)} items):")
            for i, item in enumerate(items[:3], 1):
                print(f"    {i}. {item.get('descripcion', 'N/A')} - ${item.get('precio_unitario', 0)}")
            if len(items) > 3:
                print(f"    ... and {len(items) - 3} more items")
            print()
        
        if 'partes' in data:
            partes = data['partes']
            print("  👥 PARTES:")
            if 'empresa' in partes:
                empresa = partes['empresa']
                print(f"    📍 Empresa: {empresa.get('razon_social', 'N/A')}")
                print(f"       CUIT: {empresa.get('cuit', 'N/A')}")
            if 'cliente' in partes:
                cliente = partes['cliente']
                print(f"    👤 Cliente: {cliente.get('apellido_nombre_razon_social', 'N/A')}")
                print(f"       CUIT: {cliente.get('cuit', 'N/A')}")
            print()
        
        if 'documento' in data:
            documento = data['documento']
            print("  📄 DOCUMENTO:")
            print(f"    Tipo: {documento.get('tipo_comprobante', 'N/A')}")
            print(f"    Número: {documento.get('numero_comprobante', 'N/A')}")
            print(f"    Fecha: {documento.get('fecha_emision', 'N/A')}")
            print(f"    CAE: {documento.get('cae', 'N/A')}")
            print()
        
        if 'fiscalidad' in data:
            fiscalidad = data['fiscalidad']
            totales = fiscalidad.get('totales', {})
            print("  💰 FISCALIDAD:")
            print(f"    Subtotal: ${totales.get('subtotal_gravado', 0):,.2f}")
            print(f"    Descuentos: ${totales.get('descuentos', 0):,.2f}")
            print(f"    Total: ${totales.get('importe_total', 0):,.2f}")
            print()
        elif 'totales' in data:
            totales = data['totales']
            print("  💰 TOTALES:")
            print(f"    Subtotal: ${totales.get('subtotal_gravado', 0):,.2f}")
            print(f"    Descuentos: ${totales.get('descuentos', 0):,.2f}")
            print(f"    Total: ${totales.get('importe_total', 0):,.2f}")
            print()
        
        # Save result to JSON file
        output_file = f"extraction_result_{'_'.join(segments) if segments else 'complete'}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"💾 Full result saved to: {output_file}")
        
    else:
        print("❌ Extraction failed!")
        print(f"Error: {result.get('error', 'Unknown error')}")


def main():
    """Main function"""
    print("=" * 80)
    print("🧪 MODULAR INVOICE EXTRACTION TEST")
    print("=" * 80)
    print()
    
    # Check arguments
    if len(sys.argv) < 2:
        print("Usage: python test_modular_extraction.py <file_path> [segments...]")
        print()
        print_available_segments()
        print("Examples:")
        print("  python test_modular_extraction.py invoice.pdf")
        print("  python test_modular_extraction.py invoice.pdf items documento")
        print("  python test_modular_extraction.py invoice.pdf partes")
        sys.exit(1)
    
    file_path = sys.argv[1]
    segments = sys.argv[2:] if len(sys.argv) > 2 else None
    
    if segments:
        # Validate segments
        available = SchemaComposer.get_available_segments()
        invalid = set(segments) - available - {'all'}
        if invalid:
            print(f"❌ Invalid segments: {invalid}")
            print()
            print_available_segments()
            sys.exit(1)
    
    # Run extraction
    test_extraction(file_path, segments)


if __name__ == '__main__':
    main()

