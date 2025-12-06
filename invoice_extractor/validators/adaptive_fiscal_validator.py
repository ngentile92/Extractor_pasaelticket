"""
🎯 Adaptive Fiscal Validator - Validador que se adapta al tipo de factura

Este validador es "inteligente" porque:
1. Detecta qué tan completa es la factura
2. Aplica validaciones apropiadas según el tipo
3. No exige campos que no están presentes en facturas simples
4. Es más estricto con facturas completas

Tipos de factura:
- Completa: Todos los datos (items, IVA, partes, CAE)
- Simplificada: Items + algunos datos faltantes
- Mínima: Solo total, sin detalles
- Desconocida: Estructura no identificable
"""

import logging
from typing import Dict, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)


class AdaptiveFiscalValidator:
    """
    Validador fiscal que adapta sus reglas según el tipo de factura detectado.
    
    No todas las facturas tienen la misma información:
    - Facturas completas: Se valida TODO
    - Facturas simplificadas: Se valida lo esencial
    - Facturas mínimas: Solo se verifica el total
    
    Esto evita marcar como "errores" la ausencia de campos que simplemente
    no existen en ese tipo de factura.
    """
    
    def __init__(self, tolerance: float = 0.10):
        """
        Args:
            tolerance: Tolerancia para comparaciones numéricas (en pesos)
        """
        self.tolerance = tolerance
    
    def validate(self, data: Dict[str, Any], invoice_completeness: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida la factura adaptándose a su tipo.
        
        Args:
            data: Datos extraídos de la factura
            invoice_completeness: Resultado de detect_invoice_completeness()
        
        Returns:
            {
                'errors': List[str],
                'warnings': List[str],
                'alerts': List[str],
                'validation_type': str,
                'checks_performed': List[str]
            }
        """
        invoice_type = invoice_completeness.get('type', 'desconocida')
        
        logger.info(f"🎯 [AdaptiveValidator] Tipo de factura: {invoice_type}")
        
        if invoice_type == 'completa':
            return self._validate_complete_invoice(data, invoice_completeness)
        elif invoice_type == 'simplificada':
            return self._validate_simplified_invoice(data, invoice_completeness)
        elif invoice_type == 'minima':
            return self._validate_minimal_invoice(data, invoice_completeness)
        else:
            return self._validate_unknown_structure(data, invoice_completeness)
    
    def _validate_complete_invoice(self, data: Dict[str, Any], completeness: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validaciones estrictas para facturas completas.
        
        Se esperan:
        - Items con detalle
        - IVA discriminado
        - Partes completas
        - CAE
        - Coherencia matemática total
        """
        errors = []
        warnings = []
        alerts = []
        checks = []
        
        logger.info("   📋 Aplicando validaciones COMPLETAS")
        
        # === VALIDACIÓN DE ITEMS ===
        checks.append("items_sum")
        items = data.get('items', [])
        if items:
            items_sum = sum(float(item.get('subtotal', 0)) for item in items)
            subtotal = float(data.get('fiscalidad', {}).get('totales', {}).get('subtotal_gravado', 0))
            
            diff = abs(items_sum - subtotal)
            if diff > self.tolerance:
                errors.append(
                    f"Suma de items (${items_sum:.2f}) difiere del subtotal "
                    f"gravado (${subtotal:.2f}) en ${diff:.2f}"
                )
            else:
                alerts.append(f"✅ Suma de items coincide con subtotal gravado")
        
        # === VALIDACIÓN DE IVA ===
        checks.append("iva_calculation")
        fiscalidad = data.get('fiscalidad', {})
        impuestos = fiscalidad.get('impuestos', {})
        iva_dict = impuestos.get('iva', {})
        
        if iva_dict:
            subtotal = float(fiscalidad.get('totales', {}).get('subtotal_gravado', 0))
            
            for alicuota_str, monto_iva in iva_dict.items():
                try:
                    alicuota = float(alicuota_str.replace('105', '10.5').replace('25', '2.5'))
                    expected_iva = subtotal * (alicuota / 100)
                    monto_iva = float(monto_iva)
                    
                    diff = abs(expected_iva - monto_iva)
                    if diff > 0.50:  # Tolerancia mayor para IVA
                        warnings.append(
                            f"IVA {alicuota}%: declarado ${monto_iva:.2f}, "
                            f"calculado ${expected_iva:.2f} (diff: ${diff:.2f})"
                        )
                except (ValueError, ZeroDivisionError) as e:
                    warnings.append(f"No se pudo validar IVA alícuota {alicuota_str}: {e}")
        else:
            warnings.append("Sin IVA discriminado (puede ser correcto si es Monotributo)")
        
        # === VALIDACIÓN DE TOTAL ===
        checks.append("total_calculation")
        totales = fiscalidad.get('totales', {})
        subtotal = float(totales.get('subtotal_gravado', 0))
        iva_total = sum(float(v) for v in iva_dict.values())
        percepciones_total = (
            float(impuestos.get('percepcion_iva', 0)) +
            float(impuestos.get('percepcion_ganancias', 0)) +
            sum(float(p.get('monto', 0)) for p in impuestos.get('percepcion_iibb', []))
        )
        retenciones_total = (
            float(impuestos.get('retencion_iva', 0) or 0) +
            float(impuestos.get('retencion_ganancias', 0) or 0) +
            float(impuestos.get('retencion_suss', 0) or 0) +
            sum(float(r.get('monto', 0)) for r in impuestos.get('retenciones_iibb', []))
        )
        descuentos = float(totales.get('descuentos', 0))
        
        calculated_total = subtotal + iva_total + percepciones_total - retenciones_total - descuentos
        declared_total = float(totales.get('importe_total', 0))
        
        diff_total = abs(calculated_total - declared_total)
        if diff_total > self.tolerance:
            errors.append(
                f"Total calculado (${calculated_total:.2f}) difiere del declarado "
                f"(${declared_total:.2f}) en ${diff_total:.2f}"
            )
            # Desglose para debugging
            alerts.append(f"  Subtotal: ${subtotal:.2f}")
            alerts.append(f"  + IVA: ${iva_total:.2f}")
            alerts.append(f"  + Percepciones: ${percepciones_total:.2f}")
            alerts.append(f"  - Retenciones: ${retenciones_total:.2f}")
            alerts.append(f"  - Descuentos: ${descuentos:.2f}")
            alerts.append(f"  = ${calculated_total:.2f}")
        else:
            alerts.append(f"✅ Total calculado coincide con declarado")
        
        # === VALIDACIÓN DE CUITS ===
        checks.append("cuits")
        partes = data.get('partes', {})
        empresa_cuit = partes.get('empresa', {}).get('cuit')
        cliente_cuit = partes.get('cliente', {}).get('cuit')
        
        if not empresa_cuit:
            errors.append("CUIT de empresa faltante")
        if not cliente_cuit:
            warnings.append("CUIT de cliente faltante (puede ser Consumidor Final)")
        
        # === VALIDACIÓN DE CAE ===
        checks.append("cae")
        documento = data.get('documento', {})
        cae = documento.get('cae')
        if not cae:
            warnings.append("CAE faltante (puede ser factura sin AFIP)")
        elif len(str(cae)) != 14:
            warnings.append(f"CAE con longitud incorrecta: {len(str(cae))} dígitos (esperado: 14)")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'alerts': alerts,
            'validation_type': 'completa',
            'checks_performed': checks
        }
    
    def _validate_simplified_invoice(self, data: Dict[str, Any], completeness: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validaciones relajadas para facturas simplificadas.
        
        Se valida:
        - Items (si existen)
        - Total coherente
        - Lo que esté disponible, sin exigir todo
        """
        errors = []
        warnings = []
        alerts = []
        checks = []
        
        logger.info("   📋 Aplicando validaciones SIMPLIFICADAS")
        
        # === VALIDACIÓN DE ITEMS (si existen) ===
        items = data.get('items', [])
        if items:
            checks.append("items_sum")
            items_sum = sum(float(item.get('subtotal', 0)) for item in items)
            
            fiscalidad = data.get('fiscalidad', {})
            subtotal = float(fiscalidad.get('totales', {}).get('subtotal_gravado', 0))
            
            if subtotal > 0:
                diff = abs(items_sum - subtotal)
                if diff > self.tolerance * 5:  # Tolerancia 5x mayor
                    warnings.append(
                        f"Suma de items (${items_sum:.2f}) difiere significativamente "
                        f"del subtotal (${subtotal:.2f})"
                    )
        
        # === VALIDACIÓN DE TOTAL (mínimo requerido) ===
        checks.append("has_total")
        fiscalidad = data.get('fiscalidad', {})
        importe_total = fiscalidad.get('totales', {}).get('importe_total')
        
        if not importe_total or float(importe_total) <= 0:
            errors.append("Factura sin importe total")
        else:
            alerts.append(f"✅ Importe total presente: ${float(importe_total):.2f}")
        
        # === ALERTAS INFORMATIVAS ===
        if not completeness.get('has_iva_discrimination'):
            alerts.append("ℹ️ Sin IVA discriminado (factura simplificada)")
        
        if not completeness.get('has_parties_complete'):
            alerts.append("ℹ️ Datos de partes incompletos")
        
        if not completeness.get('has_cae'):
            alerts.append("ℹ️ Sin CAE")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'alerts': alerts,
            'validation_type': 'simplificada',
            'checks_performed': checks
        }
    
    def _validate_minimal_invoice(self, data: Dict[str, Any], completeness: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validaciones mínimas para facturas con poca información.
        
        Solo se valida:
        - Que exista un importe total
        - Que los datos presentes sean coherentes
        """
        errors = []
        warnings = []
        alerts = []
        checks = ['has_total']
        
        logger.info("   📋 Aplicando validaciones MÍNIMAS")
        
        fiscalidad = data.get('fiscalidad', {})
        importe_total = fiscalidad.get('totales', {}).get('importe_total')
        
        if not importe_total or float(importe_total) <= 0:
            errors.append("Factura sin importe total válido")
        else:
            alerts.append(f"✅ Importe total: ${float(importe_total):.2f}")
        
        alerts.append("ℹ️ Factura con información mínima - validaciones limitadas")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'alerts': alerts,
            'validation_type': 'minima',
            'checks_performed': checks
        }
    
    def _validate_unknown_structure(self, data: Dict[str, Any], completeness: Dict[str, Any]) -> Dict[str, Any]:
        """
        Para facturas con estructura desconocida.
        
        Se marca como advertencia para revisión manual.
        """
        warnings = [
            "⚠️ Estructura de factura no identificada",
            "Se recomienda revisión manual"
        ]
        
        logger.warning("   ⚠️ Estructura desconocida - validaciones limitadas")
        
        return {
            'errors': [],
            'warnings': warnings,
            'alerts': ["ℹ️ Requiere revisión manual"],
            'validation_type': 'desconocida',
            'checks_performed': ['structure_detection']
        }


