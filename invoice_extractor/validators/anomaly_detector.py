"""
🚨 Anomaly Detector - Detección de datos sospechosos en extracciones

Este módulo detecta anomalías en los datos extraídos y genera alarmas
claras cuando hay dudas sobre la precisión de la extracción.

Principio: Es mejor emitir una alarma que entregar datos incorrectos.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Niveles de severidad de alertas."""
    INFO = "info"           # Información, no requiere acción
    WARNING = "warning"     # Sospechoso, revisar manualmente
    ERROR = "error"         # Probablemente incorrecto, requiere corrección
    CRITICAL = "critical"   # Definitivamente incorrecto, no usar sin revisar


@dataclass
class ExtractionAlert:
    """Alerta de extracción."""
    field: str              # Campo afectado (ej: "items[3].cantidad")
    message: str            # Descripción del problema
    severity: AlertSeverity
    suggestion: Optional[str] = None  # Sugerencia de corrección
    extracted_value: Any = None       # Valor extraído
    expected_range: Optional[str] = None  # Rango esperado
    confidence: float = 0.0  # 0-1, qué tan seguro está el detector


@dataclass 
class AnomalyReport:
    """Reporte completo de anomalías detectadas."""
    alerts: List[ExtractionAlert] = field(default_factory=list)
    is_reliable: bool = True
    requires_manual_review: bool = False
    critical_issues: int = 0
    error_issues: int = 0
    warning_issues: int = 0
    
    def add_alert(self, alert: ExtractionAlert):
        self.alerts.append(alert)
        if alert.severity == AlertSeverity.CRITICAL:
            self.critical_issues += 1
            self.is_reliable = False
            self.requires_manual_review = True
        elif alert.severity == AlertSeverity.ERROR:
            self.error_issues += 1
            self.requires_manual_review = True
        elif alert.severity == AlertSeverity.WARNING:
            self.warning_issues += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_reliable": self.is_reliable,
            "requires_manual_review": self.requires_manual_review,
            "summary": {
                "critical": self.critical_issues,
                "errors": self.error_issues,
                "warnings": self.warning_issues,
                "total": len(self.alerts)
            },
            "alerts": [
                {
                    "field": a.field,
                    "message": a.message,
                    "severity": a.severity.value,
                    "suggestion": a.suggestion,
                    "extracted_value": a.extracted_value,
                    "expected_range": a.expected_range,
                    "confidence": a.confidence
                }
                for a in self.alerts
            ]
        }


