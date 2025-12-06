"""
🖼️ Multi-Image Processor for Enhanced Invoice Extraction

Genera múltiples versiones de una imagen de factura para enviar
a Gemini en una sola llamada, mejorando la precisión de extracción
sin aumentar el número de requests.

Estrategia:
1. Imagen original → Contexto general, layout, texto grande
2. Imagen zoom 2x → Números pequeños, detalles
3. Imagen alto contraste → Texto borroso, fondos difíciles
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ImageVariant:
    """Representa una variante de imagen procesada."""
    path: str
    description: str
    purpose: str
    size: Tuple[int, int]
    

class MultiImageProcessor:
    """
    Procesador que genera múltiples versiones de una imagen
    para mejorar la extracción de datos.
    """
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Args:
            temp_dir: Directorio para guardar imágenes temporales.
                     Si es None, usa el directorio temporal del sistema.
        """
        if not PIL_AVAILABLE:
            raise ImportError("PIL/Pillow es requerido. Instalar con: pip install Pillow")
        
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self._temp_files: List[str] = []
    
    def create_variants(
        self,
        image_path: str,
        include_original: bool = True,
        include_zoomed: bool = True,
        include_enhanced: bool = True,
        zoom_factor: float = 2.0,
        contrast_factor: float = 1.4,
        sharpness_factor: float = 1.5
    ) -> List[ImageVariant]:
        """
        Crea múltiples variantes de la imagen.
        
        Args:
            image_path: Ruta a la imagen original
            include_original: Incluir imagen original
            include_zoomed: Incluir versión con zoom
            include_enhanced: Incluir versión con alto contraste
            zoom_factor: Factor de zoom (2.0 = doble tamaño)
            contrast_factor: Factor de contraste (1.0 = sin cambio)
            sharpness_factor: Factor de nitidez
            
        Returns:
            Lista de ImageVariant con las rutas a las imágenes procesadas
        """
        variants = []
        
        try:
            img = Image.open(image_path)
            original_size = img.size
            base_name = Path(image_path).stem
            
            logger.info(f"🖼️ Procesando imagen: {original_size[0]}x{original_size[1]}")
            
            # 1. Imagen original (o ligeramente optimizada)
            if include_original:
                original_path = self._save_variant(
                    img, 
                    f"{base_name}_original",
                    "original"
                )
                variants.append(ImageVariant(
                    path=original_path,
                    description="Imagen original - contexto general",
                    purpose="layout, texto grande, estructura general",
                    size=original_size
                ))
                logger.info(f"   ✅ Original: {original_size}")
            
            # 2. Imagen con zoom
            if include_zoomed:
                zoomed_img = self._apply_zoom(img, zoom_factor)
                zoomed_path = self._save_variant(
                    zoomed_img,
                    f"{base_name}_zoomed",
                    "zoomed"
                )
                variants.append(ImageVariant(
                    path=zoomed_path,
                    description=f"Imagen zoom {zoom_factor}x - detalles numéricos",
                    purpose="números pequeños, códigos, cantidades, precios",
                    size=zoomed_img.size
                ))
                logger.info(f"   ✅ Zoomed: {zoomed_img.size}")
            
            # 3. Imagen con alto contraste y nitidez
            if include_enhanced:
                enhanced_img = self._apply_enhancement(
                    img, 
                    contrast_factor, 
                    sharpness_factor
                )
                enhanced_path = self._save_variant(
                    enhanced_img,
                    f"{base_name}_enhanced",
                    "enhanced"
                )
                variants.append(ImageVariant(
                    path=enhanced_path,
                    description="Imagen alto contraste - texto difícil",
                    purpose="texto borroso, fondos complejos, sellos",
                    size=enhanced_img.size
                ))
                logger.info(f"   ✅ Enhanced: {enhanced_img.size}")
            
            return variants
            
        except Exception as e:
            logger.error(f"❌ Error procesando imagen: {e}")
            # Fallback: retornar solo la original
            return [ImageVariant(
                path=image_path,
                description="Imagen original (fallback)",
                purpose="extracción general",
                size=(0, 0)
            )]
    
    def _apply_zoom(self, img: Image.Image, factor: float) -> Image.Image:
        """Aplica zoom a la imagen."""
        new_size = (int(img.width * factor), int(img.height * factor))
        return img.resize(new_size, Image.LANCZOS)
    
    def _apply_enhancement(
        self, 
        img: Image.Image, 
        contrast: float,
        sharpness: float
    ) -> Image.Image:
        """Aplica mejoras de contraste y nitidez."""
        # Contraste
        img = ImageEnhance.Contrast(img).enhance(contrast)
        
        # Nitidez
        img = ImageEnhance.Sharpness(img).enhance(sharpness)
        
        # Opcional: auto-contraste para normalizar niveles
        if img.mode == 'RGB':
            img = ImageOps.autocontrast(img, cutoff=1)
        
        return img
    
    def _save_variant(
        self, 
        img: Image.Image, 
        name: str, 
        variant_type: str
    ) -> str:
        """Guarda una variante de imagen en el directorio temporal."""
        # Usar PNG para mejor calidad (sin pérdida)
        filename = f"{name}_{variant_type}.png"
        path = os.path.join(self.temp_dir, filename)
        
        # Convertir a RGB si es necesario (para evitar problemas con RGBA)
        if img.mode == 'RGBA':
            img = img.convert('RGB')
        
        img.save(path, 'PNG', optimize=True)
        self._temp_files.append(path)
        
        return path
    
    def cleanup(self):
        """Elimina los archivos temporales creados."""
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


