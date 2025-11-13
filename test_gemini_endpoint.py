"""
Script de testing para el endpoint Gemini

Este script realiza pruebas del nuevo endpoint /api/invoices-gemini/upload-gemini/
y compara resultados con el endpoint principal /api/invoices/process/
"""

import requests
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple


BASE_URL = "http://localhost:8000/api"
COMPARISONS_DIR = Path("comparaciones_gemini_vs_llama")
EJEMPLOS = [
    "Ejemplo1.jpeg",
    "Ejemplo2.jpeg",
    "Ejemplo3.jpeg"
]


def compare_values(llama_val, gemini_val, field_name: str) -> Tuple[bool, str]:
    """
    Compara dos valores y retorna si son iguales y una descripción de la diferencia.
    """
    # Normalizar None y valores vacíos
    llama_normalized = llama_val if llama_val not in [None, "", [], {}] else None
    gemini_normalized = gemini_val if gemini_val not in [None, "", [], {}] else None
    
    if llama_normalized == gemini_normalized:
        return True, ""
    
    # Para números, considerar diferencias pequeñas como iguales
    if isinstance(llama_normalized, (int, float)) and isinstance(gemini_normalized, (int, float)):
        diff = abs(llama_normalized - gemini_normalized)
        if diff < 0.01:  # Diferencia menor a 1 centavo
            return True, ""
    
    # Generar descripción de la diferencia
    diff_desc = f"**{field_name}**\n"
    diff_desc += f"  - LlamaExtract: `{llama_normalized}`\n"
    diff_desc += f"  - Gemini: `{gemini_normalized}`\n"
    
    return False, diff_desc


def compare_items(llama_items: List[Dict], gemini_items: List[Dict]) -> Tuple[int, List[str]]:
    """
    Compara los items extraídos.
    Retorna: (diferencias_count, lista_de_diferencias)
    """
    differences = []
    diff_count = 0
    
    # Comparar cantidad de items
    if len(llama_items) != len(gemini_items):
        differences.append(f"### ⚠️ Cantidad de Items Diferente\n")
        differences.append(f"- LlamaExtract: {len(llama_items)} items\n")
        differences.append(f"- Gemini: {len(gemini_items)} items\n\n")
        diff_count += 1
    
    # Comparar cada item
    max_items = max(len(llama_items), len(gemini_items))
    for i in range(max_items):
        item_diffs = []
        
        llama_item = llama_items[i] if i < len(llama_items) else {}
        gemini_item = gemini_items[i] if i < len(gemini_items) else {}
        
        if not llama_item or not gemini_item:
            differences.append(f"### ⚠️ Item {i+1}: Falta en {'Gemini' if not gemini_item else 'LlamaExtract'}\n\n")
            diff_count += 1
            continue
        
        # Comparar campos del item
        fields = ['codigo', 'descripcion', 'cantidad', 'unidad_medida', 'precio_unitario', 'subtotal']
        for field in fields:
            llama_val = llama_item.get(field)
            gemini_val = gemini_item.get(field)
            
            is_equal, diff_desc = compare_values(llama_val, gemini_val, field)
            if not is_equal:
                item_diffs.append(diff_desc)
                diff_count += 1
        
        if item_diffs:
            differences.append(f"### 📦 Item {i+1}\n")
            differences.extend(item_diffs)
            differences.append("\n")
    
    return diff_count, differences


def compare_documento(llama_doc: Dict, gemini_doc: Dict) -> Tuple[int, List[str]]:
    """Compara los datos del documento."""
    differences = []
    diff_count = 0
    
    fields = [
        'tipo_comprobante', 'codigo', 'numero_comprobante', 'punto_venta',
        'fecha_emision', 'cae', 'fecha_vencimiento_cae', 'moneda', 'condicion_venta'
    ]
    
    for field in fields:
        llama_val = llama_doc.get(field)
        gemini_val = gemini_doc.get(field)
        
        is_equal, diff_desc = compare_values(llama_val, gemini_val, field)
        if not is_equal:
            differences.append(diff_desc)
            diff_count += 1
    
    return diff_count, differences


