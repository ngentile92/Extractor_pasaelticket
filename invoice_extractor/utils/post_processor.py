# invoice_extractor/utils/post_processor.py
"""
🎯 POST-PROCESADOR PRINCIPAL

Orquesta todo el pipeline de post-procesamiento:
1. Normalización de datos
2. Correcciones específicas
3. Validaciones fiscales y AFIP
4. Cálculo de validation_score

Este es el módulo principal que se llama desde views.py después de la extracción.

Referencia: CORRECCIONES_POST_EXTRACCION.md + PLAN_POST_PROCESAMIENTO.md
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from invoice_extractor.utils.normalization import normalize_all
from invoice_extractor.utils.corrections import apply_all_corrections
from invoice_extractor.validators.fiscal_validator import FiscalValidator
from invoice_extractor.validators.master_validator import MasterValidator

logger = logging.getLogger(__name__)

# Importar GeminiCorrector (solo si está disponible)
try:
    from invoice_extractor.services_gemini_corrector import GeminiCorrector
    GEMINI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ GeminiCorrector no disponible: {e}")
    GEMINI_AVAILABLE = False


class InvoicePostProcessor:
    """
    🎯 Post-procesador completo de facturas
    
    Pipeline:
    1. NORMALIZACIÓN: Limpieza de datos, conversión de valores nullish
    2. CORRECCIONES: Intercambios, consolidaciones, recálculos
    3. VALIDACIONES: Verificaciones AFIP y aritméticas
    4. SCORING: Cálculo de puntuación de calidad
    """
    
    def __init__(self, use_master_validator: bool = True, enable_gemini_retry: bool = True):
        """
        Args:
            use_master_validator: Si True, usa MasterValidator (completo con todos los validadores).
                                 Si False, usa solo FiscalValidator (compatible hacia atrás).
            enable_gemini_retry: Si True y hay errores matemáticos, intenta re-extracción con Gemini.
        """
        self.use_master_validator = use_master_validator
        self.enable_gemini_retry = enable_gemini_retry and GEMINI_AVAILABLE
        
        if use_master_validator:
            self.master_validator = MasterValidator()
        else:
            self.fiscal_validator = FiscalValidator()
        
        # Inicializar GeminiCorrector si está habilitado
        if self.enable_gemini_retry:
            try:
                self.gemini_corrector = GeminiCorrector()
                logger.info("✅ GeminiCorrector inicializado y listo para re-extracciones")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar GeminiCorrector: {e}")
                self.enable_gemini_retry = False
        
        self.processing_log = []
    
    def process(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🚀 Procesar datos extraídos completos
        
        Args:
            extracted_data: Datos crudos de LlamaExtract
        
        Returns:
            Dict con:
            - processed_data: Datos procesados y validados
            - validation_result: Resultado de validaciones
            - processing_metadata: Metadatos del procesamiento
        """
        start_time = datetime.now()
        self.processing_log = []
        
        try:
            # Log inicio
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
            # FASE 3: VALIDACIONES COMPLETAS
            # ==================================================================
            if self.use_master_validator:
                self._log("🎯 FASE 3: Validaciones completas (MasterValidator)")
                master_result = self.master_validator.validate_complete(corrected_data)
                
                # Adaptar resultado del MasterValidator al formato esperado
                validation_result = {
                    'validation_errors': master_result['errors'],
                    'validation_warnings': master_result['warnings'],
                    'validation_score': master_result['confidence_score'],
                    'has_validation_errors': len(master_result['errors']) > 0,
                    
                    # Información adicional del MasterValidator
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
                # Modo legacy con FiscalValidator solo
                self._log("🎯 FASE 3: Validaciones fiscales (FiscalValidator)")
                validation_result = self.fiscal_validator.validate_invoice_complete(corrected_data)
                self._log(f"   ✅ Validaciones completadas")
                self._log(f"   📊 Validation Score: {validation_result['validation_score']:.2%}")
                self._log(f"   ⚠️ Errores: {len(validation_result['validation_errors'])}")
                self._log(f"   📢 Warnings: {len(validation_result['validation_warnings'])}")
            
            # ==================================================================
            # FASE 4: METADATA Y RESULTADO FINAL
            # ==================================================================
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            self._log(f"✅ Post-procesamiento completado en {processing_time:.2f}s")
            
            # Construir resultado final
            result = {
                "processed_data": corrected_data,
                "validation_result": validation_result,
                "processing_metadata": {
                    "processing_time": processing_time,
                    "processing_timestamp": end_time.isoformat(),
                    "pipeline_version": "1.0.0",
                    "processing_log": self.processing_log,
                    "phases_executed": [
                        "normalization",
                        "corrections",
                        "fiscal_validation"
                    ]
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en post-procesamiento: {str(e)}", exc_info=True)
            self._log(f"❌ ERROR: {str(e)}")
            
            # Retornar datos originales con error
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
                    "pipeline_version": "1.0.0",
                    "processing_log": self.processing_log,
                    "error": str(e)
                }
            }
    
    def process_with_gemini_retry(
        self, 
        extracted_data: Dict[str, Any],
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        🔄 Procesar con posible re-extracción usando Gemini si hay errores matemáticos
        
        Flujo:
        1. Procesar primera extracción (LlamaExtract) normalmente
        2. Si hay errores matemáticos significativos Y file_path disponible:
           - Re-extraer con Gemini usando contexto de errores
           - Procesar nueva extracción
           - Comparar scores
           - Retornar la mejor
        3. Si no hay errores o no se puede re-extraer, retornar primera extracción
        
        Args:
            extracted_data: Datos extraídos por LlamaExtract
            file_path: Path al documento original (necesario para re-extracción)
        
        Returns:
            Resultado del mejor procesamiento
        """
        logger.warning("=" * 80)
        logger.warning("🔄 [GEMINI RETRY] Método process_with_gemini_retry llamado")
        logger.warning(f"   enable_gemini_retry: {self.enable_gemini_retry}")
        logger.warning(f"   file_path: {file_path}")
        logger.warning("=" * 80)
        
        # PASO 1: Procesar primera extracción (LlamaExtract)
        logger.info("=" * 80)
        logger.info("🎯 PROCESAMIENTO INICIAL (LlamaExtract)")
        logger.info("=" * 80)
        
        first_result = self.process(extracted_data)
        first_score = first_result["validation_result"]["validation_score"]
        first_errors = first_result["validation_result"]["validation_errors"]
        
        logger.info(f"📊 Score inicial: {first_score:.2%}")
        logger.info(f"❌ Errores iniciales: {len(first_errors)}")
        
        # PASO 2: Decidir si vale la pena re-extraer con Gemini
        if not self.enable_gemini_retry:
            logger.info("⚠️ GeminiCorrector no disponible, usando resultado inicial")
            return first_result
        
        if not file_path:
            logger.info("⚠️ file_path no disponible, no se puede re-extraer con Gemini")
            return first_result
        
        should_retry = self.gemini_corrector.should_retry_extraction(
            first_result["validation_result"]
        )
        
        if not should_retry:
            logger.info("✅ Score aceptable, no se necesita re-extracción")
            return first_result
        
        # PASO 3: Re-extraer con Gemini
        logger.info("")
        logger.info("=" * 80)
        logger.info("🔄 RE-EXTRACCIÓN CON GEMINI (errores matemáticos detectados)")
        logger.info("=" * 80)
        
        gemini_extracted = self.gemini_corrector.retry_extraction_with_gemini(
            file_path=file_path,
            original_data=extracted_data,
            validation_result=first_result["validation_result"]
        )
        
        if not gemini_extracted:
            logger.warning("⚠️ Re-extracción con Gemini falló, usando resultado inicial")
            return first_result
        
        # PASO 4: Procesar nueva extracción de Gemini
        logger.info("")
        logger.info("=" * 80)
        logger.info("🎯 PROCESAMIENTO DE EXTRACCIÓN GEMINI")
        logger.info("=" * 80)
        
        # Merge con datos originales (mantener partes y documento de LlamaExtract)
        merged_data = {
            **extracted_data,  # Base original
            **gemini_extracted  # Sobreescribir items y fiscalidad con Gemini
        }
        
        second_result = self.process(merged_data)
        second_score = second_result["validation_result"]["validation_score"]
        second_errors = second_result["validation_result"]["validation_errors"]
        
        logger.info(f"📊 Score con Gemini: {second_score:.2%}")
        logger.info(f"❌ Errores con Gemini: {len(second_errors)}")
        
        # PASO 5: Comparar y elegir la mejor
        logger.warning("")
        logger.warning("=" * 80)
        logger.warning("⚖️ COMPARACIÓN DE RESULTADOS")
        logger.warning("=" * 80)
        logger.warning(f"   LlamaExtract: {first_score:.2%} ({len(first_errors)} errores)")
        logger.warning(f"   Gemini:       {second_score:.2%} ({len(second_errors)} errores)")
        
        if second_score > first_score:
            improvement = (second_score - first_score) * 100
            logger.warning(f"✅ GEMINI GANÓ! Mejora: +{improvement:.1f}pp")
            logger.warning("=" * 80)
            
            # Agregar metadata de re-extracción
            second_result["processing_metadata"]["gemini_retry"] = {
                "was_retried": True,
                "first_score": first_score,
                "second_score": second_score,
                "improvement": improvement,
                "method_used": "gemini"
            }
            
            return second_result
        else:
            logger.warning(f"✅ LLAMAEXTRACT GANÓ! (o empate)")
            logger.warning("=" * 80)
            
            # Agregar metadata indicando que se intentó pero no mejoró
            first_result["processing_metadata"]["gemini_retry"] = {
                "was_retried": True,
                "first_score": first_score,
                "second_score": second_score,
                "improvement": 0,
                "method_used": "llamaextract"
            }
            
            return first_result
    
    def _log(self, message: str):
        """Agregar mensaje al log de procesamiento"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {message}"
        self.processing_log.append(log_entry)
        logger.info(message)
    
    def get_processing_summary(self, result: Dict[str, Any]) -> str:
        """
        📊 Generar resumen legible del procesamiento
        
        Args:
            result: Resultado del procesamiento
        
        Returns:
            String con resumen formateado
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
        
        # Mostrar errores si hay
        if validation.get("validation_errors"):
            summary_lines.append("❌ ERRORES DE VALIDACIÓN:")
            for error in validation["validation_errors"][:5]:  # Mostrar máximo 5
                summary_lines.append(f"   • {error}")
            if len(validation["validation_errors"]) > 5:
                summary_lines.append(f"   ... y {len(validation['validation_errors']) - 5} más")
            summary_lines.append("")
        
        # Mostrar warnings si hay
        if validation.get("validation_warnings"):
            summary_lines.append("⚠️  WARNINGS:")
            for warning in validation["validation_warnings"][:5]:  # Mostrar máximo 5
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
    
    Esta es la función principal que se llama desde views.py
    
    Args:
        extracted_data: Datos extraídos por LlamaExtract
    
    Returns:
        Resultado completo del procesamiento
    
    Example:
        >>> from invoice_extractor.services import InvoiceExtractionService
        >>> from invoice_extractor.utils.post_processor import process_invoice
        >>> 
        >>> # Extraer datos
        >>> extractor = InvoiceExtractionService()
        >>> extraction_result = extractor.extract_invoice_data("factura.pdf")
        >>> 
        >>> # Post-procesar
        >>> processed_result = process_invoice(extraction_result["data"])
        >>> 
        >>> # Usar datos procesados
        >>> final_data = processed_result["processed_data"]
        >>> validation_score = processed_result["validation_result"]["validation_score"]
    """
    processor = InvoicePostProcessor()
    result = processor.process(extracted_data)
    
    # Log resumen
    summary = processor.get_processing_summary(result)
    logger.info(f"\n{summary}")
    
    return result


def get_validation_score(extracted_data: Dict[str, Any]) -> float:
    """
    📊 Obtener solo el validation_score de una factura
    
    Args:
        extracted_data: Datos extraídos
    
    Returns:
        Score de validación (0.0 - 1.0)
    """
    result = process_invoice(extracted_data)
    return result["validation_result"]["validation_score"]


def get_validation_errors(extracted_data: Dict[str, Any]) -> list:
    """
    ❌ Obtener solo los errores de validación
    
    Args:
        extracted_data: Datos extraídos
    
    Returns:
        Lista de errores de validación
    """
    result = process_invoice(extracted_data)
    return result["validation_result"]["validation_errors"]


# =============================================================================
# TRANSFORMACIÓN A FORMATO LEGACY (estructura original)
# =============================================================================

def transform_to_legacy_format(processed_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    🔄 Transformar resultado procesado a formato legacy (estructura original)
    
    La estructura legacy espera:
    {
        "items": [...],
        "partes": {...},
        "documento": {...},
        "fiscalidad": {...},
        "metadata": {...}  // opcional: validation, processing, extraction
    }
    
    Args:
        processed_result: Resultado del post-procesamiento con estructura:
            {
                "raw_data": {...},
                "processed_data": {...},
                "validation_result": {...},
                "processing_metadata": {...},
                "extraction_metadata": {...}
            }
    
    Returns:
        Dict con estructura legacy + metadata opcional
    """
    processed_data = processed_result.get("processed_data", {})
    validation_result = processed_result.get("validation_result", {})
    processing_metadata = processed_result.get("processing_metadata", {})
    extraction_metadata = processed_result.get("extraction_metadata", {})
    
    # Construir estructura legacy
    legacy_format = {}
    
    # 1. ITEMS - Directo desde processed_data
    if "items" in processed_data:
        legacy_format["items"] = processed_data["items"]
    
    # 2. PARTES - Directo desde processed_data
    if "partes" in processed_data:
        legacy_format["partes"] = processed_data["partes"]
    
    # 3. DOCUMENTO - Directo desde processed_data
    if "documento" in processed_data:
        legacy_format["documento"] = processed_data["documento"]
    
    # 4. FISCALIDAD - Transformar estructura de impuestos
    if "fiscalidad" in processed_data:
        fiscalidad = processed_data["fiscalidad"].copy()
        
        # Transformar estructura de impuestos
        if "impuestos" in fiscalidad:
            impuestos = fiscalidad["impuestos"].copy()
            
            # Convertir iva_21, iva_105, etc. a estructura anidada {"21": valor, "105": valor}
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
            
            # Solo agregar 'iva' si hay valores
            if iva_nested:
                impuestos["iva"] = iva_nested
            
            fiscalidad["impuestos"] = impuestos
        
        # Asegurar que totales tiene 'descuentos'
        if "totales" in fiscalidad and "descuentos" not in fiscalidad["totales"]:
            fiscalidad["totales"]["descuentos"] = 0
        
        # Asegurar que calculos tiene 'items_count' y 'items_subtotal_total'
        if "calculos" in fiscalidad:
            if "items_count" not in fiscalidad["calculos"] and "items" in processed_data:
                fiscalidad["calculos"]["items_count"] = len(processed_data["items"])
            if "items_subtotal_total" not in fiscalidad["calculos"] and "items" in processed_data:
                items_total = sum(item.get("subtotal", 0) for item in processed_data["items"])
                fiscalidad["calculos"]["items_subtotal_total"] = items_total
        
        legacy_format["fiscalidad"] = fiscalidad
    
    # 5. METADATA (opcional) - Agregar información de validación, procesamiento, extracción
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
            "extraction_method": extraction_metadata.get("extractor", "llamaextract"),
            "schema_type": extraction_metadata.get("schema_type", "completo")
        }
    }
    
    # Agregar información de Gemini retry si está disponible
    gemini_retry = processing_metadata.get("gemini_retry", {})
    if gemini_retry.get("was_retried"):
        legacy_format["metadata"]["gemini_retry"] = {
            "used": True,
            "first_score": gemini_retry.get("first_score", 0),
            "second_score": gemini_retry.get("second_score", 0),
            "improvement": gemini_retry.get("improvement", 0),
            "method_used": gemini_retry.get("method_used", "llamaextract")
        }
    
    return legacy_format


# =============================================================================
# CLASE PARA PROCESAMIENTO POR LOTES
# =============================================================================

class BatchPostProcessor:
    """
    📦 Procesador de múltiples facturas en lote
    
    Útil para procesar múltiples documentos de manera eficiente
    """
    
    def __init__(self):
        self.processor = InvoicePostProcessor()
        self.results = []
    
    def process_batch(self, invoices_data: list) -> list:
        """
        Procesar múltiples facturas
        
        Args:
            invoices_data: Lista de datos extraídos
        
        Returns:
            Lista de resultados procesados
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
        
        Args:
            results: Lista de resultados
        
        Returns:
            Dict con estadísticas agregadas
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

