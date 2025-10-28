"""
Sistema de Scoring de Confiabilidad

Este módulo calcula el score de confiabilidad de una extracción de factura
basado en múltiples validaciones ponderadas.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calcula score de confiabilidad de la extracción.
    
    El score es un valor entre 0.0 y 1.0 donde:
    - 1.0 = Extracción perfecta, sin errores
    - 0.0 = Extracción con múltiples errores críticos
    """
    
    # Pesos de cada categoría de validación (total = 1.0)
    WEIGHTS = {
        'cuit_empresa': 0.15,        # 15% - Identificación empresa (crítico)
        'cuit_cliente': 0.10,        # 10% - Identificación cliente
        'items_calculation': 0.20,   # 20% - Cálculos de items (crítico)
        'items_sum': 0.15,           # 15% - Suma de items
        'iva_discrimination': 0.15,  # 15% - Discriminación de IVA
        'total_calculation': 0.20,   # 20% - Cálculo de total (crítico)
        'percepciones_retenciones': 0.05  # 5% - Percepciones/retenciones
    }
    
    # Niveles de confianza
    CONFIDENCE_LEVELS = {
        'high': {
            'threshold': 0.95,
            'label': 'Alta Confianza',
            'color': '#4CAF50',  # Verde
            'icon': '✅',
            'description': 'Datos correctos y confiables',
            'requires_review': False
        },
        'medium': {
            'threshold': 0.80,
            'label': 'Confianza Media',
            'color': '#FF9800',  # Naranja
            'icon': '⚠️',
            'description': 'Datos mayormente correctos, revisar advertencias',
            'requires_review': False
        },
        'low': {
            'threshold': 0.60,
            'label': 'Baja Confianza',
            'color': '#F44336',  # Rojo
            'icon': '❌',
            'description': 'Errores detectados, revisión recomendada',
            'requires_review': True
        },
        'critical': {
            'threshold': 0.0,
            'label': 'Confianza Crítica',
            'color': '#9C27B0',  # Púrpura
            'icon': '🚨',
            'description': 'Errores críticos, revisión obligatoria',
            'requires_review': True
        }
    }
    
    @staticmethod
    def calculate_category_score(validation_result: Dict[str, Any], category: str) -> float:
        """
        Calcula el score para una categoría específica.
        
        Args:
            validation_result: Resultado de validación de esa categoría
            category: Nombre de la categoría
            
        Returns:
            Score entre 0.0 y 1.0
        """
        if not validation_result:
            return 0.0
        
        # Si tiene is_valid, es binario
        if 'is_valid' in validation_result:
            return 1.0 if validation_result['is_valid'] else 0.0
        
        # Si tiene validation_score, usarlo
        if 'validation_score' in validation_result:
            return float(validation_result['validation_score'])
        
        # Si tiene errores/warnings, calcular basado en eso
        errors = validation_result.get('errors', [])
        warnings = validation_result.get('warnings', [])
        
        if len(errors) > 0:
            # Por cada error, reducir score
            score = max(0.0, 1.0 - (len(errors) * 0.25))
            return score
        elif len(warnings) > 0:
            # Warnings reducen menos el score
            score = max(0.5, 1.0 - (len(warnings) * 0.10))
            return score
        
        return 1.0
    
    def calculate_score(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula score global de confiabilidad.
        
        Args:
            validation_results: Diccionario con resultados de todas las validaciones
                {
                    'cuit_empresa': {...},
                    'cuit_cliente': {...},
                    'items_calculation': {...},
                    'items_sum': {...},
                    'iva_discrimination': {...},
                    'total_calculation': {...},
                    'percepciones_retenciones': {...}
                }
        
        Returns:
            {
                'overall_score': float (0.0 - 1.0),
                'category_scores': Dict[str, float],
                'weighted_scores': Dict[str, float],
                'confidence_level': str,
                'confidence_details': Dict,
                'requires_review': bool,
                'critical_issues': List[str],
                'warnings': List[str],
                'summary': str
            }
        """
        category_scores = {}
        weighted_scores = {}
        overall_score = 0.0
        
        # Calcular score por categoría
        for category, weight in self.WEIGHTS.items():
            if category in validation_results:
                score = self.calculate_category_score(validation_results[category], category)
                category_scores[category] = round(score, 4)
                weighted_scores[category] = round(score * weight, 4)
                overall_score += score * weight
            else:
                # Si no está presente, asumir score 0
                category_scores[category] = 0.0
                weighted_scores[category] = 0.0
        
        overall_score = round(overall_score, 4)
        
        # Determinar nivel de confianza
        confidence_level = self.get_confidence_level(overall_score)
        confidence_details = self.CONFIDENCE_LEVELS[confidence_level].copy()
        
        # Recopilar issues críticos y warnings
        critical_issues = []
        warnings = []
        
        for category, result in validation_results.items():
            if isinstance(result, dict):
                # Errors son críticos
                if 'errors' in result:
                    for error in result['errors']:
                        critical_issues.append(f"[{category}] {error}")
                
                # Warnings son menos severos
                if 'warnings' in result:
                    for warning in result['warnings']:
                        warnings.append(f"[{category}] {warning}")
                
                # Inconsistencies también son críticos
                if 'inconsistencies' in result:
                    for inconsistency in result['inconsistencies']:
                        critical_issues.append(f"[{category}] {inconsistency}")
        
        # Generar resumen
        summary = self._generate_summary(
            overall_score, 
            confidence_level, 
            len(critical_issues), 
            len(warnings)
        )
        
        return {
            'overall_score': overall_score,
            'category_scores': category_scores,
            'weighted_scores': weighted_scores,
            'confidence_level': confidence_level,
            'confidence_details': confidence_details,
            'requires_review': confidence_details['requires_review'],
            'critical_issues': critical_issues,
            'warnings': warnings,
            'summary': summary,
            'breakdown': {
                'total_categories': len(self.WEIGHTS),
                'categories_evaluated': len(category_scores),
                'categories_passed': sum(1 for score in category_scores.values() if score >= 0.9),
                'categories_failed': sum(1 for score in category_scores.values() if score < 0.6)
            }
        }
    
    def get_confidence_level(self, score: float) -> str:
        """
        Determina nivel de confianza según score.
        
        Args:
            score: Score de confiabilidad (0.0 - 1.0)
            
        Returns:
            'high' | 'medium' | 'low' | 'critical'
        """
        if score >= 0.95:
            return 'high'
        elif score >= 0.80:
            return 'medium'
        elif score >= 0.60:
            return 'low'
        else:
            return 'critical'
    
    def _generate_summary(
        self, 
        score: float, 
        level: str, 
        errors_count: int, 
        warnings_count: int
    ) -> str:
        """
        Genera un resumen textual del resultado.
        
        Args:
            score: Score general
            level: Nivel de confianza
            errors_count: Cantidad de errores
            warnings_count: Cantidad de warnings
            
        Returns:
            Resumen textual
        """
        level_details = self.CONFIDENCE_LEVELS[level]
        icon = level_details['icon']
        label = level_details['label']
        
        if level == 'high':
            summary = (
                f"{icon} {label} ({score:.1%}): "
                f"Datos correctos y confiables. "
            )
            if warnings_count > 0:
                summary += f"{warnings_count} advertencia(s) menor(es)."
            else:
                summary += "Sin problemas detectados."
        
        elif level == 'medium':
            summary = (
                f"{icon} {label} ({score:.1%}): "
                f"Datos mayormente correctos. "
            )
            if errors_count > 0:
                summary += f"{errors_count} error(es), "
            if warnings_count > 0:
                summary += f"{warnings_count} advertencia(s)."
        
        elif level == 'low':
            summary = (
                f"{icon} {label} ({score:.1%}): "
                f"Errores detectados, revisión recomendada. "
            )
            if errors_count > 0:
                summary += f"{errors_count} error(es), "
            if warnings_count > 0:
                summary += f"{warnings_count} advertencia(s)."
        
        else:  # critical
            summary = (
                f"{icon} {label} ({score:.1%}): "
                f"Errores críticos detectados, revisión obligatoria. "
            )
            if errors_count > 0:
                summary += f"{errors_count} error(es) críticos."
        
        return summary
    
    @staticmethod
    def get_recommendations(confidence_result: Dict[str, Any]) -> List[str]:
        """
        Genera recomendaciones basadas en el resultado de confianza.
        
        Args:
            confidence_result: Resultado de calculate_score()
            
        Returns:
            Lista de recomendaciones
        """
        recommendations = []
        
        level = confidence_result['confidence_level']
        category_scores = confidence_result['category_scores']
        
        # Recomendaciones por nivel
        if level == 'critical':
            recommendations.append(
                "🚨 CRÍTICO: Revisar manualmente todos los datos antes de procesar"
            )
            recommendations.append(
                "Considerar re-escanear el documento con mejor calidad"
            )
        elif level == 'low':
            recommendations.append(
                "⚠️ Revisar campos con errores antes de procesar"
            )
        
        # Recomendaciones por categoría
        if category_scores.get('cuit_empresa', 1.0) < 0.9:
            recommendations.append(
                "🆔 Verificar CUIT de empresa en documento original"
            )
        
        if category_scores.get('cuit_cliente', 1.0) < 0.9:
            recommendations.append(
                "🆔 Verificar CUIT de cliente en documento original"
            )
        
        if category_scores.get('items_calculation', 1.0) < 0.9:
            recommendations.append(
                "📦 Revisar cálculos de items (cantidad × precio = subtotal)"
            )
        
        if category_scores.get('iva_discrimination', 1.0) < 0.9:
            recommendations.append(
                "💰 Verificar discriminación de IVA por alícuota"
            )
        
        if category_scores.get('total_calculation', 1.0) < 0.9:
            recommendations.append(
                "🧮 Revisar cálculo de total (subtotal + IVA + percepciones - retenciones)"
            )
        
        # Si no hay recomendaciones específicas
        if not recommendations and level in ['medium', 'high']:
            recommendations.append(
                "✅ Datos en buen estado, puede procesar la factura"
            )
        
        return recommendations