def compare_partes(llama_partes: Dict, gemini_partes: Dict) -> Tuple[int, List[str]]:
    """Compara los datos de empresa y cliente."""
    differences = []
    diff_count = 0
    
    # Comparar empresa
    llama_empresa = llama_partes.get('empresa', {})
    gemini_empresa = gemini_partes.get('empresa', {})
    
    empresa_fields = [
        'razon_social', 'cuit', 'condicion_iva', 'provincia', 
        'domicilio_comercial', 'domicilio_calle', 'domicilio_localidad',
        'ingresos_brutos'
    ]
    
    empresa_diffs = []
    for field in empresa_fields:
        llama_val = llama_empresa.get(field)
        gemini_val = gemini_empresa.get(field)
        
        is_equal, diff_desc = compare_values(llama_val, gemini_val, f"empresa.{field}")
        if not is_equal:
            empresa_diffs.append(diff_desc)
            diff_count += 1
    
    if empresa_diffs:
        differences.append("### 🏢 Empresa\n")
        differences.extend(empresa_diffs)
        differences.append("\n")
    
    # Comparar cliente
    llama_cliente = llama_partes.get('cliente', {})
    gemini_cliente = gemini_partes.get('cliente', {})
    
    cliente_fields = [
        'apellido_nombre_razon_social', 'cuit', 'condicion_iva', 
        'provincia', 'domicilio', 'domicilio_calle', 'domicilio_localidad'
    ]
    
    cliente_diffs = []
    for field in cliente_fields:
        llama_val = llama_cliente.get(field)
        gemini_val = gemini_cliente.get(field)
        
        is_equal, diff_desc = compare_values(llama_val, gemini_val, f"cliente.{field}")
        if not is_equal:
            cliente_diffs.append(diff_desc)
            diff_count += 1
    
    if cliente_diffs:
        differences.append("### 👤 Cliente\n")
        differences.extend(cliente_diffs)
        differences.append("\n")
    
    return diff_count, differences


def compare_fiscalidad(llama_fisc: Dict, gemini_fisc: Dict) -> Tuple[int, List[str]]:
    """Compara los datos fiscales."""
    differences = []
    diff_count = 0
    
    # Comparar totales
    llama_totales = llama_fisc.get('totales', {})
    gemini_totales = gemini_fisc.get('totales', {})
    
    totales_fields = ['subtotal_gravado', 'importe_total', 'descuentos']
    totales_diffs = []
    
    for field in totales_fields:
        llama_val = llama_totales.get(field)
        gemini_val = gemini_totales.get(field)
        
        is_equal, diff_desc = compare_values(llama_val, gemini_val, f"totales.{field}")
        if not is_equal:
            totales_diffs.append(diff_desc)
            diff_count += 1
    
    if totales_diffs:
        differences.append("### 💰 Totales\n")
        differences.extend(totales_diffs)
        differences.append("\n")
    
    # Comparar impuestos
    llama_impuestos = llama_fisc.get('impuestos', {})
    gemini_impuestos = gemini_fisc.get('impuestos', {})
    
    # IVA
    llama_iva = llama_impuestos.get('iva', {})
    gemini_iva = gemini_impuestos.get('iva', {})
    
    iva_diffs = []
    all_iva_keys = set(list(llama_iva.keys()) + list(gemini_iva.keys()))
    for key in all_iva_keys:
        llama_val = llama_iva.get(key, 0)
        gemini_val = gemini_iva.get(key, 0)
        
        is_equal, diff_desc = compare_values(llama_val, gemini_val, f"iva.{key}%")
        if not is_equal and (llama_val != 0 or gemini_val != 0):
            iva_diffs.append(diff_desc)
            diff_count += 1
    
    if iva_diffs:
        differences.append("### 📊 IVA\n")
        differences.extend(iva_diffs)
        differences.append("\n")
    
    # Percepciones y retenciones
    impuestos_fields = [
        'percepcion_iva', 'percepcion_ganancias', 'impuestos_internos',
        'retencion_iva', 'retencion_ganancias', 'retencion_suss'
    ]
    
    imp_diffs = []
    for field in impuestos_fields:
        llama_val = llama_impuestos.get(field)
        gemini_val = gemini_impuestos.get(field)
        
        is_equal, diff_desc = compare_values(llama_val, gemini_val, f"impuestos.{field}")
        if not is_equal:
            imp_diffs.append(diff_desc)
            diff_count += 1
    
    if imp_diffs:
        differences.append("### 💸 Percepciones y Retenciones\n")
        differences.extend(imp_diffs)
        differences.append("\n")
    
    # Comparar cálculos
    llama_calculos = llama_fisc.get('calculos', {})
    gemini_calculos = gemini_fisc.get('calculos', {})
    
    calculos_fields = [
        'items_count', 'items_subtotal_total', 'total_iva_calculado',
        'diferencia_matematica'
    ]
    
    calc_diffs = []
    for field in calculos_fields:
        llama_val = llama_calculos.get(field)
        gemini_val = gemini_calculos.get(field)
        
        is_equal, diff_desc = compare_values(llama_val, gemini_val, f"calculos.{field}")
        if not is_equal:
            calc_diffs.append(diff_desc)
            diff_count += 1
    
    if calc_diffs:
        differences.append("### 🧮 Cálculos\n")
        differences.extend(calc_diffs)
        differences.append("\n")
    
    return diff_count, differences


