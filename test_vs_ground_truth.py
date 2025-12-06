#!/usr/bin/env python3
"""
🧪 Test de extracción comparando contra Ground Truth

Compara los resultados de extracción de Gemini contra valores verificados manualmente.
"""

import json
import sys
import os
import requests
from typing import Dict, Any, List, Tuple

# Ground truth files
GROUND_TRUTH = {
    'Ejemplo1.jpeg': 'ground_truth_ejemplo1.json',
    'Ejemplo2.jpeg': 'ground_truth_ejemplo2.json',
}

API_URL = "http://127.0.0.1:8000/api/invoices-gemini/upload-gemini/"


def load_ground_truth(filename: str) -> Dict[str, Any]:
    """Carga el ground truth de un archivo."""
    with open(filename) as f:
        return json.load(f)


def extract_invoice(image_path: str) -> Dict[str, Any]:
    """Extrae factura usando la API y obtiene el resultado formateado."""
    # Paso 1: Subir y extraer
    with open(image_path, 'rb') as f:
        response = requests.post(API_URL, files={'document': f})
    
    upload_result = response.json()
    
    if upload_result.get('status') != 'completed':
        return upload_result
    
    # Paso 2: Obtener datos formateados con GET
    invoice_id = upload_result.get('id')
    if invoice_id:
        get_response = requests.get(f"http://127.0.0.1:8000/api/invoices/{invoice_id}/")
        return get_response.json()
    
    return upload_result


def compare_values(expected: Any, actual: Any, path: str = "") -> List[str]:
    """Compara valores y retorna lista de diferencias."""
    differences = []
    
    if expected is None and actual is None:
        return []
    
    if type(expected) != type(actual):
        # Permitir comparar int/float
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            if abs(float(expected) - float(actual)) > 0.01:
                differences.append(f"{path}: {expected} vs {actual}")
        else:
            differences.append(f"{path}: tipo diferente {type(expected).__name__} vs {type(actual).__name__}")
        return differences
    
    if isinstance(expected, dict):
        all_keys = set(expected.keys()) | set(actual.keys())
        for key in all_keys:
            new_path = f"{path}.{key}" if path else key
            exp_val = expected.get(key)
            act_val = actual.get(key)
            differences.extend(compare_values(exp_val, act_val, new_path))
    
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            differences.append(f"{path}: longitud diferente {len(expected)} vs {len(actual)}")
        for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
            differences.extend(compare_values(exp_item, act_item, f"{path}[{i}]"))
    
    elif isinstance(expected, (int, float)):
        if abs(float(expected) - float(actual)) > 0.01:
            differences.append(f"{path}: {expected} vs {actual}")
    
    elif isinstance(expected, str):
        if expected.strip().upper() != str(actual).strip().upper():
            differences.append(f"{path}: '{expected}' vs '{actual}'")
    
    return differences


