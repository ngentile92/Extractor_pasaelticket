"""
Validador Maestro

Orquesta todas las validaciones en un pipeline unificado:
- CUIT (empresa y cliente)
- Items (cálculos, cantidades, suma)
- Fiscal (IVA, percepciones, totales)
- Scoring de confiabilidad
- Generación de alertas estructuradas
"""

from typing import Dict, Any, List, Optional
import logging
import time
from datetime import datetime

from .cuit_validator import CUITValidator
from .items_validator import ItemsValidator
from .fiscal_validator_advanced import FiscalValidatorAdvanced
from .confidence_scorer import ConfidenceScorer

logger = logging.getLogger(__name__)


class MasterValidator:
    """
    Validador maestro que orquesta todas las validaciones.
    
    Pipeline:
    1. Validar CUITs (empresa y cliente)
    2. Validar items (cálculos, cantidades, suma)
    3. Validar fiscalidad (IVA, percepciones, total)
    4. Calcular score de confiabilidad
    5. Generar alertas y recomendaciones
    """
    
    def __init__(self):
        self.cuit_validator = CUITValidator()
        self.items_validator = ItemsValidator()
        self.fiscal_validator = FiscalValidatorAdvanced()
        self.confidence_scorer = ConfidenceScorer()
    
    def validate_complete(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta todas las validaciones y genera reporte completo.
        
        Args:
            extracted_data: Datos extraídos de la factura
            
        Returns:
            {
                'validation_results': {
                    'cuits': {...},
                    'items': {...},
                    'fiscal': {...}
                },
                'confidence_score': float,
                'confidence_level': str,
                'confidence_details': Dict,
                'requires_review': bool,
                'critical_issues': List[str],
                'errors': List[str],
                'warnings': List[str],
                'alerts': List[Dict],  # Para frontend
                'recommendations': List[str],
                'corrections_applied': List[str],
                'processing_time': float,
                'timestamp': str
            }
        """
        start_time = time.time()
        timestamp = datetime.now().isoformat()
        
        logger.info("=" * 80)
        logger.info("🚀 [MasterValidator] INICIANDO VALIDACIÓN MAESTRA COMPLETA")
        logger.info("=" * 80)
        
        # Estructura para resultados
        validation_results = {}
        all_errors = []
        all_warnings = []
        all_corrections = []
        all_alerts = []
        
        # PASO 1: Validar CUITs
        logger.info("")
        logger.info("📋 [MasterValidator] ═══ PASO 1/5: VALIDANDO CUITs ═══")
        cuits_result = self._validate_cuits(extracted_data)
        validation_results['cuits'] = cuits_result
        all_errors.extend(cuits_result.get('errors', []))
        all_warnings.extend(cuits_result.get('warnings', []))
        all_alerts.extend(cuits_result.get('alerts', []))
        logger.info(f"   Resultado: {len(cuits_result.get('errors', []))} error(es), {len(cuits_result.get('warnings', []))} warning(s), {len(cuits_result.get('alerts', []))} alerta(s)")
        
        # PASO 2: Validar Items
        logger.info("")
        logger.info("📦 [MasterValidator] ═══ PASO 2/5: VALIDANDO ITEMS ═══")
        items_result = self._validate_items(extracted_data)
        validation_results['items'] = items_result
        all_errors.extend(items_result.get('errors', []))
        all_warnings.extend(items_result.get('warnings', []))
        all_corrections.extend(items_result.get('corrections_applied', []))
        all_alerts.extend(items_result.get('alerts', []))
        logger.info(f"   Resultado: {len(items_result.get('errors', []))} error(es), {len(items_result.get('warnings', []))} warning(s), {len(items_result.get('corrections_applied', []))} corrección(es)")
        
        # PASO 3: Validar Fiscalidad
        logger.info("")
        logger.info("💰 [MasterValidator] ═══ PASO 3/5: VALIDANDO FISCALIDAD ═══")
        fiscal_result = self._validate_fiscal(extracted_data)
        validation_results['fiscal'] = fiscal_result
        all_errors.extend(fiscal_result.get('validation_errors', []))
        all_warnings.extend(fiscal_result.get('validation_warnings', []))
        all_alerts.extend(fiscal_result.get('alerts', []))
        logger.info(f"   Resultado: {len(fiscal_result.get('validation_errors', []))} error(es), {len(fiscal_result.get('validation_warnings', []))} warning(s)")
        
        # PASO 4: Calcular Score de Confiabilidad
        logger.info("")
        logger.info("🎯 [MasterValidator] ═══ PASO 4/5: CALCULANDO SCORE DE CONFIABILIDAD ═══")
        confidence_input = self._prepare_confidence_input(validation_results)
        confidence_result = self.confidence_scorer.calculate_score(confidence_input)
        logger.info(f"   Score global: {confidence_result['overall_score']:.2%} ({confidence_result['confidence_level'].upper()})")
        logger.info(f"   Categorías evaluadas: {confidence_result['breakdown']['categories_evaluated']}/{confidence_result['breakdown']['total_categories']}")
        logger.info(f"   Categorías aprobadas: {confidence_result['breakdown']['categories_passed']}")
        logger.info(f"   Categorías fallidas: {confidence_result['breakdown']['categories_failed']}")
        
        # PASO 5: Generar Recomendaciones
        logger.info("")
        logger.info("💡 [MasterValidator] ═══ PASO 5/5: GENERANDO RECOMENDACIONES ═══")
        recommendations = self.confidence_scorer.get_recommendations(confidence_result)
        logger.info(f"   {len(recommendations)} recomendación(es) generada(s)")
        for i, rec in enumerate(recommendations, 1):
            logger.info(f"   {i}. {rec}")
        
        # Calcular tiempo de procesamiento
        processing_time = time.time() - start_time
        
        # Resumen final
        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ [MasterValidator] VALIDACIÓN COMPLETADA")
        logger.info(f"   ⏱️  Tiempo: {processing_time:.2f}s")
        logger.info(f"   📊 Score: {confidence_result['overall_score']:.2%} ({confidence_result['confidence_level'].upper()})")
        logger.info(f"   🚨 Errores: {len(all_errors)}")
        logger.info(f"   ⚠️  Warnings: {len(all_warnings)}")
        logger.info(f"   🔔 Alertas: {len(all_alerts)}")
        logger.info(f"   🔧 Correcciones: {len(all_corrections)}")
        logger.info(f"   📝 Recomendaciones: {len(recommendations)}")
        logger.info(f"   🔍 Revisión requerida: {'SÍ' if confidence_result['requires_review'] else 'NO'}")
        logger.info("=" * 80)
        
        return {
            'validation_results': validation_results,
            'confidence_score': confidence_result['overall_score'],
            'confidence_level': confidence_result['confidence_level'],
            'confidence_details': confidence_result['confidence_details'],
            'confidence_breakdown': confidence_result.get('breakdown', {}),
            'requires_review': confidence_result['requires_review'],
            'critical_issues': confidence_result['critical_issues'],
            'errors': all_errors,
            'warnings': all_warnings,
            'alerts': all_alerts,  # Para frontend
            'recommendations': recommendations,
            'corrections_applied': all_corrections,
            'processing_time': round(processing_time, 4),
            'timestamp': timestamp,
            'summary': {
                'total_errors': len(all_errors),
                'total_warnings': len(all_warnings),
                'total_alerts': len(all_alerts),
                'total_corrections': len(all_corrections),
                'has_critical_issues': confidence_result['confidence_level'] in ['critical', 'low']
            }
        }
    
    def _validate_cuits(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida CUITs de empresa y cliente.
        
        Returns:
            {
                'empresa': Dict,
                'cliente': Dict,
                'errors': List[str],
                'warnings': List[str],
                'alerts': List[Dict]
            }
        """
        errors = []
        warnings = []
        alerts = []
        
        # Extraer partes
        partes = extracted_data.get('partes', {})
        empresa = partes.get('empresa', {})
        cliente = partes.get('cliente', {})
        
        # Validar CUIT empresa
        cuit_empresa_result = {'is_valid': False}
        if empresa and empresa.get('cuit'):
            cuit_empresa_result = self.cuit_validator.validate_complete(empresa['cuit'])
            
            if not cuit_empresa_result['is_valid']:
                errors.extend(cuit_empresa_result['errors'])
            
            warnings.extend(cuit_empresa_result['warnings'])
            
            # Crear alerta si hay error
            alert = self.cuit_validator.create_alert(cuit_empresa_result, 'partes.empresa.cuit')
            if alert:
                alerts.append(alert)
        else:
            errors.append("CUIT de empresa no encontrado")
        
        # Validar CUIT cliente
        cuit_cliente_result = {'is_valid': False}
        if cliente and cliente.get('cuit'):
            cuit_cliente_result = self.cuit_validator.validate_complete(cliente['cuit'])
            
            if not cuit_cliente_result['is_valid']:
                errors.extend(cuit_cliente_result['errors'])
            
            warnings.extend(cuit_cliente_result['warnings'])
            
            # Crear alerta si hay error
            alert = self.cuit_validator.create_alert(cuit_cliente_result, 'partes.cliente.cuit')
            if alert:
                alerts.append(alert)
        else:
            # Cliente sin CUIT es válido (puede ser consumidor final)
            warnings.append("Cliente sin CUIT (puede ser consumidor final)")
            cuit_cliente_result = {'is_valid': True}
        
        return {
            'cuit_empresa': cuit_empresa_result,
            'cuit_cliente': cuit_cliente_result,
            'errors': errors,
            'warnings': warnings,
            'alerts': alerts
        }
    
    def _validate_items(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida items (cálculos, cantidades, suma).
        
        Returns:
            {
                'is_valid': bool,
                'items_calculations_valid': bool,
                'items_sum_valid': bool,
                'has_negative_quantities': bool,
                'has_outliers': bool,
                'errors': List[str],
                'warnings': List[str],
                'corrections_applied': List[str],
                'alerts': List[Dict]
            }
        """
        items = extracted_data.get('items', [])
        
        # Obtener subtotal declarado
        fiscalidad = extracted_data.get('fiscalidad', {})
        totales = fiscalidad.get('totales', {})
        subtotal_declarado = totales.get('subtotal_gravado')
        
        # Validar items
        items_result = self.items_validator.validate_complete(items, subtotal_declarado)
        
        # Generar alertas
        alerts = self.items_validator.create_alerts(items_result)
        items_result['alerts'] = alerts
        
        return items_result
    
    def _validate_fiscal(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida fiscalidad (IVA, percepciones, totales).
        
        Returns:
            {
                'validation_errors': List[str],
                'validation_warnings': List[str],
                'validation_score': float,
                'advanced_validation': Dict,
                'alerts': List[Dict]
            }
        """
        # Validación fiscal avanzada
        fiscal_result = self.fiscal_validator.validate_complete_advanced(extracted_data)
        
        # Generar alertas
        alerts = self.fiscal_validator.create_alerts(fiscal_result)
        fiscal_result['alerts'] = alerts
        
        return fiscal_result
    
    def _prepare_confidence_input(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara el input para el calculador de confianza.
        
        Args:
            validation_results: Resultados de todas las validaciones
            
        Returns:
            Diccionario con formato esperado por ConfidenceScorer
        """
        cuits = validation_results.get('cuits', {})
        items = validation_results.get('items', {})
        fiscal = validation_results.get('fiscal', {})
        
        # Extraer validaciones avanzadas de fiscal
        fiscal_advanced = fiscal.get('advanced_validation', {})
        
        return {
            'cuit_empresa': cuits.get('cuit_empresa', {}),
            'cuit_cliente': cuits.get('cuit_cliente', {}),
            'items_calculation': {
                'is_valid': items.get('items_calculations_valid', False),
                'errors': items.get('errors', []),
                'warnings': items.get('warnings', [])
            },
            'items_sum': {
                'is_valid': items.get('items_sum_valid', True),
                'errors': [] if items.get('items_sum_valid', True) else ['Suma de items incorrecta'],
                'warnings': []
            },
            'iva_discrimination': fiscal_advanced.get('iva_discrimination', {}),
            'total_calculation': fiscal_advanced.get('total_calculation', {}),
            'percepciones_retenciones': fiscal_advanced.get('percepciones_retenciones', {})
        }
    
    def validate_quick(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validación rápida (solo validaciones críticas).
        
        Args:
            extracted_data: Datos extraídos
            
        Returns:
            Resultado simplificado con score y alertas críticas
        """
        start_time = time.time()
        
        # Solo CUITs y totales
        cuits_result = self._validate_cuits(extracted_data)
        
        # Validar total (sin detalles)
        fiscalidad = extracted_data.get('fiscalidad', {})
        total_result = self.fiscal_validator.validate_total_calculation(fiscalidad)
        
        # Score simple
        cuit_score = 1.0 if cuits_result['cuit_empresa']['is_valid'] else 0.0
        total_score = 1.0 if total_result['is_valid'] else 0.0
        quick_score = (cuit_score * 0.5) + (total_score * 0.5)
        
        processing_time = time.time() - start_time
        
        return {
            'quick_score': round(quick_score, 4),
            'confidence_level': self.confidence_scorer.get_confidence_level(quick_score),
            'requires_review': quick_score < 0.80,
            'cuit_empresa_valid': cuits_result['cuit_empresa']['is_valid'],
            'total_valid': total_result['is_valid'],
            'critical_errors': cuits_result['errors'] + total_result['errors'],
            'processing_time': round(processing_time, 4)
        }