def generate_comparison_report(
    file_name: str,
    llama_response: Dict[str, Any],
    gemini_response: Dict[str, Any]
) -> str:
    """
    Genera un reporte completo de comparación entre LlamaExtract y Gemini.
    
    1. Guarda las respuestas completas en JSONs
    2. Compara los datos extraídos campo por campo
    3. Genera un reporte en Markdown
    
    Retorna la ruta del archivo de reporte generado.
    """
    # Crear directorio si no existe
    COMPARISONS_DIR.mkdir(exist_ok=True)
    
    # Timestamp para archivos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(file_name).stem
    
    # 1. GUARDAR RESPUESTAS COMPLETAS EN JSON
    llama_json_file = COMPARISONS_DIR / f"llama_{base_name}_{timestamp}.json"
    gemini_json_file = COMPARISONS_DIR / f"gemini_{base_name}_{timestamp}.json"
    
    with open(llama_json_file, 'w', encoding='utf-8') as f:
        json.dump(llama_response, f, indent=2, ensure_ascii=False)
    
    with open(gemini_json_file, 'w', encoding='utf-8') as f:
        json.dump(gemini_response, f, indent=2, ensure_ascii=False)
    
    print(f"   📄 JSONs guardados:")
    print(f"      - LlamaExtract: {llama_json_file.name}")
    print(f"      - Gemini: {gemini_json_file.name}")
    
    # Extraer datos para comparación
    llama_data = llama_response.get('data', {})
    gemini_data = gemini_response.get('data', {})
    
    # 2. GENERAR REPORTE MD
    report_file = COMPARISONS_DIR / f"comparacion_{base_name}_{timestamp}.md"
    
    # Iniciar reporte
    report_lines = []
    report_lines.append(f"# 📊 Comparación: LlamaExtract vs Gemini\n\n")
    report_lines.append(f"**Factura**: `{file_name}`  \n")
    report_lines.append(f"**Fecha**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n\n")
    
    # Scores
    llama_score = llama_data.get('metadata', {}).get('validation', {}).get('validation_score', 0)
    gemini_score = gemini_data.get('metadata', {}).get('validation', {}).get('validation_score', 0)
    
    report_lines.append(f"## 🎯 Scores de Validación\n\n")
    report_lines.append(f"| Extractor | Score | Nivel |\n")
    report_lines.append(f"|-----------|-------|-------|\n")
    report_lines.append(f"| LlamaExtract | {llama_score:.1%} | {llama_data.get('metadata', {}).get('validation', {}).get('confidence_level', 'N/A').upper()} |\n")
    report_lines.append(f"| Gemini | {gemini_score:.1%} | {gemini_data.get('metadata', {}).get('validation', {}).get('confidence_level', 'N/A').upper()} |\n\n")
    
    # Tiempos
    llama_time = llama_data.get('metadata', {}).get('extraction', {}).get('extraction_time', 0)
    gemini_time = gemini_data.get('metadata', {}).get('extraction', {}).get('extraction_time', 0)
    
    report_lines.append(f"## ⏱️ Tiempos de Extracción\n\n")
    report_lines.append(f"| Extractor | Tiempo |\n")
    report_lines.append(f"|-----------|--------|\n")
    report_lines.append(f"| LlamaExtract | {llama_time:.2f}s |\n")
    report_lines.append(f"| Gemini | {gemini_time:.2f}s |\n\n")
    
    # Comparaciones detalladas
    total_diffs = 0
    
    # Items
    report_lines.append(f"## 📦 Items\n\n")
    items_diff_count, items_diffs = compare_items(
        llama_data.get('items', []),
        gemini_data.get('items', [])
    )
    
    if items_diffs:
        report_lines.extend(items_diffs)
        total_diffs += items_diff_count
    else:
        report_lines.append("✅ **Sin diferencias**\n\n")
    
    # Documento
    report_lines.append(f"## 📄 Documento\n\n")
    doc_diff_count, doc_diffs = compare_documento(
        llama_data.get('documento', {}),
        gemini_data.get('documento', {})
    )
    
    if doc_diffs:
        report_lines.extend(doc_diffs)
        total_diffs += doc_diff_count
    else:
        report_lines.append("✅ **Sin diferencias**\n\n")
    
    # Partes
    report_lines.append(f"## 👥 Partes (Empresa y Cliente)\n\n")
    partes_diff_count, partes_diffs = compare_partes(
        llama_data.get('partes', {}),
        gemini_data.get('partes', {})
    )
    
    if partes_diffs:
        report_lines.extend(partes_diffs)
        total_diffs += partes_diff_count
    else:
        report_lines.append("✅ **Sin diferencias**\n\n")
    
    # Fiscalidad
    report_lines.append(f"## 💰 Fiscalidad\n\n")
    fisc_diff_count, fisc_diffs = compare_fiscalidad(
        llama_data.get('fiscalidad', {}),
        gemini_data.get('fiscalidad', {})
    )
    
    if fisc_diffs:
        report_lines.extend(fisc_diffs)
        total_diffs += fisc_diff_count
    else:
        report_lines.append("✅ **Sin diferencias**\n\n")
    
    # Resumen
    report_lines.insert(6, f"## 📋 Resumen\n\n")
    report_lines.insert(7, f"**Total de diferencias encontradas**: {total_diffs}\n\n")
    
    if total_diffs == 0:
        report_lines.insert(8, f"✅ **¡Extracción idéntica!** Ambos extractores obtuvieron exactamente los mismos datos.\n\n")
    else:
        report_lines.insert(8, f"⚠️ Se encontraron **{total_diffs} diferencias** entre las extracciones. Revisa los detalles a continuación.\n\n")
    
    report_lines.append(f"---\n\n")
    report_lines.append(f"## 📁 Archivos Relacionados\n\n")
    report_lines.append(f"Para revisar las respuestas completas de cada endpoint:\n\n")
    report_lines.append(f"- **LlamaExtract JSON**: `{llama_json_file.name}`\n")
    report_lines.append(f"- **Gemini JSON**: `{gemini_json_file.name}`\n\n")
    report_lines.append(f"---\n\n")
    report_lines.append(f"📸 **Próximo paso**: Revisar la factura original `{file_name}` junto con los JSONs para determinar qué extractor tuvo razón en cada diferencia.\n")
    
    # 3. GENERAR JSON CON SOLO LAS DIFERENCIAS
    differences_json_file = COMPARISONS_DIR / f"diferencias_{base_name}_{timestamp}.json"
    
    differences_json = {
        "factura": file_name,
        "timestamp": timestamp,
        "total_diferencias": total_diffs,
        "scores": {
            "llama": llama_score,
            "gemini": gemini_score,
            "ganador": "llama" if llama_score > gemini_score else ("gemini" if gemini_score > llama_score else "empate")
        },
        "tiempos": {
            "llama": llama_time,
            "gemini": gemini_time
        },
        "diferencias_por_seccion": {}
    }
    
    # Agregar diferencias de items
    if items_diff_count > 0:
        differences_json["diferencias_por_seccion"]["items"] = []
        for i, llama_item in enumerate(llama_data.get('items', [])):
            gemini_item = gemini_data.get('items', [])[i] if i < len(gemini_data.get('items', [])) else {}
            item_diffs = {}
            
            for field in ['codigo', 'descripcion', 'cantidad', 'unidad_medida', 'precio_unitario', 'subtotal']:
                if llama_item.get(field) != gemini_item.get(field):
                    item_diffs[field] = {
                        "llama": llama_item.get(field),
                        "gemini": gemini_item.get(field)
                    }
            
            if item_diffs:
                differences_json["diferencias_por_seccion"]["items"].append({
                    "item_index": i,
                    "diferencias": item_diffs
                })
    
    # Agregar diferencias de documento
    if doc_diff_count > 0:
        differences_json["diferencias_por_seccion"]["documento"] = {}
        for field in ['tipo_comprobante', 'codigo', 'numero_comprobante', 'punto_venta', 'fecha_emision', 'cae']:
            llama_val = llama_data.get('documento', {}).get(field)
            gemini_val = gemini_data.get('documento', {}).get(field)
            if llama_val != gemini_val:
                differences_json["diferencias_por_seccion"]["documento"][field] = {
                    "llama": llama_val,
                    "gemini": gemini_val
                }
    
    # Agregar diferencias de partes
    if partes_diff_count > 0:
        differences_json["diferencias_por_seccion"]["partes"] = {}
        
        # Empresa
        empresa_diffs = {}
        llama_empresa = llama_data.get('partes', {}).get('empresa', {})
        gemini_empresa = gemini_data.get('partes', {}).get('empresa', {})
        for field in ['razon_social', 'cuit', 'condicion_iva', 'provincia', 'domicilio_comercial']:
            if llama_empresa.get(field) != gemini_empresa.get(field):
                empresa_diffs[field] = {
                    "llama": llama_empresa.get(field),
                    "gemini": gemini_empresa.get(field)
                }
        if empresa_diffs:
            differences_json["diferencias_por_seccion"]["partes"]["empresa"] = empresa_diffs
        
        # Cliente
        cliente_diffs = {}
        llama_cliente = llama_data.get('partes', {}).get('cliente', {})
        gemini_cliente = gemini_data.get('partes', {}).get('cliente', {})
        for field in ['apellido_nombre_razon_social', 'cuit', 'condicion_iva', 'provincia', 'domicilio']:
            if llama_cliente.get(field) != gemini_cliente.get(field):
                cliente_diffs[field] = {
                    "llama": llama_cliente.get(field),
                    "gemini": gemini_cliente.get(field)
                }
        if cliente_diffs:
            differences_json["diferencias_por_seccion"]["partes"]["cliente"] = cliente_diffs
    
    # Agregar diferencias de fiscalidad
    if fisc_diff_count > 0:
        differences_json["diferencias_por_seccion"]["fiscalidad"] = {}
        
        # Totales
        llama_totales = llama_data.get('fiscalidad', {}).get('totales', {})
        gemini_totales = gemini_data.get('fiscalidad', {}).get('totales', {})
        for field in ['subtotal_gravado', 'importe_total', 'descuentos']:
            if llama_totales.get(field) != gemini_totales.get(field):
                if "totales" not in differences_json["diferencias_por_seccion"]["fiscalidad"]:
                    differences_json["diferencias_por_seccion"]["fiscalidad"]["totales"] = {}
                differences_json["diferencias_por_seccion"]["fiscalidad"]["totales"][field] = {
                    "llama": llama_totales.get(field),
                    "gemini": gemini_totales.get(field)
                }
    
    # Guardar JSON de diferencias
    with open(differences_json_file, 'w', encoding='utf-8') as f:
        json.dump(differences_json, f, indent=2, ensure_ascii=False)
    
    print(f"      - Diferencias JSON: {differences_json_file.name}")
    
    # Guardar reporte
    with open(report_file, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    return str(report_file)


def test_gemini_extraction(file_path, schema_type="completo", segments=None):
    """
    Test de extracción con Gemini
    """
    print("\n" + "=" * 80)
    print(f"🧪 TEST: {Path(file_path).name}")
    print("=" * 80)
    
    url = f"{BASE_URL}/invoices-gemini/upload-gemini/"
    
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'schema_type': schema_type}
        
        if segments:
            data['segments'] = json.dumps(segments)
        
        print(f"📤 Enviando request a {url}")
        print(f"   Schema: {schema_type}")
        if segments:
            print(f"   Segmentos: {segments}")
        
        try:
            response = requests.post(url, files=files, data=data, timeout=180)
            
            print(f"\n📥 Response Status: {response.status_code}")
            
            if response.status_code == 201:
                result = response.json()
                
                print("\n✅ EXTRACCIÓN EXITOSA")
                print(f"   Invoice ID: {result['id']}")
                print(f"   Status: {result['status']}")
                print(f"   Message: {result['message']}")
                
                # Metadata
                data = result['data']
                metadata = data.get('metadata', {})
                
                # Extraction info
                extraction = metadata.get('extraction', {})
                print(f"\n📊 EXTRACCIÓN:")
                print(f"   Método: {extraction.get('extraction_method')}")
                print(f"   Tiempo: {extraction.get('extraction_time', 0):.2f}s")
                print(f"   Schema: {extraction.get('schema_type')}")
                
                # Validation info
                validation = metadata.get('validation', {})
                print(f"\n🎯 VALIDACIÓN:")
                print(f"   Score: {validation.get('validation_score', 0):.2%}")
                print(f"   Nivel: {validation.get('confidence_level', 'unknown').upper()}")
                print(f"   Errores: {validation.get('errors_count', 0)}")
                print(f"   Warnings: {validation.get('warnings_count', 0)}")
                print(f"   Requiere revisión: {'SÍ' if validation.get('requires_review') else 'NO'}")
                
                # Gemini retry info
                gemini_retry = metadata.get('gemini_retry')
                if gemini_retry and gemini_retry.get('used'):
                    print(f"\n🔄 RETRY CON GEMINI:")
                    print(f"   Usado: SÍ")
                    print(f"   Score inicial: {gemini_retry.get('first_score', 0):.2%}")
                    print(f"   Score final: {gemini_retry.get('second_score', 0):.2%}")
                    print(f"   Mejora: +{gemini_retry.get('improvement', 0):.1f}pp")
                
                # Data sections
                print(f"\n📦 SECCIONES EXTRAÍDAS:")
                if 'items' in data:
                    print(f"   ✅ Items: {len(data['items'])} productos")
                if 'partes' in data:
                    print(f"   ✅ Partes: Empresa y Cliente")
                if 'documento' in data:
                    print(f"   ✅ Documento: {data['documento'].get('tipo_comprobante', 'N/A')}")
                if 'fiscalidad' in data:
                    totales = data['fiscalidad'].get('totales', {})
                    print(f"   ✅ Fiscalidad: Total ${totales.get('importe_total', 0):,.2f}")
                
                return True, result
            else:
                print(f"\n❌ ERROR EN REQUEST")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return False, None
                
        except requests.exceptions.Timeout:
            print("\n❌ TIMEOUT: La request tardó más de 60 segundos")
            return False, None
        except Exception as e:
            print(f"\n❌ EXCEPTION: {str(e)}")
            return False, None