def create_image_variants(
    image_path: str,
    zoom_factor: float = 2.0,
    contrast_factor: float = 1.4
) -> List[ImageVariant]:
    """
    Función de conveniencia para crear variantes de imagen.
    
    Args:
        image_path: Ruta a la imagen
        zoom_factor: Factor de zoom para la versión ampliada
        contrast_factor: Factor de contraste para la versión mejorada
        
    Returns:
        Lista de ImageVariant
    """
    processor = MultiImageProcessor()
    return processor.create_variants(
        image_path,
        zoom_factor=zoom_factor,
        contrast_factor=contrast_factor
    )


# ============================================================================
# PROMPT BUILDER PARA MULTI-IMAGEN
# ============================================================================

def build_multi_image_prompt(variants: List[ImageVariant], base_prompt: str) -> str:
    """
    Construye el prompt que explica las múltiples imágenes a Gemini.
    
    Args:
        variants: Lista de variantes de imagen
        base_prompt: Prompt base de extracción
        
    Returns:
        Prompt completo con instrucciones para usar las múltiples imágenes
    """
    
    intro = """📷 INSTRUCCIONES DE IMAGEN MÚLTIPLE:
Te envío {count} versiones de la MISMA factura, cada una optimizada para diferentes propósitos:

""".format(count=len(variants))
    
    for i, variant in enumerate(variants, 1):
        intro += f"""📎 IMAGEN {i}: {variant.description}
   Usar para: {variant.purpose}

"""
    
    intro += """⚠️ IMPORTANTE: 
- Usa la imagen que mejor te sirva para cada dato
- Para números pequeños (cantidades, precios), prefiere la imagen con ZOOM
- Para texto borroso, prefiere la imagen con ALTO CONTRASTE
- Para entender el layout general, usa la imagen ORIGINAL

---

"""
    
    return intro + base_prompt


# ============================================================================
# VALIDACIÓN DE EXTRACCIÓN CON RE-ANÁLISIS
# ============================================================================

class ExtractionValidator:
    """
    Valida los datos extraídos y determina si se necesita re-análisis.
    """
    
    TOLERANCE = 1.0  # Tolerancia de $1 para diferencias de redondeo
    
    @staticmethod
    def needs_reanalysis(extracted_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Determina si los datos extraídos necesitan re-análisis.
        
        Args:
            extracted_data: Datos extraídos de la factura
            
        Returns:
            Tuple de (necesita_reanalisis, lista_de_problemas)
        """
        problems = []
        
        # Obtener datos
        items = extracted_data.get('items', [])
        fiscalidad = extracted_data.get('fiscalidad', {})
        totales = fiscalidad.get('totales', {})
        
        # Validación 1: Suma de items vs subtotal
        if items:
            items_sum = sum(
                float(item.get('subtotal', 0) or 0) 
                for item in items
            )
            subtotal_declared = float(totales.get('subtotal_gravado', 0) or 0)
            
            if subtotal_declared > 0:
                diff = abs(items_sum - subtotal_declared)
                if diff > ExtractionValidator.TOLERANCE:
                    problems.append(
                        f"Suma items (${items_sum:,.2f}) != subtotal (${subtotal_declared:,.2f}), diff=${diff:,.2f}"
                    )
        
        # Validación 2: Items con subtotal = 0 o None
        zero_items = [
            i for i, item in enumerate(items) 
            if not item.get('subtotal') or float(item.get('subtotal', 0)) == 0
        ]
        if zero_items:
            problems.append(f"Items sin subtotal: {zero_items}")
        
        # Validación 3: Cantidad de items muy diferente a lo esperado
        # (heurística: si hay muchos items con precio_unitario = subtotal, 
        #  probablemente la cantidad es incorrecta)
        suspicious_qty = [
            i for i, item in enumerate(items)
            if item.get('cantidad', 1) == 1 and 
               item.get('precio_unitario') == item.get('subtotal') and
               float(item.get('subtotal', 0)) > 10000
        ]
        if len(suspicious_qty) > len(items) * 0.5:
            problems.append(f"Posibles cantidades incorrectas en items: {suspicious_qty}")
        
        # Validación 4: Total muy diferente al esperado
        total_declared = float(totales.get('importe_total', 0) or 0)
        iva_total = sum(
            float(v) for v in fiscalidad.get('impuestos', {}).get('iva', {}).values()
            if v
        )
        subtotal = float(totales.get('subtotal_gravado', 0) or 0)
        
        if total_declared > 0 and subtotal > 0:
            expected_min = subtotal  # Total mínimo = subtotal (sin IVA tipo C)
            expected_max = subtotal * 1.35  # Total máximo = subtotal + 27% IVA + 8% percepciones
            
            if not (expected_min <= total_declared <= expected_max):
                problems.append(
                    f"Total (${total_declared:,.2f}) fuera de rango esperado (${expected_min:,.2f} - ${expected_max:,.2f})"
                )
        
        needs_reanalysis = len(problems) > 0
        
        if needs_reanalysis:
            logger.warning(f"⚠️ Se detectaron {len(problems)} problemas que requieren re-análisis:")
            for p in problems:
                logger.warning(f"   • {p}")
        
        return needs_reanalysis, problems
    
    @staticmethod
    def identify_problem_areas(problems: List[str]) -> List[str]:
        """
        Identifica qué áreas de la factura necesitan re-análisis.
        
        Returns:
            Lista de áreas: 'items', 'totales', 'header'
        """
        areas = set()
        
        for problem in problems:
            problem_lower = problem.lower()
            if 'item' in problem_lower or 'subtotal' in problem_lower or 'cantidad' in problem_lower:
                areas.add('items')
            if 'total' in problem_lower or 'iva' in problem_lower:
                areas.add('totales')
            if 'cuit' in problem_lower or 'empresa' in problem_lower:
                areas.add('header')
        
        return list(areas) if areas else ['items']  # Default: re-analizar items

