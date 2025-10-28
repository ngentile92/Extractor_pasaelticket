"""
Validador de Items de Facturas

Este módulo implementa validaciones matemáticas para los items de una factura:
- Validación de cálculo: subtotal = cantidad × precio_unitario
- Validación de suma: Σ(subtotals) = total declarado
- Corrección de cantidades negativas
- Detección de outliers (valores anormales)
"""

from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class ItemsValidator:
    """
    Validador de consistencia matemática de items.
    """
    
    # Tolerancia para comparaciones numéricas (1 centavo)
    TOLERANCE = 0.01
    
    # Tolerancia para outliers (diferencias mayores al 10%)
    OUTLIER_THRESHOLD = 0.10
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """
        Convierte un valor a float de forma segura.
        
        Args:
            value: Valor a convertir
            default: Valor por defecto si la conversión falla
            
        Returns:
            float o default
        """
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def validate_item_calculation(item: Dict) -> Dict[str, Any]:
        """
        Valida que subtotal = cantidad × precio_unitario para un item.
        
        Args:
            item: Diccionario con datos del item
            
        Returns:
            {
                'is_valid': bool,
                'expected_subtotal': float,
                'actual_subtotal': float,
                'difference': float,
                'difference_percentage': float,
                'tolerance': float,
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        
        # Extraer valores de forma segura
        cantidad = ItemsValidator.safe_float(item.get('cantidad', 0))
        precio_unitario = ItemsValidator.safe_float(item.get('precio_unitario', 0))
        subtotal_declarado = ItemsValidator.safe_float(item.get('subtotal', 0))
        
        descripcion = item.get('descripcion', 'N/A')
        logger.debug(
            f"   📦 [ItemsValidator] Validando item '{descripcion}': "
            f"cantidad={cantidad}, precio=${precio_unitario:.2f}, subtotal=${subtotal_declarado:.2f}"
        )
        
        # Calcular subtotal esperado
        subtotal_calculado = cantidad * precio_unitario
        
        # Calcular diferencia
        diferencia = abs(subtotal_calculado - subtotal_declarado)
        
        # Calcular porcentaje de diferencia
        if subtotal_declarado != 0:
            diferencia_porcentaje = (diferencia / abs(subtotal_declarado)) * 100
        else:
            diferencia_porcentaje = 0.0
        
        # Validar
        is_valid = diferencia <= ItemsValidator.TOLERANCE
        
        if not is_valid:
            if diferencia_porcentaje < 1:  # < 1%
                warnings.append(
                    f"Diferencia menor: calculado ${subtotal_calculado:.2f} vs "
                    f"declarado ${subtotal_declarado:.2f} (diff: ${diferencia:.2f}, {diferencia_porcentaje:.2f}%)"
                )
            else:
                errors.append(
                    f"Subtotal incorrecto: cantidad ({cantidad}) × precio (${precio_unitario:.2f}) = "
                    f"${subtotal_calculado:.2f}, pero declarado ${subtotal_declarado:.2f} "
                    f"(diff: ${diferencia:.2f}, {diferencia_porcentaje:.2f}%)"
                )
        
        return {
            'is_valid': is_valid,
            'expected_subtotal': round(subtotal_calculado, 2),
            'actual_subtotal': round(subtotal_declarado, 2),
            'difference': round(diferencia, 2),
            'difference_percentage': round(diferencia_porcentaje, 2),
            'tolerance': ItemsValidator.TOLERANCE,
            'errors': errors,
            'warnings': warnings,
            'details': {
                'cantidad': cantidad,
                'precio_unitario': precio_unitario
            }
        }
    
    @staticmethod
    def validate_items_sum(items: List[Dict], declared_total: float) -> Dict[str, Any]:
        """
        Valida que la suma de subtotals de items = total declarado.
        
        Args:
            items: Lista de items
            declared_total: Total declarado
            
        Returns:
            {
                'is_valid': bool,
                'calculated_total': float,
                'declared_total': float,
                'difference': float,
                'difference_percentage': float,
                'items_with_errors': List[int],
                'items_calculations': List[Dict],
                'errors': List[str],
                'warnings': List[str]
            }
        """
        errors = []
        warnings = []
        items_with_errors = []
        items_calculations = []
        
        # Validar cada item y sumar
        total_calculado = 0.0
        for idx, item in enumerate(items):
            item_validation = ItemsValidator.validate_item_calculation(item)
            items_calculations.append({
                'index': idx,
                'descripcion': item.get('descripcion', 'N/A'),
                'validation': item_validation
            })
            
            if not item_validation['is_valid']:
                items_with_errors.append(idx)
            
            # Sumar el subtotal declarado (no el calculado)
            subtotal = ItemsValidator.safe_float(item.get('subtotal', 0))
            total_calculado += subtotal
        
        # Comparar con el total declarado
        declared = ItemsValidator.safe_float(declared_total, 0)
        diferencia = abs(total_calculado - declared)
        
        # Calcular porcentaje de diferencia
        if declared != 0:
            diferencia_porcentaje = (diferencia / abs(declared)) * 100
        else:
            diferencia_porcentaje = 0.0
        
        # Validar
        is_valid = diferencia <= ItemsValidator.TOLERANCE
        
        if not is_valid:
            if diferencia_porcentaje < 1:  # < 1%
                warnings.append(
                    f"Diferencia menor en total: suma items ${total_calculado:.2f} vs "
                    f"declarado ${declared:.2f} (diff: ${diferencia:.2f}, {diferencia_porcentaje:.2f}%)"
                )
            else:
                errors.append(
                    f"Suma de items no coincide: suma ${total_calculado:.2f} vs "
                    f"total declarado ${declared:.2f} (diff: ${diferencia:.2f}, {diferencia_porcentaje:.2f}%)"
                )
        
        # Advertir sobre items con errores
        if items_with_errors:
            warnings.append(f"{len(items_with_errors)} item(s) con errores de cálculo: índices {items_with_errors}")
        
        return {
            'is_valid': is_valid,
            'calculated_total': round(total_calculado, 2),
            'declared_total': round(declared, 2),
            'difference': round(diferencia, 2),
            'difference_percentage': round(diferencia_porcentaje, 2),
            'items_with_errors': items_with_errors,
            'items_calculations': items_calculations,
            'errors': errors,
            'warnings': warnings
        }
    
    @staticmethod
    def fix_negative_quantities(items: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Convierte cantidades negativas a positivas y recalcula subtotales.
        
        Args:
            items: Lista de items
            
        Returns:
            Tupla (items_corregidos, lista_de_correcciones)
        """
        correcciones = []
        items_corregidos = []
        
        for idx, item in enumerate(items):
            item_copia = item.copy()
            cantidad = ItemsValidator.safe_float(item.get('cantidad', 0))
            
            if cantidad < 0:
                # Convertir a positivo
                nueva_cantidad = abs(cantidad)
                item_copia['cantidad'] = nueva_cantidad
                
                # Recalcular subtotal si precio_unitario está disponible
                precio = ItemsValidator.safe_float(item.get('precio_unitario', 0))
                if precio != 0:
                    nuevo_subtotal = nueva_cantidad * precio
                    item_copia['subtotal'] = nuevo_subtotal
                    
                    correcciones.append(
                        f"Item {idx} ({item.get('descripcion', 'N/A')}): "
                        f"cantidad {cantidad} → {nueva_cantidad}, "
                        f"subtotal recalculado: ${nuevo_subtotal:.2f}"
                    )
                else:
                    # Solo corregir cantidad sin recalcular subtotal
                    subtotal_original = ItemsValidator.safe_float(item.get('subtotal', 0))
                    item_copia['subtotal'] = abs(subtotal_original)
                    
                    correcciones.append(
                        f"Item {idx} ({item.get('descripcion', 'N/A')}): "
                        f"cantidad {cantidad} → {nueva_cantidad}"
                    )
            
            items_corregidos.append(item_copia)
        
        return items_corregidos, correcciones
    
    @staticmethod
    def detect_outliers(items: List[Dict]) -> Dict[str, Any]:
        """
        Detecta items con valores anormales.
        
        Detecta:
        - Precios unitarios = 0 (o muy cercanos a 0)
        - Cantidades = 0 (o muy cercanos a 0)
        - Subtotales desproporcionados respecto al promedio
        - Precios unitarios muy altos/bajos respecto al promedio
        
        Args:
            items: Lista de items
            
        Returns:
            {
                'has_outliers': bool,
                'outliers': List[Dict],
                'warnings': List[str],
                'stats': Dict (estadísticas generales)
            }
        """
        outliers = []
        warnings = []
        
        if not items:
            return {
                'has_outliers': False,
                'outliers': [],
                'warnings': ['No hay items para analizar'],
                'stats': {}
            }
        
        # Calcular estadísticas
        precios = [ItemsValidator.safe_float(item.get('precio_unitario', 0)) for item in items]
        cantidades = [ItemsValidator.safe_float(item.get('cantidad', 0)) for item in items]
        subtotales = [ItemsValidator.safe_float(item.get('subtotal', 0)) for item in items]
        
        # Filtrar valores válidos para calcular promedios
        precios_validos = [p for p in precios if p > 0]
        cantidades_validas = [c for c in cantidades if c > 0]
        subtotales_validos = [s for s in subtotales if s > 0]
        
        precio_promedio = sum(precios_validos) / len(precios_validos) if precios_validos else 0
        cantidad_promedio = sum(cantidades_validas) / len(cantidades_validas) if cantidades_validas else 0
        subtotal_promedio = sum(subtotales_validos) / len(subtotales_validos) if subtotales_validos else 0
        
        # Detectar outliers
        for idx, item in enumerate(items):
            precio = ItemsValidator.safe_float(item.get('precio_unitario', 0))
            cantidad = ItemsValidator.safe_float(item.get('cantidad', 0))
            subtotal = ItemsValidator.safe_float(item.get('subtotal', 0))
            descripcion = item.get('descripcion', 'N/A')
            
            outlier_reasons = []
            
            # Precio = 0
            if precio == 0:
                outlier_reasons.append('precio_unitario = 0')
            
            # Cantidad = 0
            if cantidad == 0:
                outlier_reasons.append('cantidad = 0')
            
            # Subtotal = 0
            if subtotal == 0:
                outlier_reasons.append('subtotal = 0')
            
            # Precio muy alto o muy bajo (> 3x promedio o < 0.3x promedio)
            if precio_promedio > 0:
                if precio > precio_promedio * 3:
                    outlier_reasons.append(f'precio muy alto (${precio:.2f} vs promedio ${precio_promedio:.2f})')
                elif precio > 0 and precio < precio_promedio * 0.3:
                    outlier_reasons.append(f'precio muy bajo (${precio:.2f} vs promedio ${precio_promedio:.2f})')
            
            # Cantidad muy alta (> 3x promedio)
            if cantidad_promedio > 0 and cantidad > cantidad_promedio * 3:
                outlier_reasons.append(f'cantidad muy alta ({cantidad} vs promedio {cantidad_promedio:.1f})')
            
            # Subtotal desproporcionado
            if subtotal_promedio > 0:
                if subtotal > subtotal_promedio * 3:
                    outlier_reasons.append(f'subtotal muy alto (${subtotal:.2f} vs promedio ${subtotal_promedio:.2f})')
            
            if outlier_reasons:
                outlier = {
                    'index': idx,
                    'descripcion': descripcion,
                    'cantidad': cantidad,
                    'precio_unitario': precio,
                    'subtotal': subtotal,
                    'reasons': outlier_reasons
                }
                outliers.append(outlier)
                warnings.append(
                    f"Item {idx} ({descripcion}): {', '.join(outlier_reasons)}"
                )
        
        stats = {
            'total_items': len(items),
            'precio_promedio': round(precio_promedio, 2),
            'cantidad_promedio': round(cantidad_promedio, 2),
            'subtotal_promedio': round(subtotal_promedio, 2),
            'precio_min': round(min(precios_validos), 2) if precios_validos else 0,
            'precio_max': round(max(precios_validos), 2) if precios_validos else 0,
            'total_suma': round(sum(subtotales), 2)
        }
        
        return {
            'has_outliers': len(outliers) > 0,
            'outliers': outliers,
            'warnings': warnings,
            'stats': stats
        }
    
    @staticmethod
    def validate_complete(items: List[Dict], declared_subtotal: Optional[float] = None) -> Dict[str, Any]:
        """
        Validación completa de items.
        
        Args:
            items: Lista de items
            declared_subtotal: Subtotal declarado (opcional)
            
        Returns:
            {
                'is_valid': bool,
                'items_calculations_valid': bool,
                'items_sum_valid': bool,
                'has_negative_quantities': bool,
                'has_outliers': bool,
                'items_calculations': List[Dict],
                'sum_validation': Dict,
                'outliers': Dict,
                'errors': List[str],
                'warnings': List[str],
                'corrections_applied': List[str]
            }
        """
        logger.info(f"📦 [ItemsValidator] Iniciando validación de {len(items) if items else 0} items")
        
        errors = []
        warnings = []
        corrections_applied = []
        
        if not items:
            logger.warning("⚠️ [ItemsValidator] No hay items para validar")
            errors.append("No hay items para validar")
            return {
                'is_valid': False,
                'items_calculations_valid': False,
                'items_sum_valid': False,
                'has_negative_quantities': False,
                'has_outliers': False,
                'items_calculations': [],
                'sum_validation': {},
                'outliers': {},
                'errors': errors,
                'warnings': warnings,
                'corrections_applied': []
            }
        
        # 1. Corregir cantidades negativas
        logger.debug("   🔧 [ItemsValidator] PASO 1: Corrigiendo cantidades negativas")
        items_corregidos, correcciones_cantidad = ItemsValidator.fix_negative_quantities(items)
        has_negative_quantities = len(correcciones_cantidad) > 0
        corrections_applied.extend(correcciones_cantidad)
        
        if has_negative_quantities:
            logger.info(f"   ✅ [ItemsValidator] {len(correcciones_cantidad)} cantidad(es) negativa(s) corregida(s)")
        else:
            logger.debug("   ✅ [ItemsValidator] Sin cantidades negativas")
        
        # 2. Validar cálculos de items
        logger.debug("   🧮 [ItemsValidator] PASO 2: Validando cálculos individuales")
        items_calculations = []
        items_calculations_valid = True
        for idx, item in enumerate(items_corregidos):
            validation = ItemsValidator.validate_item_calculation(item)
            items_calculations.append({
                'index': idx,
                'descripcion': item.get('descripcion', 'N/A'),
                'validation': validation
            })
            
            if not validation['is_valid']:
                items_calculations_valid = False
                errors.extend(validation['errors'])
                warnings.extend(validation['warnings'])
                logger.warning(f"      ❌ [ItemsValidator] Item {idx} con error de cálculo")
        
        if items_calculations_valid:
            logger.info(f"   ✅ [ItemsValidator] Todos los cálculos de items son válidos")
        else:
            logger.warning(f"   ⚠️ [ItemsValidator] {sum(1 for ic in items_calculations if not ic['validation']['is_valid'])} item(s) con errores")
        
        # 3. Validar suma de items
        logger.debug("   ➕ [ItemsValidator] PASO 3: Validando suma de items")
        sum_validation = {}
        items_sum_valid = True
        if declared_subtotal is not None:
            sum_validation = ItemsValidator.validate_items_sum(items_corregidos, declared_subtotal)
            items_sum_valid = sum_validation['is_valid']
            errors.extend(sum_validation['errors'])
            warnings.extend(sum_validation['warnings'])
            
            if items_sum_valid:
                logger.info(f"   ✅ [ItemsValidator] Suma de items válida: ${sum_validation.get('calculated_total', 0):.2f}")
            else:
                logger.error(
                    f"   ❌ [ItemsValidator] Suma incorrecta: calculado ${sum_validation.get('calculated_total', 0):.2f} "
                    f"vs declarado ${declared_subtotal:.2f}"
                )
        else:
            logger.debug("   ⏭️ [ItemsValidator] Sin subtotal declarado, omitiendo validación de suma")
        
        # 4. Detectar outliers
        logger.debug("   🔍 [ItemsValidator] PASO 4: Detectando outliers")
        outliers_result = ItemsValidator.detect_outliers(items_corregidos)
        has_outliers = outliers_result['has_outliers']
        warnings.extend(outliers_result['warnings'])
        
        if has_outliers:
            logger.warning(f"   ⚠️ [ItemsValidator] {len(outliers_result['outliers'])} outlier(s) detectado(s)")
        else:
            logger.debug("   ✅ [ItemsValidator] Sin outliers detectados")
        
        # 5. Determinar validez general
        is_valid = items_calculations_valid and items_sum_valid and not has_outliers
        
        if is_valid:
            logger.info(f"✅ [ItemsValidator] Validación de items completada exitosamente")
        else:
            logger.error(f"❌ [ItemsValidator] Validación con {len(errors)} error(es) y {len(warnings)} warning(s)")
        
        return {
            'is_valid': is_valid,
            'items_calculations_valid': items_calculations_valid,
            'items_sum_valid': items_sum_valid,
            'has_negative_quantities': has_negative_quantities,
            'has_outliers': has_outliers,
            'items_calculations': items_calculations,
            'sum_validation': sum_validation,
            'outliers': outliers_result,
            'errors': errors,
            'warnings': warnings,
            'corrections_applied': corrections_applied
        }
    
    @staticmethod
    def create_alerts(validation_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Crea alertas estructuradas para frontend basadas en el resultado de validación.
        
        Args:
            validation_result: Resultado de validate_complete()
            
        Returns:
            Lista de alertas estructuradas
        """
        alerts = []
        
        # Alerta por cálculos incorrectos
        if not validation_result['items_calculations_valid']:
            for item_calc in validation_result['items_calculations']:
                if not item_calc['validation']['is_valid']:
                    idx = item_calc['index']
                    descripcion = item_calc['descripcion']
                    validation = item_calc['validation']
                    
                    alert = {
                        'level': 'error' if validation['errors'] else 'warning',
                        'category': 'item',
                        'field': f'items[{idx}].subtotal',
                        'message': validation['errors'][0] if validation['errors'] else validation['warnings'][0],
                        'current_value': validation['actual_subtotal'],
                        'expected_value': validation['expected_subtotal'],
                        'suggestion': f"Verificar cálculo: {validation['details']['cantidad']} × ${validation['details']['precio_unitario']:.2f}",
                        'location': f'items[{idx}].subtotal',
                        'can_auto_fix': True,
                        'details': validation
                    }
                    alerts.append(alert)
        
        # Alerta por suma incorrecta
        if validation_result.get('sum_validation') and not validation_result['items_sum_valid']:
            sum_val = validation_result['sum_validation']
            alert = {
                'level': 'critical' if sum_val['errors'] else 'warning',
                'category': 'total',
                'field': 'fiscalidad.totales.subtotal_gravado',
                'message': sum_val['errors'][0] if sum_val['errors'] else sum_val['warnings'][0],
                'current_value': sum_val['declared_total'],
                'expected_value': sum_val['calculated_total'],
                'suggestion': f"Revisar suma de items o subtotal declarado",
                'location': 'fiscalidad.totales.subtotal_gravado',
                'can_auto_fix': False,
                'details': sum_val
            }
            alerts.append(alert)
        
        # Alertas por outliers
        if validation_result['has_outliers']:
            for outlier in validation_result['outliers']['outliers']:
                alert = {
                    'level': 'warning',
                    'category': 'item',
                    'field': f'items[{outlier["index"]}]',
                    'message': f"Valor anormal detectado: {', '.join(outlier['reasons'])}",
                    'current_value': {
                        'cantidad': outlier['cantidad'],
                        'precio_unitario': outlier['precio_unitario'],
                        'subtotal': outlier['subtotal']
                    },
                    'expected_value': None,
                    'suggestion': f"Verificar datos del item '{outlier['descripcion']}'",
                    'location': f'items[{outlier["index"]}]',
                    'can_auto_fix': False,
                    'details': outlier
                }
                alerts.append(alert)
        
        # Alerta por cantidades negativas corregidas
        if validation_result['has_negative_quantities']:
            alert = {
                'level': 'info',
                'category': 'item',
                'field': 'items',
                'message': f"{len(validation_result['corrections_applied'])} item(s) con cantidad negativa corregidos automáticamente",
                'current_value': None,
                'expected_value': None,
                'suggestion': 'Las cantidades negativas fueron convertidas a positivas',
                'location': 'items',
                'can_auto_fix': True,
                'details': {
                    'corrections': validation_result['corrections_applied']
                }
            }
            alerts.append(alert)
        
        return alerts

