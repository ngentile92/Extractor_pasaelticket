"""
⚠️ Sistema de Alertas y Warnings

Genera alertas claras, concisas y accionables para errores de extracción.

Características:
- Mensajes en español, claros para usuarios
- Categorización por severidad (error, warning, info)
- Sugerencias de acción
- Códigos únicos para tracking

Uso:
    from invoice_extractor.core.alerts import AlertSystem, AlertLevel
    
    alerts = AlertSystem()
    alerts.add_error("CUIT_INVALID", "20-12345678-9", "Dígito verificador incorrecto")
    alerts.add_warning("TOTAL_MISMATCH", diff=5.50)
    
    print(alerts.get_summary())
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field as dataclass_field
import datetime


class AlertLevel(Enum):
    """Niveles de alerta."""
    ERROR = "error"      # Requiere corrección manual
    WARNING = "warning"  # Posible problema, verificar
    INFO = "info"        # Información útil


@dataclass
class Alert:
    """Una alerta individual."""
    code: str
    level: AlertLevel
    message: str
    alert_field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None
    created_at: datetime.datetime = dataclass_field(default_factory=datetime.datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            'code': self.code,
            'level': self.level.value,
            'message': self.message,
            'field': self.alert_field,
            'value': str(self.value) if self.value else None,
            'suggestion': self.suggestion,
        }
    
    def __str__(self) -> str:
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(self.level.value, "•")
        return f"{icon} [{self.code}] {self.message}"


class AlertSystem:
    """
    Sistema centralizado de alertas.
    
    Genera mensajes claros y accionables para problemas detectados.
    """
    
    # Catálogo de alertas predefinidas
    ALERT_CATALOG = {
        # CUITs
        "CUIT_INVALID": {
            "level": AlertLevel.ERROR,
            "template": "CUIT inválido: {value}",
            "suggestion": "Verificar el CUIT en el documento original o en AFIP"
        },
        "CUIT_DIGIT_ERROR": {
            "level": AlertLevel.ERROR,
            "template": "Dígito verificador incorrecto en CUIT {value}",
            "suggestion": "Posible error de OCR en último dígito (8↔0, 9↔4)"
        },
        "CUIT_FORMAT_ERROR": {
            "level": AlertLevel.WARNING,
            "template": "Formato de CUIT incorrecto: {value}",
            "suggestion": "Formato esperado: XX-XXXXXXXX-X"
        },
        
        # Totales
        "TOTAL_MISMATCH": {
            "level": AlertLevel.ERROR,
            "template": "Diferencia matemática de ${diff:.2f} en el total",
            "suggestion": "Revisar suma de items, IVA y percepciones"
        },
        "SUBTOTAL_MISMATCH": {
            "level": AlertLevel.WARNING,
            "template": "Subtotal no coincide con suma de items (diff: ${diff:.2f})",
            "suggestion": "Verificar precios y cantidades de items"
        },
        "IVA_CALCULATION_ERROR": {
            "level": AlertLevel.WARNING,
            "template": "IVA calculado ({calculated:.2f}) difiere del extraído ({extracted:.2f})",
            "suggestion": "Verificar alícuota de IVA aplicada"
        },
        
        # Items
        "ITEM_SUBTOTAL_ERROR": {
            "level": AlertLevel.WARNING,
            "template": "Item '{item}': subtotal no coincide (esperado: ${expected:.2f}, encontrado: ${found:.2f})",
            "suggestion": "Verificar cantidad × precio unitario"
        },
        "ITEM_MISSING_PRICE": {
            "level": AlertLevel.WARNING,
            "template": "Item '{item}' sin precio unitario",
            "suggestion": "Agregar precio unitario manualmente"
        },
        "ITEM_NEGATIVE_VALUE": {
            "level": AlertLevel.ERROR,
            "template": "Item con valor negativo: {item}",
            "suggestion": "Verificar si es descuento o nota de crédito"
        },
        
        # Documento
        "MISSING_CAE": {
            "level": AlertLevel.WARNING,
            "template": "CAE no encontrado en el documento",
            "suggestion": "Documento puede no ser fiscal válido"
        },
        "INVALID_DATE": {
            "level": AlertLevel.WARNING,
            "template": "Fecha inválida en campo '{field}': {value}",
            "suggestion": "Formato esperado: DD/MM/YYYY"
        },
        "FUTURE_DATE": {
            "level": AlertLevel.WARNING,
            "template": "Fecha en el futuro: {field} = {value}",
            "suggestion": "Verificar fecha del documento"
        },
        
        # Partes
        "MISSING_VENDOR_CUIT": {
            "level": AlertLevel.ERROR,
            "template": "CUIT del emisor no encontrado",
            "suggestion": "Dato requerido para validación fiscal"
        },
        "MISSING_CLIENT_DATA": {
            "level": AlertLevel.INFO,
            "template": "Datos del cliente incompletos",
            "suggestion": "Normal en Facturas B/C a consumidor final"
        },
        
        # Extracción
        "LOW_CONFIDENCE": {
            "level": AlertLevel.WARNING,
            "template": "Confianza de extracción baja: {score:.1%}",
            "suggestion": "Revisar datos manualmente"
        },
        "EXTRACTION_PARTIAL": {
            "level": AlertLevel.WARNING,
            "template": "Extracción parcial: faltan secciones {sections}",
            "suggestion": "Documento puede estar incompleto o ilegible"
        },
        "OCR_QUALITY_LOW": {
            "level": AlertLevel.INFO,
            "template": "Calidad de imagen puede afectar precisión",
            "suggestion": "Usar imagen de mayor resolución si está disponible"
        },
    }
    
    def __init__(self):
        """Inicializar sistema de alertas."""
        self.alerts: List[Alert] = []
    
    def add(
        self,
        code: str,
        alert_field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ) -> Alert:
        """
        Agregar una alerta usando el catálogo.
        
        Args:
            code: Código de alerta del catálogo
            alert_field: Campo relacionado (opcional)
            value: Valor problemático (opcional)
            **kwargs: Variables para el template del mensaje
        
        Returns:
            La alerta creada
        """
        if code not in self.ALERT_CATALOG:
            # Crear alerta genérica
            alert = Alert(
                code=code,
                level=AlertLevel.WARNING,
                message=str(kwargs.get('message', f'Alerta: {code}')),
                alert_field=alert_field,
                value=value
            )
        else:
            catalog_entry = self.ALERT_CATALOG[code]
            
            # Construir mensaje desde template
            template_vars = {'value': value, 'field': alert_field, **kwargs}
            try:
                message = catalog_entry['template'].format(**template_vars)
            except KeyError:
                message = catalog_entry['template']
            
            alert = Alert(
                code=code,
                level=catalog_entry['level'],
                message=message,
                alert_field=alert_field,
                value=value,
                suggestion=catalog_entry.get('suggestion')
            )
        
        self.alerts.append(alert)
        return alert
    
    def add_error(self, code: str, value: Any = None, message: str = None, **kwargs) -> Alert:
        """Agregar un error."""
        return self.add(code, value=value, message=message, **kwargs)
    
    def add_warning(self, code: str, value: Any = None, message: str = None, **kwargs) -> Alert:
        """Agregar un warning."""
        return self.add(code, value=value, message=message, **kwargs)
    
    def add_info(self, code: str, value: Any = None, message: str = None, **kwargs) -> Alert:
        """Agregar info."""
        return self.add(code, value=value, message=message, **kwargs)
    
    @property
    def errors(self) -> List[Alert]:
        """Obtener solo errores."""
        return [a for a in self.alerts if a.level == AlertLevel.ERROR]
    
    @property
    def warnings(self) -> List[Alert]:
        """Obtener solo warnings."""
        return [a for a in self.alerts if a.level == AlertLevel.WARNING]
    
    @property
    def has_errors(self) -> bool:
        """¿Hay errores críticos?"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """¿Hay warnings?"""
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Obtener resumen de alertas."""
        if not self.alerts:
            return "✅ Sin alertas"
        
        lines = []
        
        if self.errors:
            lines.append(f"❌ {len(self.errors)} error(es):")
            for alert in self.errors:
                lines.append(f"   • {alert.message}")
        
        if self.warnings:
            lines.append(f"⚠️ {len(self.warnings)} advertencia(s):")
            for alert in self.warnings:
                lines.append(f"   • {alert.message}")
        
        return "\n".join(lines)
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convertir todas las alertas a lista de diccionarios."""
        return [alert.to_dict() for alert in self.alerts]
    
    def clear(self):
        """Limpiar todas las alertas."""
        self.alerts = []


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def create_alert(code: str, **kwargs) -> Dict[str, Any]:
    """
    Crear una alerta individual.
    
    Args:
        code: Código de alerta
        **kwargs: Parámetros del mensaje
    
    Returns:
        Diccionario con la alerta
    """
    system = AlertSystem()
    alert = system.add(code, **kwargs)
    return alert.to_dict()


def format_validation_alerts(validation_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convertir resultado de validación a alertas formateadas.
    
    Args:
        validation_result: Resultado del validador
    
    Returns:
        Lista de alertas formateadas
    """
    system = AlertSystem()
    
    # Agregar errores de validación
    for error in validation_result.get('validation_errors', []):
        if isinstance(error, dict):
            system.add(
                error.get('code', 'VALIDATION_ERROR'),
                alert_field=error.get('field'),
                value=error.get('value'),
                message=error.get('message', str(error))
            )
        else:
            system.add('VALIDATION_ERROR', message=str(error))
    
    # Agregar warnings
    for warning in validation_result.get('validation_warnings', []):
        if isinstance(warning, dict):
            system.add(
                warning.get('code', 'VALIDATION_WARNING'),
                alert_field=warning.get('field'),
                value=warning.get('value'),
                message=warning.get('message', str(warning))
            )
        else:
            system.add('VALIDATION_WARNING', message=str(warning))
    
    # Alerta de confianza baja
    score = validation_result.get('validation_score', 1.0)
    if score < 0.7:
        system.add('LOW_CONFIDENCE', score=score)
    
    return system.to_list()