def compare_with_llamaextract(file_path):
    """
    Comparar resultado de Gemini vs LlamaExtract
    """
    print("\n" + "=" * 80)
    print(f"🔬 COMPARACIÓN: {Path(file_path).name}")
    print("=" * 80)
    
    # Test con LlamaExtract
    print("\n1️⃣ Extrayendo con LlamaExtract...")
    url_llama = f"{BASE_URL}/invoices/process/"
    
    with open(file_path, 'rb') as f:
        try:
            response_llama = requests.post(url_llama, files={'document': f}, timeout=180)
            if response_llama.status_code == 201:
                result_llama = response_llama.json()
                score_llama = result_llama['data']['metadata']['validation']['validation_score']
                method_llama = result_llama['data']['metadata']['extraction']['extraction_method']
                time_llama = result_llama['data']['metadata']['extraction']['extraction_time']
                print(f"   ✅ Score: {score_llama:.2%}")
                print(f"   ✅ Método: {method_llama}")
                print(f"   ✅ Tiempo: {time_llama:.2f}s")
            else:
                print(f"   ❌ Error: {response_llama.status_code}")
                result_llama = None
                score_llama = 0
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            result_llama = None
            score_llama = 0
    
    # Test con Gemini
    print("\n2️⃣ Extrayendo con Gemini...")
    url_gemini = f"{BASE_URL}/invoices-gemini/upload-gemini/"
    
    with open(file_path, 'rb') as f:
        try:
            response_gemini = requests.post(url_gemini, files={'document': f}, timeout=180)
            if response_gemini.status_code == 201:
                result_gemini = response_gemini.json()
                score_gemini = result_gemini['data']['metadata']['validation']['validation_score']
                method_gemini = result_gemini['data']['metadata']['extraction']['extraction_method']
                time_gemini = result_gemini['data']['metadata']['extraction']['extraction_time']
                print(f"   ✅ Score: {score_gemini:.2%}")
                print(f"   ✅ Método: {method_gemini}")
                print(f"   ✅ Tiempo: {time_gemini:.2f}s")
            else:
                print(f"   ❌ Error: {response_gemini.status_code}")
                result_gemini = None
                score_gemini = 0
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            result_gemini = None
            score_gemini = 0
    
    # Comparación de scores
    print("\n📊 COMPARACIÓN DE SCORES:")
    print(f"   LlamaExtract:  Score={score_llama:.2%}")
    print(f"   Gemini:        Score={score_gemini:.2%}")
    
    if score_gemini > score_llama:
        diff = (score_gemini - score_llama) * 100
        print(f"   🏆 GANADOR: Gemini (+{diff:.1f}pp)")
    elif score_llama > score_gemini:
        diff = (score_llama - score_gemini) * 100
        print(f"   🏆 GANADOR: LlamaExtract (+{diff:.1f}pp)")
    else:
        print(f"   🤝 EMPATE")
    
    # Generar reporte detallado de diferencias
    if result_llama and result_gemini:
        print("\n📝 Generando reporte detallado de diferencias...")
        try:
            report_path = generate_comparison_report(
                Path(file_path).name,
                result_llama,  # Respuesta completa (incluye id, status, message, data)
                result_gemini  # Respuesta completa
            )
            print(f"✅ Reporte MD guardado en: {report_path}")
        except Exception as e:
            print(f"❌ Error generando reporte: {e}")
    
    return result_llama, result_gemini


