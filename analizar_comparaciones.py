#!/usr/bin/env python3
"""
Script para analizar las comparaciones generadas entre LlamaExtract y Gemini.

Este script lee los JSONs guardados y genera estadísticas útiles.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict


COMPARISONS_DIR = Path("comparaciones_gemini_vs_llama")


def load_json_pair(base_name: str, timestamp: str) -> tuple:
    """Carga el par de JSONs de LlamaExtract y Gemini."""
    llama_file = COMPARISONS_DIR / f"llama_{base_name}_{timestamp}.json"
    gemini_file = COMPARISONS_DIR / f"gemini_{base_name}_{timestamp}.json"
    
    with open(llama_file, 'r', encoding='utf-8') as f:
        llama_data = json.load(f)
    
    with open(gemini_file, 'r', encoding='utf-8') as f:
        gemini_data = json.load(f)
    
    return llama_data, gemini_data


def get_all_comparisons() -> List[Dict[str, Any]]:
    """
    Obtiene todas las comparaciones disponibles.
    
    Returns:
        Lista de dicts con 'base_name', 'timestamp', 'llama_data', 'gemini_data'
    """
    if not COMPARISONS_DIR.exists():
        print(f"❌ No existe el directorio {COMPARISONS_DIR}")
        return []
    
    # Buscar todos los archivos llama_*.json
    llama_files = list(COMPARISONS_DIR.glob("llama_*.json"))
    
    comparisons = []
    for llama_file in llama_files:
        # Extraer base_name y timestamp del nombre del archivo
        # Formato: llama_Ejemplo1_20251109_140505.json
        parts = llama_file.stem.split('_', 2)  # ['llama', 'Ejemplo1', '20251109_140505']
        
        if len(parts) < 3:
            continue
        
        base_name = parts[1]
        timestamp = parts[2]
        
        try:
            llama_data, gemini_data = load_json_pair(base_name, timestamp)
            
            comparisons.append({
                'base_name': base_name,
                'timestamp': timestamp,
                'llama_data': llama_data,
                'gemini_data': gemini_data
            })
        except Exception as e:
            print(f"⚠️ Error cargando {base_name}_{timestamp}: {e}")
    
    return comparisons


def analyze_scores(comparisons: List[Dict]) -> None:
    """Analiza y muestra estadísticas de scores."""
    print("\n" + "="*80)
    print("📊 ANÁLISIS DE SCORES")
    print("="*80)
    
    if not comparisons:
        print("No hay comparaciones para analizar.")
        return
    
    llama_scores = []
    gemini_scores = []
    
    for comp in comparisons:
        llama_score = comp['llama_data'].get('data', {}).get('metadata', {}).get('validation', {}).get('validation_score', 0)
        gemini_score = comp['gemini_data'].get('data', {}).get('metadata', {}).get('validation', {}).get('validation_score', 0)
        
        llama_scores.append(llama_score)
        gemini_scores.append(gemini_score)
    
    print(f"\n📈 Estadísticas de {len(comparisons)} facturas:\n")
    
    # LlamaExtract
    llama_avg = sum(llama_scores) / len(llama_scores)
    llama_min = min(llama_scores)
    llama_max = max(llama_scores)
    
    print(f"LlamaExtract:")
    print(f"  - Promedio: {llama_avg:.1%}")
    print(f"  - Mínimo:   {llama_min:.1%}")
    print(f"  - Máximo:   {llama_max:.1%}")
    
    # Gemini
    gemini_avg = sum(gemini_scores) / len(gemini_scores)
    gemini_min = min(gemini_scores)
    gemini_max = max(gemini_scores)
    
    print(f"\nGemini:")
    print(f"  - Promedio: {gemini_avg:.1%}")
    print(f"  - Mínimo:   {gemini_min:.1%}")
    print(f"  - Máximo:   {gemini_max:.1%}")
    
    # Comparación
    print(f"\n🏆 Resultados:")
    llama_wins = sum(1 for l, g in zip(llama_scores, gemini_scores) if l > g)
    gemini_wins = sum(1 for l, g in zip(llama_scores, gemini_scores) if g > l)
    ties = len(comparisons) - llama_wins - gemini_wins
    
    print(f"  - LlamaExtract ganó: {llama_wins} veces")
    print(f"  - Gemini ganó:       {gemini_wins} veces")
    print(f"  - Empates:           {ties} veces")


def analyze_extraction_times(comparisons: List[Dict]) -> None:
    """Analiza tiempos de extracción."""
    print("\n" + "="*80)
    print("⏱️ ANÁLISIS DE TIEMPOS")
    print("="*80)
    
    if not comparisons:
        return
    
    llama_times = []
    gemini_times = []
    
    for comp in comparisons:
        llama_time = comp['llama_data'].get('data', {}).get('metadata', {}).get('extraction', {}).get('extraction_time', 0)
        gemini_time = comp['gemini_data'].get('data', {}).get('metadata', {}).get('extraction', {}).get('extraction_time', 0)
        
        llama_times.append(llama_time)
        gemini_times.append(gemini_time)
    
    llama_avg_time = sum(llama_times) / len(llama_times)
    gemini_avg_time = sum(gemini_times) / len(gemini_times)
    
    print(f"\n⏱️ Tiempos promedio de extracción:\n")
    print(f"LlamaExtract: {llama_avg_time:.2f}s")
    print(f"Gemini:       {gemini_avg_time:.2f}s")
    print(f"\n📊 Gemini es {gemini_avg_time / llama_avg_time:.1f}x más lento")


def analyze_retry_usage(comparisons: List[Dict]) -> None:
    """Analiza uso de retry."""
    print("\n" + "="*80)
    print("🔄 ANÁLISIS DE RETRY")
    print("="*80)
    
    if not comparisons:
        return
    
    llama_retries = 0
    gemini_retries = 0
    
    for comp in comparisons:
        llama_retry = comp['llama_data'].get('data', {}).get('metadata', {}).get('gemini_retry', {}).get('used', False)
        gemini_retry = comp['gemini_data'].get('data', {}).get('metadata', {}).get('gemini_retry', {}).get('used', False)
        
        if llama_retry:
            llama_retries += 1
        if gemini_retry:
            gemini_retries += 1
    
    print(f"\n🔄 Uso de retry en {len(comparisons)} facturas:\n")
    print(f"LlamaExtract: {llama_retries} veces ({llama_retries/len(comparisons):.1%})")
    print(f"Gemini:       {gemini_retries} veces ({gemini_retries/len(comparisons):.1%})")
    
    print(f"\n💡 Retry se activa cuando validation_score <= 0.8")


def analyze_common_differences(comparisons: List[Dict]) -> None:
    """Analiza diferencias comunes entre extractores."""
    print("\n" + "="*80)
    print("🔍 CAMPOS CON MÁS DIFERENCIAS")
    print("="*80)
    
    if not comparisons:
        return
    
    # Contador de diferencias por campo
    field_diffs = defaultdict(int)
    
    for comp in comparisons:
        llama_data = comp['llama_data'].get('data', {})
        gemini_data = comp['gemini_data'].get('data', {})
        
        # Comparar documento
        for field in ['tipo_comprobante', 'numero_comprobante', 'fecha_emision', 'cae']:
            llama_val = llama_data.get('documento', {}).get(field)
            gemini_val = gemini_data.get('documento', {}).get(field)
            
            if llama_val != gemini_val:
                field_diffs[f'documento.{field}'] += 1
        
        # Comparar empresa
        for field in ['razon_social', 'cuit', 'condicion_iva']:
            llama_val = llama_data.get('partes', {}).get('empresa', {}).get(field)
            gemini_val = gemini_data.get('partes', {}).get('empresa', {}).get(field)
            
            if llama_val != gemini_val:
                field_diffs[f'empresa.{field}'] += 1
        
        # Comparar totales
        for field in ['subtotal_gravado', 'importe_total']:
            llama_val = llama_data.get('fiscalidad', {}).get('totales', {}).get(field)
            gemini_val = gemini_data.get('fiscalidad', {}).get('totales', {}).get(field)
            
            if llama_val != gemini_val:
                field_diffs[f'totales.{field}'] += 1
    
    if not field_diffs:
        print("\n✅ ¡No se encontraron diferencias comunes!")
        return
    
    # Ordenar por frecuencia
    sorted_diffs = sorted(field_diffs.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n📊 Top 10 campos con más diferencias:\n")
    for field, count in sorted_diffs[:10]:
        pct = (count / len(comparisons)) * 100
        print(f"  {field:30s} → {count:2d} veces ({pct:.0f}%)")


def main():
    """Función principal."""
    print("\n" + "="*80)
    print("🔬 ANÁLISIS DE COMPARACIONES: LlamaExtract vs Gemini")
    print("="*80)
    
    # Cargar todas las comparaciones
    print("\n📂 Cargando comparaciones...")
    comparisons = get_all_comparisons()
    
    if not comparisons:
        print("\n❌ No se encontraron comparaciones.")
        print(f"💡 Ejecuta 'python test_gemini_endpoint.py' primero para generar comparaciones.")
        return
    
    print(f"✅ Encontradas {len(comparisons)} comparaciones\n")
    
    # Listar archivos
    print("Facturas analizadas:")
    for comp in comparisons:
        print(f"  - {comp['base_name']} ({comp['timestamp']})")
    
    # Ejecutar análisis
    analyze_scores(comparisons)
    analyze_extraction_times(comparisons)
    analyze_retry_usage(comparisons)
    analyze_common_differences(comparisons)
    
    print("\n" + "="*80)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*80)
    print(f"\n📁 Revisa los reportes detallados en: {COMPARISONS_DIR}/")
    print(f"📖 Lee README_COMPARACIONES.md para más información\n")


if __name__ == "__main__":
    main()