def compare_items(gt_items: List[Dict], extracted_items: List[Dict]) -> Dict[str, Any]:
    """Compara items de factura con análisis detallado."""
    
    results = {
        'count_match': len(gt_items) == len(extracted_items),
        'gt_count': len(gt_items),
        'extracted_count': len(extracted_items),
        'item_matches': [],
        'total_score': 0.0
    }
    
    # Para cada item del ground truth, buscar el mejor match en extraídos
    for i, gt_item in enumerate(gt_items):
        gt_desc = gt_item.get('descripcion', '').upper()
        gt_cantidad = float(gt_item.get('cantidad', 0))
        gt_precio = float(gt_item.get('precio_unitario', 0))
        gt_subtotal = float(gt_item.get('subtotal', 0))
        
        best_match = None
        best_score = 0
        
        for j, ext_item in enumerate(extracted_items):
            ext_desc = str(ext_item.get('descripcion', '')).upper()
            ext_cantidad = float(ext_item.get('cantidad', 0) or 0)
            ext_precio = float(ext_item.get('precio_unitario', 0) or 0)
            ext_subtotal = float(ext_item.get('subtotal', 0) or 0)
            
            score = 0
            
            # Descripción similar
            if gt_desc[:10] in ext_desc or ext_desc[:10] in gt_desc:
                score += 25
            
            # Cantidad exacta
            if abs(gt_cantidad - ext_cantidad) < 0.01:
                score += 25
            elif abs(gt_cantidad - ext_cantidad) < 1:
                score += 10
            
            # Precio unitario (tolerancia 1%)
            if gt_precio > 0 and abs(gt_precio - ext_precio) / gt_precio < 0.01:
                score += 25
            elif gt_precio > 0 and abs(gt_precio - ext_precio) / gt_precio < 0.05:
                score += 10
            
            # Subtotal (tolerancia 1%)
            if gt_subtotal > 0 and abs(gt_subtotal - ext_subtotal) / gt_subtotal < 0.01:
                score += 25
            elif gt_subtotal > 0 and abs(gt_subtotal - ext_subtotal) / gt_subtotal < 0.05:
                score += 10
            
            if score > best_score:
                best_score = score
                best_match = {
                    'index': j,
                    'descripcion': ext_desc,
                    'cantidad': ext_cantidad,
                    'precio': ext_precio,
                    'subtotal': ext_subtotal
                }
        
        results['item_matches'].append({
            'gt_index': i,
            'gt_descripcion': gt_desc,
            'gt_cantidad': gt_cantidad,
            'gt_precio': gt_precio,
            'gt_subtotal': gt_subtotal,
            'match': best_match,
            'score': best_score
        })
        results['total_score'] += best_score
    
    if gt_items:
        results['total_score'] = results['total_score'] / (len(gt_items) * 100) * 100
    
    return results