class AnomalyDetector:
    """
    Detector de anomalías en datos extraídos de facturas.
    
    Detecta problemas comunes como:
    - Cantidades sospechosamente grandes (posible confusión código/cantidad)
    - Matemáticas que no cuadran (cantidad × precio ≠ subtotal)
    - CUITs con formato inválido
    - Totales que no suman correctamente
    - Campos faltantes críticos
    """
    
    # Umbrales configurables
    MAX_REASONABLE_QUANTITY = 1000  # Cantidad máxima razonable
    MAX_TYPICAL_QUANTITY = 100      # Cantidad típica máxima
    MATH_TOLERANCE = 1.0            # Tolerancia en pesos para diferencias
    MIN_ITEM_SUBTOTAL = 0.01        # Subtotal mínimo válido
    
    def __init__(self):
        self.report = AnomalyReport()
    
    def analyze(self, extracted_data: Dict[str, Any]) -> AnomalyReport:
        """
        Analiza los datos extraídos y genera un reporte de anomalías.
        
        Args:
            extracted_data: Diccionario con datos extraídos de la factura
            
        Returns:
            AnomalyReport con todas las alertas detectadas
        """
        self.report = AnomalyReport()
        
        logger.info("🔍 Iniciando análisis de anomalías...")
        
        # 1. Validar items
        self._check_items(extracted_data.get('items', []))
        
        # 2. Validar CUITs
        self._check_cuits(extracted_data.get('partes', {}))
        
        # 3. Validar totales
        self._check_totals(extracted_data)
        
        # 4. Validar campos críticos
        self._check_required_fields(extracted_data)
        
        # 5. Validar coherencia fiscal
        self._check_fiscal_coherence(extracted_data)
        
        # Log resumen
        if self.report.alerts:
            logger.warning(f"⚠️ Detectadas {len(self.report.alerts)} anomalías:")
            for alert in self.report.alerts:
                icon = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}
                logger.warning(f"   {icon.get(alert.severity.value, '?')} [{alert.field}] {alert.message}")
        else:
            logger.info("✅ No se detectaron anomalías")
        
        return self.report
    
    def _check_items(self, items: List[Dict[str, Any]]):
        """Valida items individuales."""
        if not items:
            self.report.add_alert(ExtractionAlert(
                field="items",
                message="No se extrajeron items de la factura",
                severity=AlertSeverity.ERROR,
                suggestion="Verificar que la factura contenga una tabla de productos"
            ))
            return
        
        items_total = 0
        
        for i, item in enumerate(items):
            item_field = f"items[{i}]"
            
            # Obtener valores
            cantidad = self._safe_float(item.get('cantidad'))
            precio = self._safe_float(item.get('precio_unitario'))
            subtotal = self._safe_float(item.get('subtotal'))
            descripcion = item.get('descripcion', '')
            codigo = item.get('codigo', '')
            
            # Check 1: Cantidad sospechosamente grande
            if cantidad is not None and cantidad > self.MAX_TYPICAL_QUANTITY:
                severity = AlertSeverity.CRITICAL if cantidad > self.MAX_REASONABLE_QUANTITY else AlertSeverity.ERROR
                self.report.add_alert(ExtractionAlert(
                    field=f"{item_field}.cantidad",
                    message=f"Cantidad inusualmente grande ({cantidad}). ¿Posible confusión con código de producto?",
                    severity=severity,
                    suggestion="Verificar en el documento original. Las cantidades típicas son 1-50.",
                    extracted_value=cantidad,
                    expected_range="1-100 (típico)",
                    confidence=0.9
                ))
            
            # Check 2: Cantidad cero o negativa
            if cantidad is not None and cantidad <= 0:
                self.report.add_alert(ExtractionAlert(
                    field=f"{item_field}.cantidad",
                    message=f"Cantidad inválida ({cantidad})",
                    severity=AlertSeverity.ERROR,
                    extracted_value=cantidad,
                    expected_range="> 0"
                ))
            
            # Check 3: Verificación matemática cantidad × precio = subtotal
            if cantidad and precio and subtotal:
                expected_subtotal = cantidad * precio
                diff = abs(expected_subtotal - subtotal)
                
                if diff > self.MATH_TOLERANCE:
                    # Diferencia significativa
                    pct_diff = (diff / subtotal * 100) if subtotal else 100
                    severity = AlertSeverity.ERROR if pct_diff > 5 else AlertSeverity.WARNING
                    
                    self.report.add_alert(ExtractionAlert(
                        field=f"{item_field}",
                        message=f"Matemática no cuadra: {cantidad} × ${precio:,.2f} = ${expected_subtotal:,.2f}, pero subtotal dice ${subtotal:,.2f} (diff: ${diff:,.2f})",
                        severity=severity,
                        suggestion="Revisar cantidad, precio unitario y subtotal en el documento",
                        confidence=0.95
                    ))
            
            # Check 4: Subtotal muy pequeño o cero
            if subtotal is not None and subtotal < self.MIN_ITEM_SUBTOTAL:
                self.report.add_alert(ExtractionAlert(
                    field=f"{item_field}.subtotal",
                    message=f"Subtotal inválido o cero (${subtotal})",
                    severity=AlertSeverity.ERROR,
                    extracted_value=subtotal
                ))
            
            # Check 5: Descripción muy corta (posible error de lectura)
            if descripcion and len(descripcion.strip()) < 3:
                self.report.add_alert(ExtractionAlert(
                    field=f"{item_field}.descripcion",
                    message=f"Descripción muy corta: '{descripcion}'",
                    severity=AlertSeverity.WARNING,
                    extracted_value=descripcion,
                    suggestion="Verificar que la descripción esté completa"
                ))
            
            # Check 6: Código parece ser cantidad (número pequeño en campo código)
            if codigo and codigo.isdigit():
                codigo_num = int(codigo)
                if codigo_num <= 20 and cantidad and cantidad > 100:
                    self.report.add_alert(ExtractionAlert(
                        field=f"{item_field}",
                        message=f"Posible inversión código/cantidad: código='{codigo}', cantidad={cantidad}",
                        severity=AlertSeverity.CRITICAL,
                        suggestion=f"¿Debería ser código={int(cantidad)}, cantidad={codigo_num}?",
                        confidence=0.85
                    ))
            
            if subtotal:
                items_total += subtotal
        
        return items_total
    
    def _check_cuits(self, partes: Dict[str, Any]):
        """Valida CUITs de empresa y cliente, incluyendo dígito verificador."""
        
        for parte, nombre in [('empresa', 'emisor'), ('cliente', 'receptor')]:
            datos = partes.get(parte, {})
            cuit = datos.get('cuit')
            
            if not cuit:
                self.report.add_alert(ExtractionAlert(
                    field=f"partes.{parte}.cuit",
                    message=f"CUIT de {nombre} no extraído",
                    severity=AlertSeverity.WARNING,
                    suggestion="Verificar en el documento original"
                ))
                continue
            
            # Limpiar CUIT
            cuit_clean = ''.join(c for c in str(cuit) if c.isdigit())
            
            # Check longitud
            if len(cuit_clean) != 11:
                self.report.add_alert(ExtractionAlert(
                    field=f"partes.{parte}.cuit",
                    message=f"CUIT de {nombre} tiene {len(cuit_clean)} dígitos (debe tener 11)",
                    severity=AlertSeverity.ERROR,
                    extracted_value=cuit,
                    expected_range="11 dígitos",
                    suggestion="Verificar CUIT en el documento original"
                ))
                continue
            
            # Check prefijo válido
            if cuit_clean[:2] not in ['20', '23', '24', '27', '30', '33', '34']:
                self.report.add_alert(ExtractionAlert(
                    field=f"partes.{parte}.cuit",
                    message=f"CUIT de {nombre} tiene prefijo inválido: {cuit_clean[:2]}",
                    severity=AlertSeverity.WARNING,
                    extracted_value=cuit,
                    expected_range="Prefijo: 20,23,24,27 (persona) o 30,33,34 (empresa)",
                    suggestion="Verificar primeros dígitos del CUIT"
                ))
            
            # 🆕 Check dígito verificador (módulo 11)
            if len(cuit_clean) == 11:
                expected_verifier = self._calculate_cuit_verifier(cuit_clean[:10])
                actual_verifier = int(cuit_clean[10])
                
                if expected_verifier != actual_verifier:
                    self.report.add_alert(ExtractionAlert(
                        field=f"partes.{parte}.cuit",
                        message=f"CUIT de {nombre} tiene dígito verificador incorrecto (esperado: {expected_verifier}, encontrado: {actual_verifier})",
                        severity=AlertSeverity.WARNING,  # Warning porque puede ser error de OCR
                        extracted_value=cuit,
                        suggestion=f"Verificar CUIT en documento. El último dígito podría ser {expected_verifier} en lugar de {actual_verifier}",
                        confidence=0.8
                    ))
    
    def _calculate_cuit_verifier(self, cuit_base: str) -> int:
        """Calcula el dígito verificador de un CUIT (módulo 11)."""
        if len(cuit_base) != 10:
            return -1
        
        # Ponderadores para CUIT argentino
        weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        
        try:
            total = sum(int(cuit_base[i]) * weights[i] for i in range(10))
            remainder = total % 11
            
            if remainder == 0:
                return 0
            elif remainder == 1:
                return 9  # Caso especial
            else:
                return 11 - remainder
        except (ValueError, IndexError):
            return -1
    
    def _check_item_level_taxes(self, items: List[Dict[str, Any]], totales: Dict[str, Any]):
        """
        🆕 Valida impuestos y descuentos a nivel de item vs totales globales.
        
        Útil para facturas que tienen desglose de impuestos por línea
        (ej: Coca-Cola FEMSA con IVA e Impuestos Internos por item).
        """
        if not items:
            return
        
        # Verificar si algún item tiene datos de impuestos por línea
        has_item_taxes = any(
            item.get('iva_item') is not None or 
            item.get('descuento_item') is not None or
            item.get('impuestos_internos_item') is not None or
            item.get('subtotal_con_impuestos') is not None
            for item in items
        )
        
        if not has_item_taxes:
            return  # No hay impuestos por item, usar validación normal
        
        # Sumar impuestos por item
        sum_descuentos = 0
        sum_iva = 0
        sum_imp_internos = 0
        sum_otros = 0
        sum_subtotal_con_impuestos = 0
        sum_subtotal_neto = 0
        
        for item in items:
            sum_descuentos += self._safe_float(item.get('descuento_item')) or 0
            sum_iva += self._safe_float(item.get('iva_item')) or 0
            sum_imp_internos += self._safe_float(item.get('impuestos_internos_item')) or 0
            sum_otros += self._safe_float(item.get('otros_impuestos_item')) or 0
            sum_subtotal_con_impuestos += self._safe_float(item.get('subtotal_con_impuestos')) or 0
            sum_subtotal_neto += self._safe_float(item.get('subtotal_neto')) or 0
        
        # Comparar con totales globales
        total_iva_global = self._safe_float(totales.get('total_iva'))
        total_imp_int_global = self._safe_float(totales.get('total_impuestos_internos'))
        descuentos_global = self._safe_float(totales.get('descuentos'))
        
        # Validar IVA: suma de items vs total global
        if sum_iva > 0 and total_iva_global:
            diff_iva = abs(sum_iva - total_iva_global)
            if diff_iva > self.MATH_TOLERANCE * len(items):
                pct_diff = (diff_iva / total_iva_global * 100) if total_iva_global else 100
                severity = AlertSeverity.ERROR if pct_diff > 5 else AlertSeverity.WARNING
                
                self.report.add_alert(ExtractionAlert(
                    field="fiscalidad.totales.total_iva",
                    message=f"Suma IVA items (${sum_iva:,.2f}) ≠ IVA global (${total_iva_global:,.2f}). Diff: ${diff_iva:,.2f} ({pct_diff:.1f}%)",
                    severity=severity,
                    suggestion="Verificar IVA en cada línea y total global",
                    confidence=0.85
                ))
        
        # Validar Impuestos Internos
        if sum_imp_internos > 0 and total_imp_int_global:
            diff_imp = abs(sum_imp_internos - total_imp_int_global)
            if diff_imp > self.MATH_TOLERANCE * len(items):
                pct_diff = (diff_imp / total_imp_int_global * 100) if total_imp_int_global else 100
                severity = AlertSeverity.ERROR if pct_diff > 5 else AlertSeverity.WARNING
                
                self.report.add_alert(ExtractionAlert(
                    field="fiscalidad.totales.total_impuestos_internos",
                    message=f"Suma Imp.Internos items (${sum_imp_internos:,.2f}) ≠ global (${total_imp_int_global:,.2f}). Diff: ${diff_imp:,.2f}",
                    severity=severity,
                    suggestion="Verificar impuestos internos por línea",
                    confidence=0.85
                ))
        
        # Validar Descuentos
        if sum_descuentos > 0 and descuentos_global:
            diff_desc = abs(sum_descuentos - descuentos_global)
            if diff_desc > self.MATH_TOLERANCE * len(items):
                pct_diff = (diff_desc / descuentos_global * 100) if descuentos_global else 100
                severity = AlertSeverity.WARNING
                
                self.report.add_alert(ExtractionAlert(
                    field="fiscalidad.totales.descuentos",
                    message=f"Suma descuentos items (${sum_descuentos:,.2f}) ≠ descuentos global (${descuentos_global:,.2f})",
                    severity=severity,
                    suggestion="Verificar descuentos por línea y total",
                    confidence=0.8
                ))
        
        # Validar coherencia interna de items: subtotal - descuento + iva + otros = subtotal_con_impuestos
        for i, item in enumerate(items):
            subtotal = self._safe_float(item.get('subtotal')) or 0
            descuento = self._safe_float(item.get('descuento_item')) or 0
            subtotal_neto = self._safe_float(item.get('subtotal_neto'))
            iva = self._safe_float(item.get('iva_item')) or 0
            imp_int = self._safe_float(item.get('impuestos_internos_item')) or 0
            otros = self._safe_float(item.get('otros_impuestos_item')) or 0
            total_con_imp = self._safe_float(item.get('subtotal_con_impuestos'))
            
            # Si tiene subtotal_neto, verificar: subtotal - descuento = subtotal_neto
            if subtotal_neto is not None and subtotal > 0:
                expected_neto = subtotal - descuento
                if abs(expected_neto - subtotal_neto) > self.MATH_TOLERANCE:
                    self.report.add_alert(ExtractionAlert(
                        field=f"items[{i}].subtotal_neto",
                        message=f"Item '{item.get('descripcion', '')[:30]}': subtotal(${subtotal:,.2f}) - descuento(${descuento:,.2f}) ≠ subtotal_neto(${subtotal_neto:,.2f})",
                        severity=AlertSeverity.WARNING,
                        suggestion="Verificar cálculo de subtotal neto"
                    ))
            
            # Si tiene total con impuestos, verificar: subtotal_neto + iva + imp_int + otros = total
            if total_con_imp is not None:
                base = subtotal_neto if subtotal_neto is not None else (subtotal - descuento)
                expected_total = base + iva + imp_int + otros
                if abs(expected_total - total_con_imp) > self.MATH_TOLERANCE:
                    self.report.add_alert(ExtractionAlert(
                        field=f"items[{i}].subtotal_con_impuestos",
                        message=f"Item '{item.get('descripcion', '')[:30]}': base(${base:,.2f}) + impuestos(${iva + imp_int + otros:,.2f}) ≠ total(${total_con_imp:,.2f})",
                        severity=AlertSeverity.WARNING,
                        suggestion="Verificar cálculo de subtotal con impuestos"
                    ))
    
    def _check_totals(self, data: Dict[str, Any]):
        """Valida totales y sumas."""
        
        fiscalidad = data.get('fiscalidad', {})
        totales = fiscalidad.get('totales', {})
        items = data.get('items', [])
        
        # 🆕 Primero verificar si hay impuestos a nivel de item
        self._check_item_level_taxes(items, totales)
        
        # Suma de items (subtotal básico)
        items_sum = sum(self._safe_float(item.get('subtotal')) or 0 for item in items)
        
        # Si hay subtotal_neto en items, usar ese en lugar del subtotal
        items_neto_sum = sum(self._safe_float(item.get('subtotal_neto')) or 0 for item in items)
        if items_neto_sum > 0:
            items_sum = items_neto_sum
        
        # Subtotal declarado (subtotal_gravado o subtotal neto después de descuentos)
        subtotal_gravado = self._safe_float(totales.get('subtotal_gravado'))
        
        # Importe total
        importe_total = self._safe_float(totales.get('importe_total'))
        
        # Check: Suma de items vs subtotal
        if items_sum > 0 and subtotal_gravado:
            diff = abs(items_sum - subtotal_gravado)
            if diff > self.MATH_TOLERANCE * len(items):  # Tolerancia escala con items
                pct_diff = (diff / subtotal_gravado * 100)
                
                if pct_diff > 10:
                    severity = AlertSeverity.CRITICAL
                elif pct_diff > 5:
                    severity = AlertSeverity.ERROR
                else:
                    severity = AlertSeverity.WARNING
                
                self.report.add_alert(ExtractionAlert(
                    field="fiscalidad.totales.subtotal_gravado",
                    message=f"Suma de items (${items_sum:,.2f}) ≠ subtotal declarado (${subtotal_gravado:,.2f}). Diferencia: ${diff:,.2f} ({pct_diff:.1f}%)",
                    severity=severity,
                    suggestion="Revisar items individuales y subtotal",
                    confidence=0.9
                ))
        
        # Check: Total cero con items
        if items and importe_total is not None and importe_total == 0:
            self.report.add_alert(ExtractionAlert(
                field="fiscalidad.totales.importe_total",
                message="Importe total es $0 pero hay items extraídos",
                severity=AlertSeverity.CRITICAL,
                suggestion="Verificar el total en el documento original"
            ))
    
    def _check_required_fields(self, data: Dict[str, Any]):
        """Verifica campos críticos requeridos."""
        
        required_checks = [
            ('documento.tipo_comprobante', data.get('documento', {}).get('tipo_comprobante'), "Tipo de comprobante"),
            ('documento.numero_comprobante', data.get('documento', {}).get('numero_comprobante'), "Número de comprobante"),
            ('documento.fecha_emision', data.get('documento', {}).get('fecha_emision'), "Fecha de emisión"),
            ('partes.empresa.razon_social', data.get('partes', {}).get('empresa', {}).get('razon_social'), "Razón social del emisor"),
            ('fiscalidad.totales.importe_total', data.get('fiscalidad', {}).get('totales', {}).get('importe_total'), "Importe total"),
        ]
        
        for field, value, description in required_checks:
            if not value:
                self.report.add_alert(ExtractionAlert(
                    field=field,
                    message=f"{description} no extraído",
                    severity=AlertSeverity.WARNING,
                    suggestion=f"Verificar {description.lower()} en el documento"
                ))
    
    def _check_fiscal_coherence(self, data: Dict[str, Any]):
        """Verifica coherencia entre tipo de factura y condiciones IVA."""
        
        documento = data.get('documento', {})
        partes = data.get('partes', {})
        
        tipo = documento.get('tipo_comprobante', '').upper()
        codigo = documento.get('codigo')
        
        empresa_cond = partes.get('empresa', {}).get('condicion_iva', '').upper()
        cliente_cond = partes.get('cliente', {}).get('condicion_iva', '').upper()
        
        # Factura A: ambos deben ser Responsable Inscripto
        if codigo == '001' or 'FACTURA A' in tipo:
            if empresa_cond and 'RESPONSABLE INSCRIPTO' not in empresa_cond:
                self.report.add_alert(ExtractionAlert(
                    field="coherencia_fiscal",
                    message=f"Factura A pero emisor no es Responsable Inscripto (es: {empresa_cond})",
                    severity=AlertSeverity.WARNING,
                    suggestion="Verificar tipo de comprobante y condición IVA del emisor"
                ))
        
        # Factura C: emisor debe ser Monotributo
        if codigo == '011' or 'FACTURA C' in tipo:
            if empresa_cond and 'MONOTRIBUTO' not in empresa_cond:
                self.report.add_alert(ExtractionAlert(
                    field="coherencia_fiscal",
                    message=f"Factura C pero emisor no es Monotributo (es: {empresa_cond})",
                    severity=AlertSeverity.WARNING,
                    suggestion="Verificar tipo de comprobante y condición IVA del emisor"
                ))
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Convierte un valor a float de forma segura."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# Función de conveniencia
def detect_anomalies(extracted_data: Dict[str, Any]) -> AnomalyReport:
    """
    Detecta anomalías en datos extraídos.
    
    Args:
        extracted_data: Diccionario con datos extraídos
        
    Returns:
        AnomalyReport con alertas detectadas
    """
    detector = AnomalyDetector()
    return detector.analyze(extracted_data)

