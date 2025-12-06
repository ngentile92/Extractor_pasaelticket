"""
🎯 Smart Cropper - Recortes inteligentes por región de factura

En lugar de zoom genérico, hace crops específicos de regiones donde
hay información clave, con instrucciones contextuales para cada región.

Estructura típica de factura argentina:
┌────────────────────────────────┐
│  HEADER (15-20%)               │  ← Datos empresa, cliente, CUIT
│  Emisor | Receptor             │
├────────────────────────────────┤
│                                │
│  TABLA DE ITEMS (45-55%)       │  ← Productos, cantidades, precios
│  Código | Desc | Cant | Precio │
│                                │
├────────────────────────────────┤
│  FOOTER (25-35%)               │  ← Subtotales, IVA, percepciones
│  Totales | CAE | Código QR     │
└────────────────────────────────┘
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class RegionCrop:
    """Representa un recorte de región específica."""
    path: str
    region_name: str  # 'header', 'items', 'footer', 'full'
    description: str
    extraction_focus: str  # Qué debe extraer el modelo de esta región
    bounds: Tuple[float, float, float, float]  # (left, top, right, bottom) en porcentajes
    size: Tuple[int, int]


class SmartCropper:
    """
    Recortador inteligente que divide la factura en regiones
    y genera crops optimizados para cada una.
    """
    
    # Definición de regiones típicas de factura argentina
    REGIONS = {
        'header': {
            'bounds': (0.0, 0.0, 1.0, 0.22),  # Top 22%
            'description': 'Encabezado: datos del emisor y receptor',
            'focus': '''EXTRAER DE ESTA REGIÓN:
- Razón social del EMISOR (empresa que emite la factura)
- CUIT del emisor (formato XX-XXXXXXXX-X, 11 dígitos)
- Condición IVA del emisor
- Domicilio del emisor
- Razón social del RECEPTOR/CLIENTE
- CUIT del cliente
- Condición IVA del cliente
- Tipo de comprobante (Factura A, B, C, Nota de Crédito)
- Número de comprobante (XXXXX-XXXXXXXX)
- Fecha de emisión

⚠️ Los CUITs tienen 11 dígitos. Si ves 10 o 12, hay error de lectura.'''
        },
        'items': {
            'bounds': (0.0, 0.18, 1.0, 0.70),  # Middle ~52%
            'description': 'Tabla de items/productos',
            'focus': '''EXTRAER DE ESTA REGIÓN - TABLA DE ITEMS:

⚠️⚠️⚠️ CRÍTICO - ESTRUCTURA DE COLUMNAS:
Las columnas de izquierda a derecha son:
1. CÓDIGO (izquierda) - Número largo (4-6 dígitos): 48, 197, 2843
2. DESCRIPCIÓN - Texto del producto
3. CANTIDAD (derecha de descripción) - Número PEQUEÑO (1-50): 1, 2, 4, 6, 8
4. UNIDAD - CJ, UN, KG, etc.
5. PRECIO UNITARIO - Precio por UNA unidad
6. SUBTOTAL - cantidad × precio_unitario

🔴 ERROR COMÚN: Confundir CÓDIGO con CANTIDAD
- Si extraes cantidad=48, 197, 2843... ¡ES EL CÓDIGO, NO LA CANTIDAD!
- Las cantidades reales son números pequeños: 1, 2, 4, 6, 8, 10, 12...

✅ VERIFICACIÓN: cantidad × precio_unitario ≈ subtotal
Si no cuadra, revisaste mal las columnas.'''
        },
        'footer': {
            'bounds': (0.0, 0.65, 1.0, 1.0),  # Bottom 35%
            'description': 'Pie: totales, impuestos, CAE',
            'focus': '''EXTRAER DE ESTA REGIÓN:
- Subtotal gravado (suma de items antes de IVA)
- IVA discriminado por alícuota (21%, 10.5%, 27%)
- Percepciones (IIBB, IVA, Ganancias)
- Retenciones si las hay
- Descuentos si los hay
- IMPORTE TOTAL (monto final a pagar)
- CAE (Código de Autorización Electrónica - 14 dígitos)
- Fecha de vencimiento del CAE

⚠️ El CAE tiene EXACTAMENTE 14 dígitos. Si tiene más o menos, hay error.'''
        },
        'items_table_only': {
            'bounds': (0.0, 0.25, 1.0, 0.60),  # Tabla más ajustada
            'description': 'Solo la tabla de items (ajustada)',
            'focus': '''TABLA DE ITEMS - LECTURA PRECISA:

Lee FILA por FILA, de arriba hacia abajo.
Para cada fila, lee de IZQUIERDA a DERECHA:

POSICIÓN 1 (izquierda): CÓDIGO del producto
POSICIÓN 2: DESCRIPCIÓN del producto  
POSICIÓN 3: CANTIDAD pedida (número PEQUEÑO, típicamente 1-20)
POSICIÓN 4: UNIDAD de medida
POSICIÓN 5: PRECIO UNITARIO
POSICIÓN 6 (derecha): SUBTOTAL de esa línea

⚠️ La CANTIDAD está a la DERECHA de la descripción, NO a la izquierda.
⚠️ El CÓDIGO está a la IZQUIERDA de la descripción.
⚠️ Si cantidad × precio ≠ subtotal, revisaste mal.'''
        },
        'quantities_column': {
            'bounds': (0.45, 0.20, 0.65, 0.70),  # Columna central donde están cantidades
            'description': 'Columna de cantidades (zoom específico)',
            'focus': '''COLUMNA DE CANTIDADES - VERIFICACIÓN:

Esta imagen muestra SOLO la columna de cantidades de la tabla.
Los números que ves aquí son las CANTIDADES de cada producto.

⚠️ IMPORTANTE:
- Las cantidades son números PEQUEÑOS: 1, 2, 4, 6, 8, 10, 12, 20, etc.
- Si ves números muy grandes (48, 197, 2843), esos son CÓDIGOS, no cantidades
- Las cantidades están alineadas verticalmente en esta columna

Lee de arriba hacia abajo y reporta cada cantidad.'''
        }
    }
    
    def __init__(self, temp_dir: Optional[str] = None):
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow es requerido. Instalar con: pip install Pillow")
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self._temp_files: List[str] = []
    
    def create_region_crops(
        self,
        image_path: str,
        regions: Optional[List[str]] = None,
        enhance: bool = True,
        zoom_factor: float = 1.5
    ) -> List[RegionCrop]:
        """
        Crea crops de regiones específicas de la factura.
        
        Args:
            image_path: Ruta a la imagen original
            regions: Lista de regiones a extraer. Default: ['header', 'items', 'footer']
            enhance: Si True, aplica mejoras de contraste/nitidez
            zoom_factor: Factor de escala para los crops (para mejor legibilidad)
        
        Returns:
            Lista de RegionCrop con las imágenes recortadas
        """
        if regions is None:
            regions = ['header', 'items', 'footer']
        
        crops = []
        
        try:
            img = Image.open(image_path)
            width, height = img.size
            base_name = Path(image_path).stem
            
            logger.info(f"🎯 SmartCropper: Procesando imagen {width}x{height}")
            logger.info(f"   Regiones a extraer: {regions}")
            
            for region_name in regions:
                if region_name not in self.REGIONS:
                    logger.warning(f"   ⚠️ Región desconocida: {region_name}")
                    continue
                
                region_def = self.REGIONS[region_name]
                bounds = region_def['bounds']
                
                # Calcular coordenadas de recorte
                left = int(width * bounds[0])
                top = int(height * bounds[1])
                right = int(width * bounds[2])
                bottom = int(height * bounds[3])
                
                # Recortar región
                region_img = img.crop((left, top, right, bottom))
                
                # Aplicar zoom para mejor legibilidad
                if zoom_factor != 1.0:
                    new_size = (
                        int(region_img.width * zoom_factor),
                        int(region_img.height * zoom_factor)
                    )
                    region_img = region_img.resize(new_size, Image.LANCZOS)
                
                # Aplicar mejoras si está habilitado
                if enhance:
                    region_img = self._enhance_region(region_img, region_name)
                
                # Guardar
                crop_path = self._save_crop(region_img, base_name, region_name)
                
                crops.append(RegionCrop(
                    path=crop_path,
                    region_name=region_name,
                    description=region_def['description'],
                    extraction_focus=region_def['focus'],
                    bounds=bounds,
                    size=region_img.size
                ))
                
                logger.info(f"   ✅ {region_name}: {region_img.size[0]}x{region_img.size[1]}")
            
            return crops
            
        except Exception as e:
            logger.error(f"❌ Error en SmartCropper: {e}")
            return []
    
    def _enhance_region(self, img: Image.Image, region_name: str) -> Image.Image:
        """Aplica mejoras específicas según la región."""
        
        # Para items, más contraste y nitidez (números pequeños)
        if 'items' in region_name:
            img = ImageEnhance.Contrast(img).enhance(1.3)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
        
        # Para header/footer, contraste moderado
        else:
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Sharpness(img).enhance(1.2)
        
        return img
    
    def _save_crop(self, img: Image.Image, base_name: str, region_name: str) -> str:
        """Guarda el crop en el directorio temporal."""
        filename = f"{base_name}_region_{region_name}.png"
        path = os.path.join(self.temp_dir, filename)
        
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        img.save(path, 'PNG', optimize=True)
        self._temp_files.append(path)
        
        return path
    
    def cleanup(self):
        """Elimina archivos temporales."""
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"No se pudo eliminar {path}: {e}")
        self._temp_files = []
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def build_regional_prompt(crops: List[RegionCrop], base_prompt: str) -> str:
    """
    Construye un prompt que guía al modelo sobre qué buscar en cada región.
    
    Args:
        crops: Lista de RegionCrop
        base_prompt: Prompt base de extracción
    
    Returns:
        Prompt completo con instrucciones por región
    """
    intro = f"""📋 ANÁLISIS POR REGIONES DE LA FACTURA

Te envío {len(crops)} recortes de diferentes regiones de la misma factura.
Cada región contiene información específica que debes extraer:

"""
    
    for i, crop in enumerate(crops, 1):
        intro += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📎 IMAGEN {i}: {crop.description.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{crop.extraction_focus}

"""
    
    intro += """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 INSTRUCCIONES FINALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Analiza CADA imagen por separado
2. Extrae la información indicada de CADA región
3. Combina todo en una respuesta JSON unificada
4. Si un dato aparece en múltiples regiones, usa el de mejor legibilidad

---

"""
    
    return intro + base_prompt


# ============================================================================
# FUNCIÓN DE CONVENIENCIA
# ============================================================================

def create_smart_crops(
    image_path: str,
    regions: Optional[List[str]] = None
) -> Tuple[List[RegionCrop], 'SmartCropper']:
    """
    Función de conveniencia para crear crops inteligentes.
    
    Returns:
        Tuple de (lista de crops, instancia del cropper para cleanup)
    """
    cropper = SmartCropper()
    crops = cropper.create_region_crops(image_path, regions)
    return crops, cropper