def print_comparison(image_name: str, gt: Dict, extracted: Dict):
    """Imprime comparación detallada."""
    
    print(f"\n{'='*80}")
    print(f"📊 COMPARACIÓN: {image_name}")
    print(f"{'='*80}")
    
    # Datos básicos
    gt_factura = gt.get('factura', {})
    ext_factura = extracted.get('factura', {})
    
    # Documento
    print(f"\n📋 DOCUMENTO:")
    gt_doc = gt_factura.get('documento', {})
    ext_doc = ext_factura.get('documento', {})
    
    fields = ['tipo', 'codigo', 'numero', 'fecha_emision', 'cae']
    for field in fields:
        gt_val = gt_doc.get(field, 'N/A')
        ext_val = ext_doc.get(field, 'N/A')
        match = "✅" if str(gt_val).upper() == str(ext_val).upper() else "❌"
        print(f"   {field:20} GT: {str(gt_val):30} EXT: {str(ext_val):30} {match}")
    
    # Emisor
    print(f"\n🏢 EMISOR:")
    gt_emisor = gt_factura.get('emisor', {})
    ext_emisor = ext_factura.get('emisor', {})
    
    fields = ['razon_social', 'cuit', 'condicion_iva']
    for field in fields:
        gt_val = gt_emisor.get(field, 'N/A')
        ext_val = ext_emisor.get(field, 'N/A')
        match = "✅" if str(gt_val).upper() == str(ext_val).upper() else "❌"
        print(f"   {field:20} GT: {str(gt_val)[:30]:30} EXT: {str(ext_val)[:30]:30} {match}")
    
    # Receptor
    print(f"\n👤 RECEPTOR:")
    gt_receptor = gt_factura.get('receptor', {})
    ext_receptor = ext_factura.get('receptor', {})
    
    for field in ['razon_social', 'cuit', 'condicion_iva']:
        gt_val = gt_receptor.get(field, 'N/A')
        ext_val = ext_receptor.get(field, 'N/A')
        match = "✅" if str(gt_val).upper() == str(ext_val).upper() else "❌"
        print(f"   {field:20} GT: {str(gt_val)[:30]:30} EXT: {str(ext_val)[:30]:30} {match}")
    
    # Items
    print(f"\n📦 ITEMS:")
    gt_items = gt_factura.get('items', [])
    ext_items = ext_factura.get('items', [])
    
    print(f"   Cantidad GT: {len(gt_items)}, Extraídos: {len(ext_items)}")
    
    items_comparison = compare_items(gt_items, ext_items)
    print(f"   Score items: {items_comparison['total_score']:.1f}%")
    
    # Mostrar items con problemas
    print(f"\n   Detalle items:")
    for match in items_comparison['item_matches']:
        score = match['score']
        icon = "✅" if score >= 75 else "⚠️" if score >= 50 else "❌"
        print(f"   {icon} Item {match['gt_index']+1}: {match['gt_descripcion'][:40]:40} | "
              f"Cant: {match['gt_cantidad']} | Precio: ${match['gt_precio']:,.2f} | "
              f"Subtotal: ${match['gt_subtotal']:,.2f} | Score: {score}%")
        
        if match['match'] and score < 100:
            ext = match['match']
            print(f"      ↳ Extraído: Cant: {ext['cantidad']} | Precio: ${ext['precio']:,.2f} | "
                  f"Subtotal: ${ext['subtotal']:,.2f}")
    
    # Totales
    print(f"\n💰 TOTALES:")
    gt_totales = gt_factura.get('totales', {})
    ext_totales = ext_factura.get('totales', {})
    
    for field in ['subtotal_gravado', 'importe_total']:
        gt_val = gt_totales.get(field, 0)
        ext_val = ext_totales.get(field, 0)
        try:
            gt_num = float(gt_val or 0)
            ext_num = float(ext_val or 0)
            diff = abs(gt_num - ext_num)
            match = "✅" if diff < 1 else "⚠️" if diff < 100 else "❌"
            print(f"   {field:20} GT: ${gt_num:>15,.2f}  EXT: ${ext_num:>15,.2f}  Diff: ${diff:,.2f} {match}")
        except:
            print(f"   {field:20} GT: {gt_val}  EXT: {ext_val}")
    
    # Score de validación
    print(f"\n📊 VALIDACIÓN:")
    ext_validacion = extracted.get('validacion', {})
    print(f"   Score: {ext_validacion.get('score', 0):.1f}%")
    print(f"   Nivel: {ext_validacion.get('nivel_confianza', 'N/A')}")
    print(f"   Errores: {extracted.get('alertas', {}).get('errores_count', 0)}")
    
    return items_comparison['total_score']


def main():
    """Ejecuta las comparaciones."""
    print("🧪 TEST VS GROUND TRUTH")
    print("=" * 80)
    
    total_score = 0
    tests_run = 0
    
    for image_name, gt_file in GROUND_TRUTH.items():
        if not os.path.exists(gt_file):
            print(f"⚠️ Ground truth no encontrado: {gt_file}")
            continue
        
        if not os.path.exists(image_name):
            print(f"⚠️ Imagen no encontrada: {image_name}")
            continue
        
        print(f"\n🔄 Extrayendo {image_name}...")
        
        try:
            gt = load_ground_truth(gt_file)
            extracted = extract_invoice(image_name)
            
            if extracted.get('status') not in ['completed', None]:  # GET response may not have status
                print(f"❌ Extracción falló: {extracted.get('error_message', 'Unknown error')}")
                continue
            
            if not extracted.get('factura'):
                print(f"❌ No se obtuvo factura: {list(extracted.keys())}")
                continue
            
            score = print_comparison(image_name, gt, extracted)
            total_score += score
            tests_run += 1
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN FINAL")
    print(f"{'='*80}")
    print(f"   Tests ejecutados: {tests_run}")
    print(f"   Score promedio items: {total_score/tests_run if tests_run else 0:.1f}%")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()

