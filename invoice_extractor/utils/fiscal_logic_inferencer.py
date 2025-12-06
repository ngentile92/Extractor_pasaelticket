"""
🧮 Fiscal Logic Inferencer - Sistema de Inferencia Contable

Este módulo implementa un sistema inteligente que:
1. Infiere la lógica contable de una factura basándose en relaciones matemáticas
2. Normaliza diferentes nomenclaturas a un formato estándar
3. Corrige automáticamente errores matemáticos cuando es posible
4. Marca incertidumbres y documenta todas las decisiones tomadas

El problema que resuelve:
- Facturas diferentes usan "subtotal" para conceptos distintos
- Algunos incluyen IVA, otros no
- Algunos incluyen descuentos, otros no
- No hay estándar único en Argentina

La solución:
- Prueba hipótesis matemáticas para descubrir la lógica real
- Normaliza TODO a un formato estándar
- Documenta qué decisiones tomó y por qué
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


# =============================================================================
# TIPOS DE SUBTOTAL DETECTABLES
# =============================================================================

SUBTOTAL_TYPES = {
    'base_imponible': 'Suma de items SIN IVA, SIN descuentos',
    'neto_sin_iva': 'Suma de items MENOS descuentos, SIN IVA',
    'con_iva': 'Suma de items CON IVA incluido',
    'mixto': 'Suma de items MENOS descuentos MÁS IVA',
    'incierto': 'No se pudo determinar con certeza'
}


# =============================================================================
# FISCAL LOGIC INFERENCER
# =============================================================================

class FiscalLogicInferencer:
    """
    Sistema de inferencia de lógica contable para facturas argentinas.
    
    Capabilities:
    - Detecta qué tipo de "subtotal" usa cada factura
    - Normaliza a formato estándar independiente de nomenclatura original
    - Corrige errores matemáticos en items
    - Valida y ajusta totales según lógica inferida
    - Documenta todas las decisiones para transparencia
    """
    
    def __init__(self, tolerance: float = 0.10):
        """
        Initialize inferencer.
        
        Args:
            tolerance: Tolerancia para comparaciones numéricas (en pesos)
        """
        self.tolerance = tolerance
        self.inference_log = []  # Log de decisiones tomadas
    
    def infer_subtotal_type(self, data: Dict[str, Any]) -> Tuple[str, float]:
        """
        Infiere qué tipo de subtotal está usando esta factura.
        
        Prueba múltiples hipótesis matemáticas y elige la que mejor cuadre.
        
        Args:
            data: Datos extraídos de la factura
        
        Returns:
            Tuple (tipo_subtotal, confianza)
            - tipo_subtotal: Una de las keys de SUBTOTAL_TYPES
            - confianza: 0.0 a 1.0 (qué tan bien cuadra la hipótesis)
        
        Example:
            >>> tipo, conf = inferencer.infer_subtotal_type(data)
            >>> print(f"Tipo: {tipo}, Confianza: {conf:.0%}")
            Tipo: base_imponible, Confianza: 98%
        """
        # Extraer valores necesarios
        items = data.get('items', [])
        fiscalidad = data.get('fiscalidad', {})
        totales = fiscalidad.get('totales', {})
        impuestos = fiscalidad.get('impuestos', {})
        
        # Si no hay items o subtotal, no podemos inferir
        if not items:
            self._log_inference("Sin items para analizar")
            return 'incierto', 0.0
        
        subtotal_declarado = totales.get('subtotal_gravado', 0)
        if not subtotal_declarado:
            self._log_inference("Sin subtotal declarado")
            return 'incierto', 0.0
        
        # Calcular valores base
        items_sum = sum(float(item.get('subtotal', 0)) for item in items)
        descuentos = float(totales.get('descuentos') or 0)
        iva_total = sum(float(v) for v in impuestos.get('iva', {}).values())
        
        self._log_inference(f"Items sum: ${items_sum:.2f}")
        self._log_inference(f"Subtotal declarado: ${subtotal_declarado:.2f}")
        self._log_inference(f"IVA total: ${iva_total:.2f}")
        self._log_inference(f"Descuentos: ${descuentos:.2f}")
        
        # Probar hipótesis
        hypotheses = []
        
        # H1: Subtotal = suma items (base imponible sin descuentos)
        diff_h1 = abs(subtotal_declarado - items_sum)
        conf_h1 = self._calculate_confidence(diff_h1, items_sum)
        hypotheses.append(('base_imponible', conf_h1, diff_h1))
        self._log_inference(f"H1 (base_imponible): diff=${diff_h1:.2f}, conf={conf_h1:.2%}")
        
        # H2: Subtotal = suma items - descuentos (neto sin IVA)
        if descuentos > 0:
            diff_h2 = abs(subtotal_declarado - (items_sum - descuentos))
            conf_h2 = self._calculate_confidence(diff_h2, items_sum)
            hypotheses.append(('neto_sin_iva', conf_h2, diff_h2))
            self._log_inference(f"H2 (neto_sin_iva): diff=${diff_h2:.2f}, conf={conf_h2:.2%}")
        
        # H3: Subtotal = suma items + IVA (con IVA incluido)
        if iva_total > 0:
            diff_h3 = abs(subtotal_declarado - (items_sum + iva_total))
            conf_h3 = self._calculate_confidence(diff_h3, items_sum + iva_total)
            hypotheses.append(('con_iva', conf_h3, diff_h3))
            self._log_inference(f"H3 (con_iva): diff=${diff_h3:.2f}, conf={conf_h3:.2%}")
        
        # H4: Subtotal = suma items - descuentos + IVA (mixto)
        if descuentos > 0 and iva_total > 0:
            diff_h4 = abs(subtotal_declarado - (items_sum - descuentos + iva_total))
            conf_h4 = self._calculate_confidence(diff_h4, items_sum - descuentos + iva_total)
            hypotheses.append(('mixto', conf_h4, diff_h4))
            self._log_inference(f"H4 (mixto): diff=${diff_h4:.2f}, conf={conf_h4:.2%}")
        
        # Elegir la hipótesis con mayor confianza
        if hypotheses:
            best_hypothesis = max(hypotheses, key=lambda x: x[1])
            tipo, confianza, diff = best_hypothesis
            
            self._log_inference(f"✅ Hipótesis elegida: {tipo} (conf={confianza:.2%}, diff=${diff:.2f})")
            
            # Si la confianza es muy baja, marcar como incierto
            if confianza < 0.80:
                self._log_inference(f"⚠️ Confianza baja, marcando como incierto")
                return 'incierto', confianza
            
            return tipo, confianza
        
        return 'incierto', 0.0
    
    def _calculate_confidence(self, difference: float, expected_value: float) -> float:
        """
        Calcula la confianza basándose en la diferencia absoluta.
        
        Args:
            difference: Diferencia absoluta entre valor esperado y real
            expected_value: Valor esperado para calcular % de error
        
        Returns:
            Confianza de 0.0 a 1.0
        """
        if expected_value == 0:
            return 0.0
        
        # % de error
        error_pct = difference / abs(expected_value)
        
        # Convertir a confianza (inverso del error)
        # Error 0% = confianza 100%
        # Error 5% = confianza 95%
        # Error 20% = confianza 80%
        confidence = max(0.0, 1.0 - error_pct)
        
        return confidence
    
    def normalize_to_standard_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza la estructura extraída a un formato estándar.
        
        Formato estándar objetivo:
        - subtotal_gravado: Suma de items SIN IVA, DESPUÉS de descuentos
        - base_imponible: Suma de items SIN IVA, ANTES de descuentos
        - descuentos_aplicados: Total de descuentos
        - iva_discriminado: IVA por alícuota
        - otros_impuestos: Percepciones, retenciones, etc.
        - importe_total: Todo incluido
        
        Args:
            data: Datos extraídos
        
        Returns:
            Datos normalizados con metadata de inferencia
        """
        self._log_inference("=" * 60)
        self._log_inference("INICIANDO NORMALIZACIÓN A FORMATO ESTÁNDAR")
        self._log_inference("=" * 60)
        
        # Inferir tipo de subtotal
        tipo_subtotal, confianza = self.infer_subtotal_type(data)
        
        # Extraer valores
        fiscalidad = data.get('fiscalidad', {})
        totales = fiscalidad.get('totales', {})
        impuestos = fiscalidad.get('impuestos', {})
        
        items_sum = sum(float(item.get('subtotal', 0)) for item in data.get('items', []))
        subtotal_original = float(totales.get('subtotal_gravado', 0))
        descuentos = float(totales.get('descuentos') or 0)
        iva_total = sum(float(v) for v in impuestos.get('iva', {}).values())
        
        # Inicializar ajustes
        ajustes = []
        
        # Normalizar según el tipo inferido
        if tipo_subtotal == 'base_imponible':
            # Ya está correcto: subtotal = suma items sin descuentos
            base_imponible = subtotal_original
            subtotal_gravado = subtotal_original - descuentos if descuentos > 0 else subtotal_original
            
            if descuentos > 0:
                ajustes.append(f"Subtotal gravado calculado: ${subtotal_original:.2f} - ${descuentos:.2f} = ${subtotal_gravado:.2f}")
        
        elif tipo_subtotal == 'neto_sin_iva':
            # Subtotal ya tiene descuentos aplicados
            subtotal_gravado = subtotal_original
            base_imponible = subtotal_original + descuentos if descuentos > 0 else items_sum
            
            ajustes.append(f"Subtotal original ya incluía descuentos aplicados")
            if descuentos > 0:
                ajustes.append(f"Base imponible reconstruida: ${subtotal_gravado:.2f} + ${descuentos:.2f} = ${base_imponible:.2f}")
        
        elif tipo_subtotal == 'con_iva':
            # Subtotal incluye IVA, necesitamos separarlo
            base_imponible = items_sum
            subtotal_gravado = subtotal_original - iva_total
            
            ajustes.append(f"⚠️ Subtotal original INCLUÍA IVA (${subtotal_original:.2f})")
            ajustes.append(f"IVA separado: ${iva_total:.2f}")
            ajustes.append(f"Subtotal sin IVA: ${subtotal_gravado:.2f}")
        
        elif tipo_subtotal == 'mixto':
            # Subtotal = items - descuentos + IVA
            base_imponible = items_sum
            subtotal_gravado = subtotal_original - iva_total
            
            ajustes.append(f"⚠️ Subtotal original incluía IVA y descuentos")
            ajustes.append(f"Separado: ${subtotal_original:.2f} - ${iva_total:.2f} = ${subtotal_gravado:.2f}")
        
        else:  # incierto
            # No podemos inferir con certeza, dejamos como está pero marcamos
            base_imponible = items_sum
            subtotal_gravado = subtotal_original
            
            ajustes.append(f"⚠️ No se pudo determinar el tipo de subtotal con certeza")
            ajustes.append(f"Se mantienen valores originales (conf={confianza:.0%})")
        
        # Actualizar estructura
        if 'fiscalidad' not in data:
            data['fiscalidad'] = {}
        if 'totales' not in data['fiscalidad']:
            data['fiscalidad']['totales'] = {}
        if 'calculos' not in data['fiscalidad']:
            data['fiscalidad']['calculos'] = {}
        
        # Aplicar valores normalizados
        data['fiscalidad']['totales']['subtotal_gravado'] = round(subtotal_gravado, 2)
        data['fiscalidad']['totales']['base_imponible'] = round(base_imponible, 2)
        
        # Agregar metadata de inferencia
        data['fiscalidad']['calculos'].update({
            'tipo_subtotal_original': tipo_subtotal,
            'subtotal_original_valor': round(subtotal_original, 2),
            'confianza_inferencia': round(confianza, 4),
            'ajustes_aplicados': ajustes,
            'inference_log': self.inference_log.copy()
        })
        
        self._log_inference("=" * 60)
        self._log_inference("NORMALIZACIÓN COMPLETADA")
        self._log_inference(f"Base imponible: ${base_imponible:.2f}")
        self._log_inference(f"Subtotal gravado: ${subtotal_gravado:.2f}")
        self._log_inference("=" * 60)
        
        return data
    
    def validate_and_fix_items(self, items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Valida items y corrige errores matemáticos cuando es posible.
        
        Para cada item, verifica: cantidad × precio_unitario = subtotal
        Si no cuadra, intenta inferir cuál valor está mal y lo corrige.
        
        Args:
            items: Lista de items extraídos
        
        Returns:
            Tuple (items_corregidos, correcciones_aplicadas)
        """
        if not items:
            return [], []
        
        fixed_items = []
        corrections = []
        
        self._log_inference("=" * 60)
        self._log_inference(f"VALIDANDO {len(items)} ITEMS")
        self._log_inference("=" * 60)
        
        for i, item in enumerate(items):
            cantidad = float(item.get('cantidad', 0))
            precio = float(item.get('precio_unitario', 0))
            subtotal = float(item.get('subtotal', 0))
            
            # Calcular subtotal esperado
            expected_subtotal = cantidad * precio
            
            # Calcular diferencia
            diff = abs(expected_subtotal - subtotal)
            
            # Si cuadra (con tolerancia), no tocar
            if diff <= self.tolerance:
                fixed_items.append(item)
                self._log_inference(f"Item {i+1}: ✅ OK (diff=${diff:.2f})")
                continue
            
            # No cuadra - intentar corregir
            self._log_inference(f"Item {i+1}: ⚠️ Error matemático detectado")
            self._log_inference(f"  Cantidad: {cantidad}")
            self._log_inference(f"  Precio: ${precio:.2f}")
            self._log_inference(f"  Subtotal declarado: ${subtotal:.2f}")
            self._log_inference(f"  Subtotal esperado: ${expected_subtotal:.2f}")
            self._log_inference(f"  Diferencia: ${diff:.2f}")
            
            # Hipótesis 1: El precio está mal, cantidad y subtotal están bien
            corrected_precio = None
            if cantidad > 0:
                corrected_precio = subtotal / cantidad
                change_precio_pct = abs(corrected_precio - precio) / precio if precio > 0 else float('inf')
            else:
                change_precio_pct = float('inf')
            
            # Hipótesis 2: La cantidad está mal, precio y subtotal están bien
            corrected_cantidad = None
            if precio > 0:
                corrected_cantidad = subtotal / precio
                change_cantidad_pct = abs(corrected_cantidad - cantidad) / cantidad if cantidad > 0 else float('inf')
            else:
                change_cantidad_pct = float('inf')
            
            # Hipótesis 3: El subtotal está mal, cantidad y precio están bien
            corrected_subtotal = expected_subtotal
            change_subtotal_pct = diff / subtotal if subtotal > 0 else float('inf')
            
            # Elegir la hipótesis que requiere menor cambio relativo
            min_change = min(change_precio_pct, change_cantidad_pct, change_subtotal_pct)
            
            if min_change == change_precio_pct and corrected_precio is not None:
                item['precio_unitario'] = round(corrected_precio, 2)
                item['_corrected_field'] = 'precio_unitario'
                item['_original_precio_unitario'] = precio
                correction_msg = f"Item {i+1}: Precio corregido de ${precio:.2f} a ${corrected_precio:.2f}"
                corrections.append(correction_msg)
                self._log_inference(f"  → {correction_msg}")
            
            elif min_change == change_cantidad_pct and corrected_cantidad is not None:
                item['cantidad'] = round(corrected_cantidad, 4)
                item['_corrected_field'] = 'cantidad'
                item['_original_cantidad'] = cantidad
                correction_msg = f"Item {i+1}: Cantidad corregida de {cantidad} a {corrected_cantidad:.4f}"
                corrections.append(correction_msg)
                self._log_inference(f"  → {correction_msg}")
            
            else:
                item['subtotal'] = round(corrected_subtotal, 2)
                item['_corrected_field'] = 'subtotal'
                item['_original_subtotal'] = subtotal
                correction_msg = f"Item {i+1}: Subtotal corregido de ${subtotal:.2f} a ${corrected_subtotal:.2f}"
                corrections.append(correction_msg)
                self._log_inference(f"  → {correction_msg}")
            
            fixed_items.append(item)
        
        self._log_inference("=" * 60)
        self._log_inference(f"VALIDACIÓN COMPLETADA: {len(corrections)} correcciones aplicadas")
        self._log_inference("=" * 60)
        
        return fixed_items, corrections
    
    def detect_invoice_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detecta qué tan completa es la información de la factura.
        
        Returns:
            {
                'type': 'completa' | 'simplificada' | 'minima' | 'desconocida',
                'has_items_detail': bool,
                'has_iva_discrimination': bool,
                'has_parties_complete': bool,
                'has_cae': bool,
                'completeness_score': 0.0 a 1.0
            }
        """
        has_items = bool(data.get('items'))
        has_items_detail = has_items and len(data.get('items', [])) > 0
        
        fiscalidad = data.get('fiscalidad', {})
        has_iva = bool(fiscalidad.get('impuestos', {}).get('iva'))
        
        partes = data.get('partes', {})
        has_empresa_complete = bool(
            partes.get('empresa', {}).get('cuit') and
            partes.get('empresa', {}).get('razon_social')
        )
        has_cliente_complete = bool(
            partes.get('cliente', {}).get('cuit') or
            partes.get('cliente', {}).get('apellido_nombre_razon_social')
        )
        has_parties = has_empresa_complete and has_cliente_complete
        
        documento = data.get('documento', {})
        has_cae = bool(documento.get('cae'))
        
        has_total = bool(fiscalidad.get('totales', {}).get('importe_total'))
        
        # Calcular score de completitud
        factors = [
            has_items_detail,
            has_iva,
            has_parties,
            has_cae,
            has_total
        ]
        completeness_score = sum(factors) / len(factors)
        
        # Determinar tipo
        if has_items_detail and has_iva and has_parties and has_cae:
            invoice_type = 'completa'
        elif has_items_detail and (has_iva or has_parties):
            invoice_type = 'simplificada'
        elif has_total:
            invoice_type = 'minima'
        else:
            invoice_type = 'desconocida'
        
        return {
            'type': invoice_type,
            'has_items_detail': has_items_detail,
            'has_iva_discrimination': has_iva,
            'has_parties_complete': has_parties,
            'has_cae': has_cae,
            'has_total': has_total,
            'completeness_score': completeness_score
        }
    
    def _log_inference(self, message: str):
        """Registra un mensaje en el log de inferencias"""
        self.inference_log.append(message)
        logger.debug(f"[FiscalInferencer] {message}")
    
    def clear_log(self):
        """Limpia el log de inferencias"""
        self.inference_log = []


