"""
Validador de CUIT Argentino

Este módulo implementa la validación completa de CUITs argentinos según
las reglas de AFIP, incluyendo:
- Validación de formato
- Cálculo y verificación de dígito verificador
- Identificación de tipo de persona (física/jurídica)
- Normalización de formato

Algoritmo de dígito verificador basado en módulo 11 (AFIP).
"""

from typing import Dict, Any, Optional, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class CUITValidator:
    """
    Validador completo de CUIT argentino.
    
    Formato válido: XX-XXXXXXXX-X
    - Primeros 2 dígitos: Tipo de persona
    - 8 dígitos centrales: Número de documento
    - 1 dígito final: Verificador
    
    Tipos de persona (prefijos válidos):
    - 20: Persona física masculina
    - 23: Persona física masculina (otro)
    - 24: Persona física femenina
    - 27: Persona física femenina (otro)
    - 30: Sociedad / Persona jurídica
    - 33: Sociedad / Persona jurídica (otro)
    - 34: Sociedad / Persona jurídica (otro)
    """
    
    # Prefijos válidos según AFIP
    VALID_PREFIXES = {
        '20': 'Persona física masculina',
        '23': 'Persona física masculina',
        '24': 'Persona física femenina',
        '27': 'Persona física femenina',
        '30': 'Persona jurídica',
        '33': 'Persona jurídica',
        '34': 'Persona jurídica'
    }
    
    # Multiplicadores para el algoritmo módulo 11
    MULTIPLIERS = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    
    @staticmethod
    def normalize_cuit(cuit: str) -> str:
        """
        Normaliza CUIT removiendo espacios, guiones y caracteres no numéricos,
        luego lo formatea a XX-XXXXXXXX-X.
        
        Args:
            cuit: CUIT en cualquier formato
            
        Returns:
            CUIT normalizado en formato XX-XXXXXXXX-X o string vacío si inválido
            
        Examples:
            normalize_cuit("30 71106763 9") -> "30-71106763-9"
            normalize_cuit("30711067639") -> "30-71106763-9"
            normalize_cuit("30-71106763-9") -> "30-71106763-9"
        """
        if not cuit:
            return ""
        
        # Remover todo excepto dígitos
        digits_only = re.sub(r'\D', '', str(cuit))
        
        # Debe tener exactamente 11 dígitos
        if len(digits_only) != 11:
            return digits_only  # Retornar sin formato para que falle validación
        
        # Formatear XX-XXXXXXXX-X
        return f"{digits_only[:2]}-{digits_only[2:10]}-{digits_only[10]}"
    
    @staticmethod
    def validate_format(cuit: str) -> Dict[str, Any]:
        """
        Valida el formato básico del CUIT.
        
        Args:
            cuit: CUIT a validar
            
        Returns:
            {
                'is_valid': bool,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        
        if not cuit:
            errors.append("CUIT vacío")
            return {'is_valid': False, 'errors': errors, 'warnings': warnings}
        
        # Normalizar
        normalized = CUITValidator.normalize_cuit(cuit)
        digits_only = re.sub(r'\D', '', normalized)
        
        # Validar longitud
        if len(digits_only) != 11:
            errors.append(f"CUIT debe tener 11 dígitos, tiene {len(digits_only)}")
            return {'is_valid': False, 'errors': errors, 'warnings': warnings}
        
        # Validar prefijo
        prefix = digits_only[:2]
        if prefix not in CUITValidator.VALID_PREFIXES:
            errors.append(f"Prefijo '{prefix}' no es válido. Prefijos válidos: {', '.join(CUITValidator.VALID_PREFIXES.keys())}")
        
        # Validar que todos sean dígitos
        if not digits_only.isdigit():
            errors.append("CUIT contiene caracteres no numéricos")
        
        is_valid = len(errors) == 0
        
        return {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings
        }
    
    @staticmethod
    def calculate_verifier_digit(cuit_base: str) -> int:
        """
        Calcula el dígito verificador según el algoritmo de AFIP (módulo 11).
        
        Algoritmo:
        1. Tomar los primeros 10 dígitos del CUIT
        2. Multiplicar cada dígito por [5,4,3,2,7,6,5,4,3,2]
        3. Sumar todos los productos
        4. Calcular: 11 - (suma % 11)
        5. Si resultado = 11, dígito verificador = 0
        6. Si resultado = 10, dígito verificador = 9
        
        Args:
            cuit_base: Primeros 10 dígitos del CUIT (sin el verificador)
            
        Returns:
            Dígito verificador calculado (0-9)
            
        Raises:
            ValueError: Si cuit_base no tiene 10 dígitos
        """
        # Limpiar y validar
        digits = re.sub(r'\D', '', str(cuit_base))
        
        if len(digits) < 10:
            raise ValueError(f"CUIT base debe tener al menos 10 dígitos, tiene {len(digits)}")
        
        # Tomar solo los primeros 10 dígitos
        digits = digits[:10]
        
        # Calcular suma ponderada
        suma = sum(int(d) * m for d, m in zip(digits, CUITValidator.MULTIPLIERS))
        
        # Calcular verificador
        verificador = 11 - (suma % 11)
        
        # Casos especiales
        if verificador == 11:
            verificador = 0
        elif verificador == 10:
            verificador = 9
        
        return verificador
    
    @staticmethod
    def validate_verifier_digit(cuit: str) -> Dict[str, Any]:
        """
        Valida que el dígito verificador del CUIT sea correcto.
        
        Args:
            cuit: CUIT completo (11 dígitos)
            
        Returns:
            {
                'is_valid': bool,
                'calculated_verifier': int,
                'actual_verifier': int,
                'errors': List[str]
            }
        """
        errors = []
        
        # Normalizar y extraer dígitos
        digits = re.sub(r'\D', '', str(cuit))
        
        if len(digits) != 11:
            errors.append(f"CUIT debe tener 11 dígitos para validar verificador")
            return {
                'is_valid': False,
                'calculated_verifier': None,
                'actual_verifier': None,
                'errors': errors
            }
        
        try:
            # Calcular verificador
            calculated = CUITValidator.calculate_verifier_digit(digits[:10])
            actual = int(digits[10])
            
            is_valid = (calculated == actual)
            
            if not is_valid:
                errors.append(
                    f"Dígito verificador incorrecto: esperado {calculated}, "
                    f"encontrado {actual}"
                )
            
            return {
                'is_valid': is_valid,
                'calculated_verifier': calculated,
                'actual_verifier': actual,
                'errors': errors
            }
            
        except Exception as e:
            errors.append(f"Error al calcular dígito verificador: {str(e)}")
            return {
                'is_valid': False,
                'calculated_verifier': None,
                'actual_verifier': None,
                'errors': errors
            }
    
    @staticmethod
    def get_person_type(cuit: str) -> Tuple[str, str]:
        """
        Determina el tipo de persona según el prefijo del CUIT.
        
        Args:
            cuit: CUIT a analizar
            
        Returns:
            Tupla (tipo, descripción)
            - tipo: 'fisica' | 'juridica' | 'unknown'
            - descripción: Descripción del tipo según AFIP
        """
        digits = re.sub(r'\D', '', str(cuit))
        
        if len(digits) < 2:
            return ('unknown', 'CUIT inválido')
        
        prefix = digits[:2]
        description = CUITValidator.VALID_PREFIXES.get(prefix, 'Tipo desconocido')
        
        # Determinar si es física o jurídica
        if prefix in ['20', '23', '24', '27']:
            tipo = 'fisica'
        elif prefix in ['30', '33', '34']:
            tipo = 'juridica'
        else:
            tipo = 'unknown'
        
        return (tipo, description)
    
    @staticmethod
    def validate_complete(cuit: str) -> Dict[str, Any]:
        """
        Validación completa de CUIT.
        
        Incluye:
        - Validación de formato
        - Validación de prefijo
        - Validación de dígito verificador
        - Identificación de tipo de persona
        - Normalización
        
        Args:
            cuit: CUIT a validar
            
        Returns:
            {
                'is_valid': bool,
                'cuit_normalized': str,
                'cuit_original': str,
                'person_type': str,  # 'fisica' | 'juridica' | 'unknown'
                'person_description': str,
                'format_valid': bool,
                'verifier_valid': bool,
                'errors': List[str],
                'warnings': List[str],
                'can_auto_fix': bool,
                'suggested_cuit': Optional[str]  # CUIT corregido si es posible
            }
        """
        logger.info(f"🆔 [CUITValidator] Iniciando validación de CUIT: '{cuit}'")
        
        result = {
            'is_valid': False,
            'cuit_normalized': '',
            'cuit_original': str(cuit),
            'person_type': 'unknown',
            'person_description': '',
            'format_valid': False,
            'verifier_valid': False,
            'errors': [],
            'warnings': [],
            'can_auto_fix': False,
            'suggested_cuit': None
        }
        
        if not cuit:
            logger.error(f"❌ [CUITValidator] CUIT vacío o None")
            result['errors'].append("CUIT vacío o None")
            return result
        
        # 1. Normalizar
        normalized = CUITValidator.normalize_cuit(cuit)
        result['cuit_normalized'] = normalized
        logger.debug(f"   📝 [CUITValidator] CUIT normalizado: '{cuit}' → '{normalized}'")
        
        # 2. Validar formato
        format_result = CUITValidator.validate_format(cuit)
        result['format_valid'] = format_result['is_valid']
        result['errors'].extend(format_result['errors'])
        result['warnings'].extend(format_result['warnings'])
        
        if format_result['is_valid']:
            logger.debug(f"   ✅ [CUITValidator] Formato válido")
        else:
            logger.warning(f"   ❌ [CUITValidator] Formato inválido: {format_result['errors']}")
        
        # Si el formato no es válido, no continuar
        if not format_result['is_valid']:
            return result
        
        # 3. Validar dígito verificador
        verifier_result = CUITValidator.validate_verifier_digit(normalized)
        result['verifier_valid'] = verifier_result['is_valid']
        
        if verifier_result['is_valid']:
            logger.debug(f"   ✅ [CUITValidator] Dígito verificador correcto: {verifier_result['actual_verifier']}")
        else:
            logger.warning(
                f"   ❌ [CUITValidator] Dígito verificador incorrecto: "
                f"esperado {verifier_result['calculated_verifier']}, "
                f"encontrado {verifier_result['actual_verifier']}"
            )
            result['errors'].extend(verifier_result['errors'])
            
            # Sugerir CUIT corregido
            if verifier_result['calculated_verifier'] is not None:
                digits = re.sub(r'\D', '', normalized)
                suggested = f"{digits[:2]}-{digits[2:10]}-{verifier_result['calculated_verifier']}"
                result['suggested_cuit'] = suggested
                result['can_auto_fix'] = True
                result['warnings'].append(
                    f"Sugerencia: CUIT correcto podría ser {suggested}"
                )
                logger.info(f"   💡 [CUITValidator] CUIT sugerido: {suggested}")
        
        # 4. Determinar tipo de persona
        person_type, person_desc = CUITValidator.get_person_type(normalized)
        result['person_type'] = person_type
        result['person_description'] = person_desc
        logger.debug(f"   👤 [CUITValidator] Tipo: {person_type} ({person_desc})")
        
        # 5. Determinar validez general
        result['is_valid'] = result['format_valid'] and result['verifier_valid']
        
        if result['is_valid']:
            logger.info(f"✅ [CUITValidator] CUIT válido: {normalized}")
        else:
            logger.error(f"❌ [CUITValidator] CUIT inválido: {len(result['errors'])} error(es)")
        
        return result
    
    @staticmethod
    def create_alert(validation_result: Dict[str, Any], field_name: str = "cuit") -> Optional[Dict[str, Any]]:
        """
        Crea una alerta estructurada para frontend basada en el resultado de validación.
        
        Args:
            validation_result: Resultado de validate_complete()
            field_name: Nombre del campo (ej: "empresa.cuit", "cliente.cuit")
            
        Returns:
            Alerta estructurada o None si no hay problemas
        """
        if validation_result['is_valid']:
            return None
        
        # Determinar nivel de severidad
        if not validation_result['format_valid']:
            level = 'critical'
        elif not validation_result['verifier_valid']:
            level = 'error'
        else:
            level = 'warning'
        
        # Crear alerta
        alert = {
            'level': level,
            'category': 'cuit',
            'field': field_name,
            'message': '; '.join(validation_result['errors']),
            'current_value': validation_result['cuit_original'],
            'expected_value': validation_result['suggested_cuit'],
            'suggestion': validation_result['warnings'][0] if validation_result['warnings'] else None,
            'location': field_name,
            'can_auto_fix': validation_result['can_auto_fix'],
            'details': {
                'cuit_normalized': validation_result['cuit_normalized'],
                'person_type': validation_result['person_type'],
                'person_description': validation_result['person_description'],
                'format_valid': validation_result['format_valid'],
                'verifier_valid': validation_result['verifier_valid']
            }
        }
        
        return alert


# Funciones de utilidad para uso rápido

def validate_cuit(cuit: str) -> bool:
    """
    Función simple para validar CUIT.
    
    Args:
        cuit: CUIT a validar
        
    Returns:
        True si el CUIT es válido, False en caso contrario
    """
    return CUITValidator.validate_complete(cuit)['is_valid']


def normalize_cuit(cuit: str) -> str:
    """
    Función simple para normalizar CUIT.
    
    Args:
        cuit: CUIT a normalizar
        
    Returns:
        CUIT normalizado en formato XX-XXXXXXXX-X
    """
    return CUITValidator.normalize_cuit(cuit)

