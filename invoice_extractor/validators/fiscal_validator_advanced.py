"""
Validador Fiscal Avanzado para Facturas Argentinas

Este módulo extiende FiscalValidator con validaciones específicas:
- Discriminación exacta de IVA por alícuota
- Validación de fórmula de total completa
- Validación de percepciones y retenciones
- Generación de alertas estructuradas para frontend
"""

from typing import Dict, Any, List, Optional
import logging
from .fiscal_validator import FiscalValidator

logger = logging.getLogger(__name__)


class FiscalValidatorAdvanced(FiscalValidator):
    """
    Validador fiscal avanzado con reglas matemáticas estrictas.
    
    Extiende FiscalValidator con:
    - Validación de discriminación de IVA por alícuota
    - Validación de fórmula completa de total
    - Validación de percepciones y retenciones
    - Generación de alertas estructuradas
    """
    
    # Tolerancia para comparaciones numéricas
    TOLERANCE = 0.50  # $0.50 para diferencias de redondeo
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """Convierte un valor a float de forma segura."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def validate_iva_discrimination(self, fiscalidad: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida discriminación de IVA por alícuota.
        
        Verifica que:
        - IVA 21% esté correctamente calculado
        - IVA 10.5% esté correctamente calculado
        - IVA 27% esté correctamente calculado
        - Suma de IVAs = total_iva
        
        Args:
            fiscalidad: Diccionario con datos fiscales
            
        Returns:
            {
                'is_valid': bool,
                'iva_breakdown': Dict,
                'total_iva_calculated': float,
                'total_iva_declared': float,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        
        impuestos = fiscalidad.get('impuestos', {})
        totales = fiscalidad.get('totales', {})
        
        # Extraer valores de IVA
        iva_21 = self.safe_float(impuestos.get('iva_21', 0))
        iva_105 = self.safe_float(impuestos.get('iva_105', 0))
        iva_27 = self.safe_float(impuestos.get('iva_27', 0))
        iva_5 = self.safe_float(impuestos.get('iva_5', 0))
        iva_25 = self.safe_float(impuestos.get('iva_25', 0))
        
        # También check formato antiguo
        iva_dict = impuestos.get('iva', {})
        if isinstance(iva_dict, dict):
            iva_21 += self.safe_float(iva_dict.get('21', 0))
            iva_105 += self.safe_float(iva_dict.get('10.5', 0))
            iva_27 += self.safe_float(iva_dict.get('27', 0))
        
        # Calcular total IVA
        total_iva_calculated = iva_21 + iva_105 + iva_27 + iva_5 + iva_25
        
        # Extraer subtotal gravado para verificar proporciones
        subtotal_gravado = self.safe_float(totales.get('subtotal_gravado', 0))
        
        iva_breakdown = {
            'iva_21': {
                'declared': round(iva_21, 2),
                'base': None,  # No tenemos el subtotal por alícuota
                'is_valid': iva_21 >= 0
            },
            'iva_105': {
                'declared': round(iva_105, 2),
                'base': None,
                'is_valid': iva_105 >= 0
            },
            'iva_27': {
                'declared': round(iva_27, 2),
                'base': None,
                'is_valid': iva_27 >= 0
            },
            'iva_5': {
                'declared': round(iva_5, 2),
                'base': None,
                'is_valid': iva_5 >= 0
            },
            'iva_25': {
                'declared': round(iva_25, 2),
                'base': None,
                'is_valid': iva_25 >= 0
            }
        }
        
        # Validar que al menos haya un IVA declarado si hay subtotal
        if subtotal_gravado > 0 and total_iva_calculated == 0:
            errors.append(
                f"Subtotal gravado (${subtotal_gravado:.2f}) presente pero no hay IVA discriminado"
            )
        
        # Validar proporciones razonables
        if subtotal_gravado > 0 and total_iva_calculated > 0:
            # IVA no debería ser más del 30% del subtotal (máximo 27% + algo)
            max_iva_esperado = subtotal_gravado * 0.30
            if total_iva_calculated > max_iva_esperado:
                warnings.append(
                    f"IVA total (${total_iva_calculated:.2f}) parece alto respecto al subtotal "
                    f"(${subtotal_gravado:.2f})"
                )
        
        # Validar que no haya valores negativos
        for alicuota, data in iva_breakdown.items():
            if data['declared'] < 0:
                errors.append(f"{alicuota} no puede ser negativo: ${data['declared']:.2f}")
        
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'iva_breakdown': iva_breakdown,
            'total_iva_calculated': round(total_iva_calculated, 2),
            'total_iva_declared': round(total_iva_calculated, 2),  # Usamos el calculado
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_total_calculation(self, fiscalidad: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida el cálculo completo del total de la factura.
        
        Formula:
        TOTAL = subtotal_gravado 
                - descuentos
                + IVA (21% + 10.5% + 27% + ...)
                + percepciones (IVA + IIBB + ganancias + ...)
                - retenciones (IVA + IIBB + ganancias + SUSS)
                + impuestos_internos
                + ICL/IDC
        
        Args:
            fiscalidad: Diccionario con datos fiscales
            
        Returns:
            {
                'is_valid': bool,
                'formula_breakdown': Dict,
                'calculated_total': float,
                'declared_total': float,
                'difference': float,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        
        totales = fiscalidad.get('totales', {})
        impuestos = fiscalidad.get('impuestos', {})
        
        # Componentes del total
        subtotal_gravado = self.safe_float(totales.get('subtotal_gravado', 0))
        descuentos = self.safe_float(totales.get('descuentos', 0))
        importe_total_declarado = self.safe_float(totales.get('importe_total', 0))
        
        # IVA
        total_iva = 0.0
        total_iva += self.safe_float(impuestos.get('iva_21', 0))
        total_iva += self.safe_float(impuestos.get('iva_105', 0))
        total_iva += self.safe_float(impuestos.get('iva_27', 0))
        total_iva += self.safe_float(impuestos.get('iva_5', 0))
        total_iva += self.safe_float(impuestos.get('iva_25', 0))
        
        # Formato antiguo de IVA
        iva_dict = impuestos.get('iva', {})
        if isinstance(iva_dict, dict):
            for key, value in iva_dict.items():
                total_iva += self.safe_float(value, 0)
        
        # Percepciones
        total_percepciones = 0.0
        total_percepciones += self.safe_float(impuestos.get('percepcion_iva', 0))
        total_percepciones += self.safe_float(impuestos.get('percepcion_ganancias', 0))
        
        # Percepciones IIBB
        percepcion_iibb = impuestos.get('percepcion_iibb', [])
        if isinstance(percepcion_iibb, list):
            for item in percepcion_iibb:
                if isinstance(item, dict):
                    total_percepciones += self.safe_float(item.get('monto', 0))
        elif isinstance(percepcion_iibb, dict):
            total_percepciones += self.safe_float(percepcion_iibb.get('monto', 0))
        
        # Retenciones
        total_retenciones = 0.0
        total_retenciones += self.safe_float(impuestos.get('retencion_iva', 0))
        total_retenciones += self.safe_float(impuestos.get('retencion_ganancias', 0))
        total_retenciones += self.safe_float(impuestos.get('retencion_suss', 0))
        
        # Retenciones IIBB
        retencion_iibb = impuestos.get('retenciones_iibb', [])
        if isinstance(retencion_iibb, list):
            for item in retencion_iibb:
                if isinstance(item, dict):
                    total_retenciones += self.safe_float(item.get('monto', 0))
        
        # Otros impuestos
        impuestos_internos = self.safe_float(impuestos.get('impuestos_internos', 0))
        icl_idc = self.safe_float(impuestos.get('icl_idc', 0))
        otras_retenciones = self.safe_float(impuestos.get('otras_retenciones', 0))
        total_retenciones += otras_retenciones
        
        # Calcular total
        total_calculado = (
            subtotal_gravado
            - descuentos
            + total_iva
            + total_percepciones
            - total_retenciones
            + impuestos_internos
            + icl_idc
        )
        
        # Calcular diferencia
        diferencia = abs(total_calculado - importe_total_declarado)
        
        # Validar
        is_valid = diferencia <= self.TOLERANCE
        
        if not is_valid:
            if importe_total_declarado > 0:
                diferencia_porcentaje = (diferencia / importe_total_declarado) * 100
                errors.append(
                    f"Total calculado (${total_calculado:.2f}) no coincide con declarado "
                    f"(${importe_total_declarado:.2f}) - diferencia: ${diferencia:.2f} ({diferencia_porcentaje:.2f}%)"
                )
            else:
                errors.append(f"Total declarado es 0 pero total calculado es ${total_calculado:.2f}")
        elif diferencia > 0.01:
            warnings.append(
                f"Diferencia menor en total: ${diferencia:.2f} (dentro de tolerancia)"
            )
        
        formula_breakdown = {
            'subtotal_gravado': round(subtotal_gravado, 2),
            'descuentos': round(descuentos, 2),
            'total_iva': round(total_iva, 2),
            'total_percepciones': round(total_percepciones, 2),
            'total_retenciones': round(total_retenciones, 2),
            'impuestos_internos': round(impuestos_internos, 2),
            'icl_idc': round(icl_idc, 2),
            'otras_retenciones': round(otras_retenciones, 2),
            'calculated_total': round(total_calculado, 2),
            'declared_total': round(importe_total_declarado, 2),
            'difference': round(diferencia, 2)
        }
        
        return {
            'is_valid': is_valid,
            'formula_breakdown': formula_breakdown,
            'calculated_total': round(total_calculado, 2),
            'declared_total': round(importe_total_declarado, 2),
            'difference': round(diferencia, 2),
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_percepciones_retenciones(self, impuestos: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida que percepciones y retenciones tengan sentido.
        
        Args:
            impuestos: Diccionario con impuestos
            
        Returns:
            {
                'is_valid': bool,
                'percepciones': Dict,
                'retenciones': Dict,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        
        # Percepciones
        percepciones = {
            'percepcion_iva': self.safe_float(impuestos.get('percepcion_iva', 0)),
            'percepcion_ganancias': self.safe_float(impuestos.get('percepcion_ganancias', 0)),
            'percepcion_iibb': []
        }
        
        # Percepciones IIBB
        percepcion_iibb = impuestos.get('percepcion_iibb', [])
        total_iibb_percepcion = 0.0
        if isinstance(percepcion_iibb, list):
            for item in percepcion_iibb:
                if isinstance(item, dict):
                    monto = self.safe_float(item.get('monto', 0))
                    provincia = item.get('provincia', 'sin_provincia')
                    percepciones['percepcion_iibb'].append({
                        'provincia': provincia,
                        'monto': round(monto, 2)
                    })
                    total_iibb_percepcion += monto
        
        percepciones['total_iibb'] = round(total_iibb_percepcion, 2)
        percepciones['total'] = round(
            percepciones['percepcion_iva'] + 
            percepciones['percepcion_ganancias'] + 
            total_iibb_percepcion, 
            2
        )
        
        # Retenciones
        retenciones = {
            'retencion_iva': self.safe_float(impuestos.get('retencion_iva', 0)),
            'retencion_ganancias': self.safe_float(impuestos.get('retencion_ganancias', 0)),
            'retencion_suss': self.safe_float(impuestos.get('retencion_suss', 0)),
            'otras_retenciones': self.safe_float(impuestos.get('otras_retenciones', 0)),
            'retenciones_iibb': []
        }
        
        # Retenciones IIBB
        retencion_iibb = impuestos.get('retenciones_iibb', [])
        total_iibb_retencion = 0.0
        if isinstance(retencion_iibb, list):
            for item in retencion_iibb:
                if isinstance(item, dict):
                    monto = self.safe_float(item.get('monto', 0))
                    provincia = item.get('provincia', 'sin_provincia')
                    retenciones['retenciones_iibb'].append({
                        'provincia': provincia,
                        'monto': round(monto, 2)
                    })
                    total_iibb_retencion += monto
        
        retenciones['total_iibb'] = round(total_iibb_retencion, 2)
        retenciones['total'] = round(
            retenciones['retencion_iva'] + 
            retenciones['retencion_ganancias'] + 
            retenciones['retencion_suss'] + 
            retenciones['otras_retenciones'] + 
            total_iibb_retencion, 
            2
        )
        
        # Validar que no haya valores negativos
        for key, value in percepciones.items():
            if key != 'percepcion_iibb' and key != 'total_iibb' and key != 'total':
                if value < 0:
                    errors.append(f"Percepción {key} no puede ser negativa: ${value:.2f}")
        
        for key, value in retenciones.items():
            if key != 'retenciones_iibb' and key != 'total_iibb' and key != 'total':
                if value < 0:
                    errors.append(f"Retención {key} no puede ser negativa: ${value:.2f}")
        
        # Advertir si hay percepciones IIBB sin provincia
        for item in percepciones['percepcion_iibb']:
            if item['provincia'] == 'sin_provincia':
                warnings.append(f"Percepción IIBB sin provincia especificada: ${item['monto']:.2f}")
        
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'percepciones': percepciones,
            'retenciones': retenciones,
            'errors': errors,
            'warnings': warnings
        }
    
    def validate_impuestos_consistency(self, fiscalidad: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validación de consistencia global de impuestos.
        
        Detecta:
        - IVA sin subtotal gravado
        - Percepciones sin base imponible
        - Retenciones mayores al total
        - Impuestos internos sin concepto
        
        Args:
            fiscalidad: Diccionario con datos fiscales
            
        Returns:
            {
                'is_valid': bool,
                'inconsistencies': List[str],
                'warnings': List[str]
            }
        """
        inconsistencies = []
        warnings = []
        
        totales = fiscalidad.get('totales', {})
        impuestos = fiscalidad.get('impuestos', {})
        
        subtotal_gravado = self.safe_float(totales.get('subtotal_gravado', 0))
        importe_total = self.safe_float(totales.get('importe_total', 0))
        
        # 1. IVA sin subtotal gravado
        total_iva = 0.0
        total_iva += self.safe_float(impuestos.get('iva_21', 0))
        total_iva += self.safe_float(impuestos.get('iva_105', 0))
        total_iva += self.safe_float(impuestos.get('iva_27', 0))
        
        if total_iva > 0 and subtotal_gravado == 0:
            inconsistencies.append(
                f"IVA declarado (${total_iva:.2f}) pero subtotal gravado = 0"
            )
        
        # 2. Percepciones muy altas
        total_percepciones = 0.0
        total_percepciones += self.safe_float(impuestos.get('percepcion_iva', 0))
        total_percepciones += self.safe_float(impuestos.get('percepcion_ganancias', 0))
        
        if subtotal_gravado > 0 and total_percepciones > subtotal_gravado * 0.20:
            warnings.append(
                f"Percepciones muy altas (${total_percepciones:.2f}) respecto al subtotal "
                f"(${subtotal_gravado:.2f})"
            )
        
        # 3. Retenciones mayores al total
        total_retenciones = 0.0
        total_retenciones += self.safe_float(impuestos.get('retencion_iva', 0))
        total_retenciones += self.safe_float(impuestos.get('retencion_ganancias', 0))
        total_retenciones += self.safe_float(impuestos.get('retencion_suss', 0))
        
        if importe_total > 0 and total_retenciones > importe_total:
            inconsistencies.append(
                f"Retenciones (${total_retenciones:.2f}) mayores al total "
                f"(${importe_total:.2f})"
            )
        
        is_valid = len(inconsistencies) == 0
        
        return {
            'is_valid': is_valid,
            'inconsistencies': inconsistencies,
            'warnings': warnings
        }
    
    def validate_complete_advanced(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validación completa avanzada incluyendo validación base + validaciones específicas.
        
        Args:
            invoice_data: Datos completos de la factura
            
        Returns:
            Diccionario completo con todos los resultados de validación y alertas
        """
        logger.info("💰 [FiscalValidatorAdvanced] Iniciando validación fiscal avanzada")
        
        # Ejecutar validación base
        logger.debug("   📋 [FiscalValidatorAdvanced] Ejecutando validación base (FiscalValidator)")
        base_result = self.validate_invoice_complete(invoice_data)
        logger.info(f"   ✅ [FiscalValidatorAdvanced] Validación base completada - Score: {base_result['validation_score']:.2%}")
        
        # Extraer fiscalidad
        fiscalidad = invoice_data.get('fiscalidad', {})
        impuestos = fiscalidad.get('impuestos', {})
        
        # Validaciones avanzadas
        logger.debug("   🔍 [FiscalValidatorAdvanced] PASO 1: Validando discriminación de IVA")
        iva_result = self.validate_iva_discrimination(fiscalidad)
        if iva_result['is_valid']:
            logger.info(f"      ✅ IVA total: ${iva_result['total_iva_calculated']:.2f}")
        else:
            logger.error(f"      ❌ IVA con {len(iva_result['errors'])} error(es)")
        
        logger.debug("   🧮 [FiscalValidatorAdvanced] PASO 2: Validando cálculo de total")
        total_result = self.validate_total_calculation(fiscalidad)
        if total_result['is_valid']:
            logger.info(f"      ✅ Total válido: ${total_result['declared_total']:.2f}")
        else:
            logger.error(
                f"      ❌ Total incorrecto: calculado ${total_result['calculated_total']:.2f} "
                f"vs declarado ${total_result['declared_total']:.2f} (diff: ${total_result['difference']:.2f})"
            )
        
        logger.debug("   💸 [FiscalValidatorAdvanced] PASO 3: Validando percepciones y retenciones")
        percepciones_result = self.validate_percepciones_retenciones(impuestos)
        if percepciones_result['is_valid']:
            logger.info(
                f"      ✅ Percepciones: ${percepciones_result['percepciones']['total']:.2f}, "
                f"Retenciones: ${percepciones_result['retenciones']['total']:.2f}"
            )
        else:
            logger.error(f"      ❌ Percepciones/Retenciones con {len(percepciones_result['errors'])} error(es)")
        
        logger.debug("   🔗 [FiscalValidatorAdvanced] PASO 4: Validando consistencia de impuestos")
        consistency_result = self.validate_impuestos_consistency(fiscalidad)
        if consistency_result['is_valid']:
            logger.info("      ✅ Consistencia fiscal OK")
        else:
            logger.warning(f"      ⚠️ {len(consistency_result['inconsistencies'])} inconsistencia(s) detectada(s)")
        
        # Combinar errores y advertencias
        all_errors = base_result['validation_errors'].copy()
        all_errors.extend(iva_result['errors'])
        all_errors.extend(total_result['errors'])
        all_errors.extend(percepciones_result['errors'])
        all_errors.extend(consistency_result['inconsistencies'])
        
        all_warnings = base_result['validation_warnings'].copy()
        all_warnings.extend(iva_result['warnings'])
        all_warnings.extend(total_result['warnings'])
        all_warnings.extend(percepciones_result['warnings'])
        all_warnings.extend(consistency_result['warnings'])
        
        # Calcular score mejorado
        total_validations = 4  # 4 validaciones principales
        failed_validations = sum([
            0 if iva_result['is_valid'] else 1,
            0 if total_result['is_valid'] else 1,
            0 if percepciones_result['is_valid'] else 1,
            0 if consistency_result['is_valid'] else 1
        ])
        
        advanced_score = max(0.0, 1.0 - (failed_validations / total_validations))
        
        # Combinar con score base (promedio ponderado)
        combined_score = (base_result['validation_score'] * 0.6 + advanced_score * 0.4)
        
        logger.info(
            f"✅ [FiscalValidatorAdvanced] Validación completada - "
            f"Score base: {base_result['validation_score']:.2%}, "
            f"Score avanzado: {advanced_score:.2%}, "
            f"Score combinado: {combined_score:.2%}"
        )
        
        if len(all_errors) > 0:
            logger.error(f"❌ [FiscalValidatorAdvanced] {len(all_errors)} error(es) totales")
        if len(all_warnings) > 0:
            logger.warning(f"⚠️ [FiscalValidatorAdvanced] {len(all_warnings)} warning(s) totales")
        
        return {
            'validation_errors': all_errors,
            'validation_warnings': all_warnings,
            'validation_score': combined_score,
            'base_validation': base_result,
            'advanced_validation': {
                'iva_discrimination': iva_result,
                'total_calculation': total_result,
                'percepciones_retenciones': percepciones_result,
                'consistency': consistency_result
            },
            'has_validation_errors': len(all_errors) > 0
        }
    
    @staticmethod
    def create_alerts(validation_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Crea alertas estructuradas para frontend basadas en el resultado de validación.
        
        Args:
            validation_result: Resultado de validate_complete_advanced()
            
        Returns:
            Lista de alertas estructuradas
        """
        alerts = []
        alert_id = 1
        
        advanced = validation_result.get('advanced_validation', {})
        
        # Alertas de discriminación de IVA
        iva_result = advanced.get('iva_discrimination', {})
        if iva_result and not iva_result.get('is_valid', True):
            for error in iva_result.get('errors', []):
                alerts.append({
                    'id': f'fiscal_iva_{alert_id}',
                    'level': 'error',
                    'category': 'fiscal',
                    'field': 'fiscalidad.impuestos.iva',
                    'message': error,
                    'current_value': iva_result.get('total_iva_calculated'),
                    'expected_value': None,
                    'suggestion': 'Verificar discriminación de IVA en documento original',
                    'location': 'fiscalidad.impuestos',
                    'can_auto_fix': False,
                    'details': iva_result.get('iva_breakdown', {})
                })
                alert_id += 1
        
        # Alertas de cálculo de total
        total_result = advanced.get('total_calculation', {})
        if total_result and not total_result.get('is_valid', True):
            for error in total_result.get('errors', []):
                alerts.append({
                    'id': f'fiscal_total_{alert_id}',
                    'level': 'critical',
                    'category': 'total',
                    'field': 'fiscalidad.totales.importe_total',
                    'message': error,
                    'current_value': total_result.get('declared_total'),
                    'expected_value': total_result.get('calculated_total'),
                    'suggestion': 'Revisar discriminación de impuestos y cálculo de total',
                    'location': 'fiscalidad.totales.importe_total',
                    'can_auto_fix': False,
                    'details': total_result.get('formula_breakdown', {})
                })
                alert_id += 1
        
        # Alertas de percepciones/retenciones
        perc_ret_result = advanced.get('percepciones_retenciones', {})
        if perc_ret_result and not perc_ret_result.get('is_valid', True):
            for error in perc_ret_result.get('errors', []):
                alerts.append({
                    'id': f'fiscal_perc_ret_{alert_id}',
                    'level': 'error',
                    'category': 'fiscal',
                    'field': 'fiscalidad.impuestos',
                    'message': error,
                    'current_value': None,
                    'expected_value': None,
                    'suggestion': 'Verificar percepciones y retenciones',
                    'location': 'fiscalidad.impuestos',
                    'can_auto_fix': False,
                    'details': perc_ret_result
                })
                alert_id += 1
        
        # Alertas de consistencia
        consistency_result = advanced.get('consistency', {})
        if consistency_result and not consistency_result.get('is_valid', True):
            for inconsistency in consistency_result.get('inconsistencies', []):
                alerts.append({
                    'id': f'fiscal_consistency_{alert_id}',
                    'level': 'warning',
                    'category': 'fiscal',
                    'field': 'fiscalidad',
                    'message': inconsistency,
                    'current_value': None,
                    'expected_value': None,
                    'suggestion': 'Revisar consistencia de datos fiscales',
                    'location': 'fiscalidad',
                    'can_auto_fix': False,
                    'details': consistency_result
                })
                alert_id += 1
        
        # Alertas de warnings
        for warning in validation_result.get('validation_warnings', []):
            alerts.append({
                'id': f'fiscal_warning_{alert_id}',
                'level': 'info',
                'category': 'fiscal',
                'field': 'fiscalidad',
                'message': warning,
                'current_value': None,
                'expected_value': None,
                'suggestion': None,
                'location': 'fiscalidad',
                'can_auto_fix': False,
                'details': {}
            })
            alert_id += 1
        
        return alerts