def test_modular_extraction(file_path):
    """
    Test de extracción modular
    """
    print("\n" + "=" * 80)
    print(f"🧩 TEST MODULAR: {Path(file_path).name}")
    print("=" * 80)
    
    # Test: solo items y fiscalidad
    segments = ["items", "fiscalidad"]
    success, result = test_gemini_extraction(file_path, schema_type="modular", segments=segments)
    
    if success:
        data = result['data']
        print(f"\n✅ Extracción modular exitosa")
        print(f"   Items presente: {'items' in data and len(data['items']) > 0}")
        print(f"   Fiscalidad presente: {'fiscalidad' in data}")
        print(f"   Partes presente: {'partes' in data and data['partes']}")
        print(f"   Documento presente: {'documento' in data and data['documento']}")
    
    return success


def main():
    """
    Main test runner
    """
    print("\n" + "=" * 80)
    print("🧪 TEST SUITE: ENDPOINT GEMINI")
    print("=" * 80)
    print("\nAsegúrate de que el servidor Django esté corriendo:")
    print("  python manage.py runserver")
    print("\n" + "=" * 80)
    
    # Verificar que los archivos de ejemplo existen
    ejemplos_disponibles = [f for f in EJEMPLOS if Path(f).exists()]
    
    if not ejemplos_disponibles:
        print("\n❌ ERROR: No se encontraron archivos de ejemplo")
        print("   Busca: Ejemplo1.jpeg, Ejemplo2.jpeg, Ejemplo3.jpeg")
        return
    
    print(f"\n📂 Archivos de ejemplo encontrados: {len(ejemplos_disponibles)}")
    for ejemplo in ejemplos_disponibles:
        print(f"   - {ejemplo}")
    
    # Test 1: Extracción completa
    print("\n" + "=" * 80)
    print("TEST 1: EXTRACCIÓN COMPLETA")
    print("=" * 80)
    
    for ejemplo in ejemplos_disponibles[:1]:  # Solo primer ejemplo para ser rápido
        success, result = test_gemini_extraction(ejemplo)
        if not success:
            print(f"\n⚠️ Test falló para {ejemplo}")
    
    # Test 2: Comparación con LlamaExtract PARA TODOS LOS EJEMPLOS
    print("\n" + "=" * 80)
    print("TEST 2: COMPARACIÓN CON LLAMAEXTRACT")
    print("=" * 80)
    
    for ejemplo in ejemplos_disponibles:
        compare_with_llamaextract(ejemplo)
    
    # Test 3: Extracción modular
    if len(ejemplos_disponibles) > 1:
        test_modular_extraction(ejemplos_disponibles[1])
    
    print("\n" + "=" * 80)
    print("✅ TEST SUITE COMPLETADO")
    print("=" * 80)
    print(f"\n📊 Se generaron comparaciones para {len(ejemplos_disponibles)} facturas")
    print(f"📁 Revisa: comparaciones_gemini_vs_llama/")
    print(f"📈 Ejecuta: python analizar_comparaciones.py")


if __name__ == "__main__":
    main()

