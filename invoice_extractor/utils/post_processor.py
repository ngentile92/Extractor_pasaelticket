# invoice_extractor/utils/post_processor.py
"""
🎯 POST-PROCESADOR PRINCIPAL

Orquesta todo el pipeline de post-procesamiento:
1. Normalización de datos
2. Correcciones específicas
3. Inferencia fiscal
4. Validaciones fiscales y AFIP
5. Detección de anomalías
6. Cálculo de validation_score

Este es el módulo principal que se llama desde views_gemini.py después de la extracción.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from invoice_extractor.utils.normalization import normalize_all
from invoice_extractor.utils.corrections import apply_all_corrections
from invoice_extractor.validators.fiscal_validator import FiscalValidator
from invoice_extractor.validators.master_validator import MasterValidator
from invoice_extractor.utils.fiscal_logic_inferencer import FiscalLogicInferencer
from invoice_extractor.validators.adaptive_fiscal_validator import AdaptiveFiscalValidator
from invoice_extractor.validators.anomaly_detector import AnomalyDetector, detect_anomalies

logger = logging.getLogger(__name__)


class InvoicePostProcessor:
    """
    🎯 Post-procesador completo de facturas
    
    Pipeline:
    1. NORMALIZACIÓN: Limpieza de datos, conversión de valores nullish
    2. CORRECCIONES: Intercambios, consolidaciones, recálculos
    3. INFERENCIA FISCAL: Normalización de lógica contable
    4. VALIDACIONES: Verificaciones AFIP y aritméticas
    5. ANOMALÍAS: Detección de valores sospechosos
    6. SCORING: Cálculo de puntuación de calidad
    """
    
    def __init__(
        self, 
        use_master_validator: bool = True, 
        enable_fiscal_inference: bool = True
    ):
        """
        Args:
            use_master_validator: Si True, usa MasterValidator (completo).
                                 Si False, usa solo FiscalValidator (legacy).
            enable_fiscal_inference: Si True, usa FiscalLogicInferencer.
        """
        self.use_master_validator = use_master_validator
        self.enable_fiscal_inference = enable_fiscal_inference
        
        if use_master_validator:
            self.master_validator = MasterValidator()
        else:
            self.fiscal_validator = FiscalValidator()
        
        # Inicializar Sistema de Inferencia Fiscal
        if enable_fiscal_inference:
            self.fiscal_inferencer = FiscalLogicInferencer(tolerance=0.10)
            self.adaptive_validator = AdaptiveFiscalValidator(tolerance=0.10)
            logger.info("✅ Sistema de Inferencia Fiscal activado")
        
        self.processing_log = []
    
    def process(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🚀 Procesar datos extraídos completos
        
        Args:
            extracted_data: Datos crudos de la extracción
        
        Returns:
            Dict con:
            - processed_data: Datos procesados y validados
            - validation_result: Resultado de validaciones
            - processing_metadata: Metadatos del procesamiento
        """
        start_time = datetime.now()
        self.processing_log = []
        
        try:
            self._log("🚀 Iniciando post-procesamiento")
            
            # ==================================================================
            # FASE 1: NORMALIZACIÓN
            # ==================================================================
            self._log("📋 FASE 1: Normalización de datos")
            normalized_data = normalize_all(extracted_data)
            self._log(f"   ✅ Normalización completada")
            
            # ==================================================================
            # FASE 2: CORRECCIONES
            # ==================================================================
            self._log("🔧 FASE 2: Aplicación de correcciones")
            corrected_data = apply_all_corrections(normalized_data)
            self._log(f"   ✅ Correcciones aplicadas")
            
            # ==================================================================
            # FASE 2.5: INFERENCIA FISCAL
            # ==================================================================
            if self.enable_fiscal_inference:
                self._log("🧮 FASE 2.5: Inferencia de lógica contable")
                
                # 1. Detectar completitud de la factura
                invoice_completeness = self.fiscal_inferencer.detect_invoice_completeness(corrected_data)
                self._log(f"   📊 Tipo de factura: {invoice_completeness['type'].upper()}")
                self._log(f"   📈 Completitud: {invoice_completeness['completeness_score']:.0%}")
                
                # 2. Corregir errores matemáticos en items
                if corrected_data.get('items'):
                    fixed_items, item_corrections = self.fiscal_inferencer.validate_and_fix_items(
                        corrected_data['items']
                    )
                    corrected_data['items'] = fixed_items
                    
                    if item_corrections:
                        self._log(f"   🔧 Items corregidos: {len(item_corrections)}")
                        for correction in item_corrections[:3]:
                            self._log(f"      • {correction}")
                        if len(item_corrections) > 3:
                            self._log(f"      • ... y {len(item_corrections) - 3} más")
                
                # 3. Normalizar a formato estándar
                corrected_data = self.fiscal_inferencer.normalize_to_standard_format(corrected_data)
                
                # Extraer info de inferencia
                calculos = corrected_data.get('fiscalidad', {}).get('calculos', {})
                tipo_subtotal = calculos.get('tipo_subtotal_original', 'desconocido')
                confianza = calculos.get('confianza_inferencia', 0.0)
                ajustes = calculos.get('ajustes_aplicados', [])
                
                self._log(f"   🎯 Tipo de subtotal inferido: {tipo_subtotal}")
                self._log(f"   📊 Confianza de inferencia: {confianza:.0%}")
                if ajustes:
                    self._log(f"   🔧 Ajustes aplicados: {len(ajustes)}")
                    for ajuste in ajustes[:2]:
                        self._log(f"      • {ajuste}")
                
                self._log(f"   ✅ Inferencia fiscal completada")
            
            # ==================================================================
            # FASE 3: VALIDACIONES COMPLETAS
            # ==================================================================
            if self.enable_fiscal_inference and 'invoice_completeness' in locals():
                self._log("🎯 FASE 3A: Validaciones adaptativas")
                adaptive_result = self.adaptive_validator.validate(
                    corrected_data,
                    invoice_completeness
                )
                self._log(f"   ✅ Validación adaptativa: {adaptive_result['validation_type']}")
                self._log(f"   📋 Checks: {len(adaptive_result['checks_performed'])}")
                
                if 'fiscalidad' not in corrected_data:
                    corrected_data['fiscalidad'] = {}
                if 'calculos' not in corrected_data['fiscalidad']:
                    corrected_data['fiscalidad']['calculos'] = {}
                
                corrected_data['fiscalidad']['calculos']['adaptive_validation'] = adaptive_result
            
            if self.use_master_validator:
                self._log("🎯 FASE 3B: Validaciones completas (MasterValidator)")
                master_result = self.master_validator.validate_complete(corrected_data)
                
                validation_result = {
                    'validation_errors': master_result['errors'],
                    'validation_warnings': master_result['warnings'],
                    'validation_score': master_result['confidence_score'],
                    'has_validation_errors': len(master_result['errors']) > 0,
                    'confidence_level': master_result['confidence_level'],
                    'requires_review': master_result['requires_review'],
                    'alerts': master_result['alerts'],
                    'recommendations': master_result['recommendations'],
                    'corrections_applied': master_result['corrections_applied'],
                    'validation_details': master_result['validation_results'],
                }
                
                self._log(f"   ✅ Validaciones completadas")
                self._log(f"   📊 Score: {validation_result['validation_score']:.2%} ({master_result['confidence_level'].upper()})")
                self._log(f"   🚨 Errores: {len(master_result['errors'])}")
                self._log(f"   ⚠️  Warnings: {len(master_result['warnings'])}")
                self._log(f"   🔔 Alertas: {len(master_result['alerts'])}")
                self._log(f"   🔧 Correcciones: {len(master_result['corrections_applied'])}")
                self._log(f"   🔍 Revisión: {'SÍ' if master_result['requires_review'] else 'NO'}")
            else:
                self._log("🎯 FASE 3: Validaciones fiscales (FiscalValidator)")
                validation_result = self.fiscal_validator.validate_invoice_complete(corrected_data)
                self._log(f"   ✅ Validaciones completadas")
                self._log(f"   📊 Validation Score: {validation_result['validation_score']:.2%}")
                self._log(f"   ⚠️ Errores: {len(validation_result['validation_errors'])}")
                self._log(f"   📢 Warnings: {len(validation_result['validation_warnings'])}")
            
            # ==================================================================
            # FASE 3.5: DETECCIÓN DE ANOMALÍAS
            # ==================================================================
            self._log("🚨 FASE 3.5: Detección de anomalías")
            anomaly_report = detect_anomalies(corrected_data)
            
            if anomaly_report.alerts:
                self._log(f"   ⚠️ Detectadas {len(anomaly_report.alerts)} anomalías")
                
                for alert in anomaly_report.alerts:
                    alert_msg = f"[{alert.field}] {alert.message}"
                    if alert.suggestion:
                        alert_msg += f" - Sugerencia: {alert.suggestion}"
                    
                    if alert.severity.value in ['critical', 'error']:
                        validation_result['validation_errors'].append(alert_msg)
                        self._log(f"   🚨 {alert_msg}")
                    else:
                        validation_result['validation_warnings'].append(alert_msg)
                        self._log(f"   ⚠️ {alert_msg}")
                
                validation_result['has_validation_errors'] = (
                    validation_result['has_validation_errors'] or 
                    anomaly_report.critical_issues > 0 or 
                    anomaly_report.error_issues > 0
                )
                validation_result['anomaly_report'] = anomaly_report.to_dict()
                
                if not anomaly_report.is_reliable:
                    validation_result['requires_review'] = True
                    validation_result['confidence_level'] = 'bajo'
                    self._log(f"   🚨 EXTRACCIÓN NO CONFIABLE - Requiere revisión manual")
            else:
                self._log(f"   ✅ No se detectaron anomalías")
                validation_result['anomaly_report'] = anomaly_report.to_dict()
            
            # ==================================================================
            # FASE 4: METADATA Y RESULTADO FINAL
            # ==================================================================
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            self._log(f"✅ Post-procesamiento completado en {processing_time:.2f}s")
            
            result = {
                "processed_data": corrected_data,
                "validation_result": validation_result,
                "processing_metadata": {
                    "processing_time": processing_time,
                    "processing_timestamp": end_time.isoformat(),
                    "pipeline_version": "2.0.0",
                    "processing_log": self.processing_log,
                    "phases_executed": [
                        "normalization",
                        "corrections",
                        "fiscal_inference" if self.enable_fiscal_inference else None,
                        "adaptive_validation" if self.enable_fiscal_inference else None,
                        "master_validation" if self.use_master_validator else "fiscal_validation",
                        "anomaly_detection"
                    ]
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en post-procesamiento: {str(e)}", exc_info=True)
            self._log(f"❌ ERROR: {str(e)}")
            
            return {
                "processed_data": extracted_data,
                "validation_result": {
                    "validation_errors": [f"Post-processing error: {str(e)}"],
                    "validation_warnings": [],
                    "validation_score": 0.0,
                    "has_validation_errors": True
                },
                "processing_metadata": {
                    "processing_time": 0,
                    "processing_timestamp": datetime.now().isoformat(),
                    "pipeline_version": "2.0.0",
                    "processing_log": self.processing_log,
                    "error": str(e)
                }
            }
    
    def _log(self, message: str):
        """Agregar mensaje al log de procesamiento"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        self.processing_log.append(log_entry)
        logger.info(message)
    
    def get_processing_summary(self, result: Dict[str, Any]) -> str:
        """
        📊 Generar resumen legible del procesamiento
        """
        validation = result.get("validation_result", {})
        metadata = result.get("processing_metadata", {})
        
        summary_lines = [
            "=" * 60,
            "📊 RESUMEN DE POST-PROCESAMIENTO",
            "=" * 60,
            f"⏱️  Tiempo de procesamiento: {metadata.get('processing_time', 0):.2f}s",
            f"📅 Timestamp: {metadata.get('processing_timestamp', 'N/A')}",
            f"🔢 Versión pipeline: {metadata.get('pipeline_version', 'N/A')}",
            "",
            "🎯 VALIDACIÓN:",
            f"   Score: {validation.get('validation_score', 0):.2%}",
            f"   Errores: {len(validation.get('validation_errors', []))}",
            f"   Warnings: {len(validation.get('validation_warnings', []))}",
            ""
        ]
        
        if validation.get("validation_errors"):
            summary_lines.append("❌ ERRORES DE VALIDACIÓN:")
            for error in validation["validation_errors"][:5]:
                summary_lines.append(f"   • {error}")
            if len(validation["validation_errors"]) > 5:
                summary_lines.append(f"   ... y {len(validation['validation_errors']) - 5} más")
            summary_lines.append("")
        
        if validation.get("validation_warnings"):
            summary_lines.append("⚠️  WARNINGS:")
            for warning in validation["validation_warnings"][:5]:
                summary_lines.append(f"   • {warning}")
            if len(validation["validation_warnings"]) > 5:
                summary_lines.append(f"   ... y {len(validation['validation_warnings']) - 5} más")
            summary_lines.append("")
        
        summary_lines.append("=" * 60)
        
        return "\n".join(summary_lines)


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def process_invoice(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    🚀 Función de conveniencia para procesar una factura
    """
    processor = InvoicePostProcessor()
    result = processor.process(extracted_data)
    
    summary = processor.get_processing_summary(result)
    logger.info(f"\n{summary}")
    
    return result


def get_validation_score(extracted_data: Dict[str, Any]) -> float:
    """
    📊 Obtener solo el validation_score de una factura
    """
    result = process_invoice(extracted_data)
    return result["validation_result"]["validation_score"]


def get_validation_errors(extracted_data: Dict[str, Any]) -> list:
    """
    ❌ Obtener solo los errores de validación
    """
    result = process_invoice(extracted_data)
    return result["validation_result"]["validation_errors"]


# =============================================================================
# TRANSFORMACIÓN A FORMATO LEGACY
# =============================================================================

def transform_to_legacy_format(processed_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔄 Transformar resultado procesado a formato legacy
    """
    processed_data = processed_result.get("processed_data", {})
    validation_result = processed_result.get("validation_result", {})
    processing_metadata = processed_result.get("processing_metadata", {})
    extraction_metadata = processed_result.get("extraction_metadata", {})
    
    legacy_format = {}
    
    if "items" in processed_data:
        legacy_format["items"] = processed_data["items"]
    
    if "partes" in processed_data:
        legacy_format["partes"] = processed_data["partes"]
    
    if "documento" in processed_data:
        legacy_format["documento"] = processed_data["documento"]
    
    if "fiscalidad" in processed_data:
        fiscalidad = processed_data["fiscalidad"].copy()
        
        if "impuestos" in fiscalidad:
            impuestos = fiscalidad["impuestos"].copy()
            
            iva_nested = {}
            if "iva_21" in impuestos and impuestos["iva_21"]:
                iva_nested["21"] = impuestos.pop("iva_21")
            if "iva_105" in impuestos and impuestos["iva_105"]:
                iva_nested["105"] = impuestos.pop("iva_105")
            if "iva_27" in impuestos and impuestos["iva_27"]:
                iva_nested["27"] = impuestos.pop("iva_27")
            if "iva_5" in impuestos and impuestos["iva_5"]:
                iva_nested["5"] = impuestos.pop("iva_5")
            if "iva_25" in impuestos and impuestos["iva_25"]:
                iva_nested["25"] = impuestos.pop("iva_25")
            
            if iva_nested:
                impuestos["iva"] = iva_nested
            
            fiscalidad["impuestos"] = impuestos
        
        if "totales" in fiscalidad and "descuentos" not in fiscalidad["totales"]:
            fiscalidad["totales"]["descuentos"] = 0
        
        if "calculos" in fiscalidad:
            if "items_count" not in fiscalidad["calculos"] and "items" in processed_data:
                fiscalidad["calculos"]["items_count"] = len(processed_data["items"])
            if "items_subtotal_total" not in fiscalidad["calculos"] and "items" in processed_data:
                items_total = sum(item.get("subtotal", 0) for item in processed_data["items"])
                fiscalidad["calculos"]["items_subtotal_total"] = items_total
        
        legacy_format["fiscalidad"] = fiscalidad
    
    legacy_format["metadata"] = {
        "validation": {
            "validation_score": validation_result.get("validation_score", 0.0),
            "confidence_level": validation_result.get("confidence_level", "unknown"),
            "has_validation_errors": validation_result.get("has_validation_errors", False),
            "requires_review": validation_result.get("requires_review", False),
            "errors_count": len(validation_result.get("validation_errors", [])),
            "warnings_count": len(validation_result.get("validation_warnings", [])),
            "alerts_count": len(validation_result.get("alerts", []))
        },
        "processing": {
            "processing_time": processing_metadata.get("processing_time", 0),
            "processing_timestamp": processing_metadata.get("processing_timestamp"),
            "pipeline_version": processing_metadata.get("pipeline_version"),
            "phases_executed": processing_metadata.get("phases_executed", [])
        },
        "extraction": {
            "extraction_time": extraction_metadata.get("extraction_time", 0),
            "extraction_method": extraction_metadata.get("extractor", "gemini"),
            "schema_type": extraction_metadata.get("schema_type", "completo")
        }
    }
    
    return legacy_format


# =============================================================================
# CLASE PARA PROCESAMIENTO POR LOTES
# =============================================================================

class BatchPostProcessor:
    """
    📦 Procesador de múltiples facturas en lote
    """
    
    def __init__(self):
        self.processor = InvoicePostProcessor()
        self.results = []
    
    def process_batch(self, invoices_data: list) -> list:
        """
        Procesar múltiples facturas
        """
        logger.info(f"📦 Procesando lote de {len(invoices_data)} facturas...")
        
        results = []
        for idx, invoice_data in enumerate(invoices_data):
            logger.info(f"   Procesando factura {idx + 1}/{len(invoices_data)}...")
            result = self.processor.process(invoice_data)
            results.append(result)
        
        logger.info(f"✅ Lote procesado: {len(results)} facturas")
        
        return results
    
    def get_batch_statistics(self, results: list) -> Dict[str, Any]:
        """
        Obtener estadísticas del lote procesado
        """
        if not results:
            return {}
        
        scores = [r["validation_result"]["validation_score"] for r in results]
        total_errors = sum(len(r["validation_result"]["validation_errors"]) for r in results)
        total_warnings = sum(len(r["validation_result"]["validation_warnings"]) for r in results)
        
        return {
            "total_processed": len(results),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "facturas_with_errors": sum(1 for r in results if r["validation_result"]["has_validation_errors"]),
            "facturas_perfect": sum(1 for s in scores if s == 1.0)
        }
