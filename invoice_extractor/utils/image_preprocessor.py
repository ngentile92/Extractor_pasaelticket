# invoice_extractor/utils/image_preprocessor.py
"""
🖼️ Preprocesador de Imágenes para Facturas Argentinas

Este módulo mejora la calidad de imágenes de facturas antes de la extracción OCR,
optimizando para:
- Facturas con baja iluminación
- Imágenes borrosas o con ruido
- Perspectiva inclinada
- Bajo contraste
- Artefactos de compresión JPEG

Estrategias aplicadas:
1. Corrección de perspectiva (si está inclinada)
2. Mejora de contraste (CLAHE)
3. Reducción de ruido
4. Binarización adaptativa (threshold inteligente)
5. Mejora de bordes (sharpening)
6. Normalización de iluminación

Referencia: Best practices OCR from Google, Tesseract documentation
"""

import os
import logging
from typing import Optional, Tuple
from pathlib import Path
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Preprocesador de imágenes para mejorar la calidad antes de OCR/extracción.
    
    Usa OpenCV (si está disponible) para procesamiento avanzado,
    o PIL como fallback para procesamiento básico.
    """
    
    def __init__(
        self,
        enable_perspective_correction: bool = True,
        enable_contrast_enhancement: bool = True,
        enable_noise_reduction: bool = True,
        enable_sharpening: bool = True,
        enable_binarization: bool = False,  # False por defecto, puede reducir color
        output_dpi: int = 300  # DPI objetivo para OCR óptimo
    ):
        """
        Args:
            enable_perspective_correction: Corregir perspectiva si está inclinada
            enable_contrast_enhancement: Mejorar contraste (CLAHE)
            enable_noise_reduction: Reducir ruido (filtro bilateral)
            enable_sharpening: Mejorar nitidez de bordes
            enable_binarization: Convertir a blanco/negro (solo si es necesario)
            output_dpi: DPI objetivo (300 es óptimo para OCR)
        """
        self.enable_perspective_correction = enable_perspective_correction
        self.enable_contrast_enhancement = enable_contrast_enhancement
        self.enable_noise_reduction = enable_noise_reduction
        self.enable_sharpening = enable_sharpening
        self.enable_binarization = enable_binarization
        self.output_dpi = output_dpi
        
        if not CV2_AVAILABLE and not PIL_AVAILABLE:
            logger.warning("⚠️ Ni OpenCV ni PIL están disponibles. Preprocesamiento deshabilitado.")
    
    def preprocess(self, input_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Preprocesar imagen para mejorar calidad antes de extracción.
        
        Args:
            input_path: Ruta a la imagen original
            output_path: Ruta donde guardar imagen procesada (opcional)
                        Si no se provee, se guarda como {original}_preprocessed.{ext}
        
        Returns:
            Ruta a la imagen procesada, o None si falla
        """
        try:
            # Generar output_path si no se provee
            if output_path is None:
                input_path_obj = Path(input_path)
                output_path = str(
                    input_path_obj.parent / f"{input_path_obj.stem}_preprocessed{input_path_obj.suffix}"
                )
            
            # Procesar con OpenCV (preferido) o PIL (fallback)
            if CV2_AVAILABLE:
                return self._preprocess_opencv(input_path, output_path)
            elif PIL_AVAILABLE:
                return self._preprocess_pil(input_path, output_path)
            else:
                logger.warning("⚠️ No hay librerías de procesamiento de imágenes disponibles")
                return input_path  # Devolver original sin procesar
        
        except Exception as e:
            logger.error(f"❌ Error preprocesando imagen: {e}")
            return input_path  # Devolver original si falla
    
    def _preprocess_opencv(self, input_path: str, output_path: str) -> str:
        """
        Preprocesamiento avanzado con OpenCV.
        """
        logger.info(f"🖼️ Preprocesando con OpenCV: {Path(input_path).name}")
        
        # 1. Leer imagen
        img = cv2.imread(input_path)
        if img is None:
            logger.error(f"❌ No se pudo leer imagen: {input_path}")
            return input_path
        
        original_shape = img.shape
        logger.info(f"   Resolución original: {original_shape[1]}x{original_shape[0]}")
        
        # 2. CORRECCIÓN DE PERSPECTIVA (si está habilitada)
        if self.enable_perspective_correction:
            img = self._correct_perspective_opencv(img)
        
        # 3. MEJORA DE CONTRASTE (CLAHE - Contrast Limited Adaptive Histogram Equalization)
        if self.enable_contrast_enhancement:
            img = self._enhance_contrast_opencv(img)
        
        # 4. REDUCCIÓN DE RUIDO (Filtro bilateral)
        if self.enable_noise_reduction:
            img = self._reduce_noise_opencv(img)
        
        # 5. MEJORA DE NITIDEZ (Sharpening)
        if self.enable_sharpening:
            img = self._sharpen_opencv(img)
        
        # 6. BINARIZACIÓN (opcional, solo si está habilitada)
        if self.enable_binarization:
            img = self._binarize_opencv(img)
        
        # 7. Guardar imagen procesada
        success = cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        if success:
            logger.info(f"   ✅ Imagen preprocesada guardada: {Path(output_path).name}")
            return output_path
        else:
            logger.error(f"   ❌ Error guardando imagen procesada")
            return input_path
    
    def _correct_perspective_opencv(self, img: np.ndarray) -> np.ndarray:
        """
        Corregir perspectiva si la imagen está inclinada.
        
        Detecta los bordes del documento y aplica transformación de perspectiva
        para "enderezar" la imagen.
        """
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            
            # Encontrar contornos
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return img
            
            # Encontrar el contorno más grande (probablemente el documento)
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Aproximar a un polígono
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # Si es un cuadrilátero, aplicar transformación de perspectiva
            if len(approx) == 4:
                logger.info("   🔧 Corrigiendo perspectiva...")
                
                # Ordenar puntos: [top-left, top-right, bottom-right, bottom-left]
                pts = approx.reshape(4, 2)
                rect = self._order_points(pts)
                
                # Calcular dimensiones del documento "enderezado"
                width_a = np.linalg.norm(rect[0] - rect[1])
                width_b = np.linalg.norm(rect[2] - rect[3])
                height_a = np.linalg.norm(rect[0] - rect[3])
                height_b = np.linalg.norm(rect[1] - rect[2])
                
                max_width = max(int(width_a), int(width_b))
                max_height = max(int(height_a), int(height_b))
                
                # Puntos de destino
                dst = np.array([
                    [0, 0],
                    [max_width - 1, 0],
                    [max_width - 1, max_height - 1],
                    [0, max_height - 1]
                ], dtype="float32")
                
                # Calcular matriz de transformación
                M = cv2.getPerspectiveTransform(rect, dst)
                
                # Aplicar transformación
                warped = cv2.warpPerspective(img, M, (max_width, max_height))
                return warped
            
            return img
        
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudo corregir perspectiva: {e}")
            return img
    
    def _order_points(self, pts: np.ndarray) -> np.ndarray:
        """Ordenar puntos en sentido horario: [top-left, top-right, bottom-right, bottom-left]"""
        rect = np.zeros((4, 2), dtype="float32")
        
        # Top-left: menor suma de coordenadas
        # Bottom-right: mayor suma
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        
        # Top-right: menor diferencia
        # Bottom-left: mayor diferencia
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        return rect
    
    def _enhance_contrast_opencv(self, img: np.ndarray) -> np.ndarray:
        """
        Mejorar contraste usando CLAHE (Contrast Limited Adaptive Histogram Equalization).
        
        CLAHE es mejor que ecualización de histograma normal porque:
        - Trabaja en pequeñas regiones (tiles) en lugar de globalmente
        - Limita la amplificación de contraste para evitar ruido
        - Preserva mejor los detalles
        """
        try:
            logger.info("   🔧 Mejorando contraste (CLAHE)...")
            
            # Convertir a LAB (mejor para manipular luminosidad)
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Aplicar CLAHE al canal de luminosidad
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Fusionar canales y convertir de vuelta a BGR
            lab = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            
            return enhanced
        
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudo mejorar contraste: {e}")
            return img
    
    def _reduce_noise_opencv(self, img: np.ndarray) -> np.ndarray:
        """
        Reducir ruido usando filtro bilateral.
        
        El filtro bilateral es ideal para facturas porque:
        - Suaviza áreas uniformes (reduce ruido)
        - Preserva bordes (mantiene texto nítido)
        """
        try:
            logger.info("   🔧 Reduciendo ruido (filtro bilateral)...")
            denoised = cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)
            return denoised
        
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudo reducir ruido: {e}")
            return img
    
    def _sharpen_opencv(self, img: np.ndarray) -> np.ndarray:
        """
        Mejorar nitidez para hacer el texto más legible.
        """
        try:
            logger.info("   🔧 Mejorando nitidez...")
            
            # Kernel para sharpening
            kernel = np.array([
                [-1, -1, -1],
                [-1,  9, -1],
                [-1, -1, -1]
            ])
            
            sharpened = cv2.filter2D(img, -1, kernel)
            return sharpened
        
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudo mejorar nitidez: {e}")
            return img
    
    def _binarize_opencv(self, img: np.ndarray) -> np.ndarray:
        """
        Convertir a blanco y negro con threshold adaptativo.
        
        ⚠️ USAR CON CUIDADO: Elimina información de color que puede ser útil.
        Solo usar si la imagen tiene muy bajo contraste y OCR falla.
        """
        try:
            logger.info("   🔧 Binarizando imagen...")
            
            # Convertir a escala de grises
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Threshold adaptativo (mejor que threshold fijo)
            binary = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11,
                C=2
            )
            
            # Convertir de vuelta a BGR para compatibilidad
            binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
            return binary_bgr
        
        except Exception as e:
            logger.warning(f"   ⚠️ No se pudo binarizar: {e}")
            return img
    
    def _preprocess_pil(self, input_path: str, output_path: str) -> str:
        """
        Preprocesamiento básico con PIL (fallback si OpenCV no está disponible).
        """
        logger.info(f"🖼️ Preprocesando con PIL: {Path(input_path).name}")
        
        try:
            # 1. Abrir imagen
            img = Image.open(input_path)
            
            # 2. Mejorar contraste
            if self.enable_contrast_enhancement:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.5)  # 1.5x contraste
                logger.info("   🔧 Contraste mejorado")
            
            # 3. Mejorar nitidez
            if self.enable_sharpening:
                img = img.filter(ImageFilter.SHARPEN)
                logger.info("   🔧 Nitidez mejorada")
            
            # 4. Reducir ruido (suavizado ligero)
            if self.enable_noise_reduction:
                img = img.filter(ImageFilter.MedianFilter(size=3))
                logger.info("   🔧 Ruido reducido")
            
            # 5. Guardar
            img.save(output_path, quality=95)
            logger.info(f"   ✅ Imagen preprocesada guardada: {Path(output_path).name}")
            
            return output_path
        
        except Exception as e:
            logger.error(f"   ❌ Error con PIL: {e}")
            return input_path


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def preprocess_invoice_image(
    input_path: str,
    output_path: Optional[str] = None,
    **kwargs
) -> Optional[str]:
    """
    Función de conveniencia para preprocesar una imagen de factura.
    
    Args:
        input_path: Ruta a la imagen original
        output_path: Ruta donde guardar (opcional)
        **kwargs: Parámetros para ImagePreprocessor
    
    Returns:
        Ruta a la imagen procesada
    
    Example:
        >>> processed_path = preprocess_invoice_image("factura.jpg")
        >>> # Usar processed_path para extracción
    """
    preprocessor = ImagePreprocessor(**kwargs)
    return preprocessor.preprocess(input_path, output_path)


def should_preprocess(file_path: str) -> bool:
    """
    Determinar si una imagen necesita preprocesamiento basándose en heurísticas.
    
    Args:
        file_path: Ruta al archivo
    
    Returns:
        True si se recomienda preprocesar
    """
    # Por ahora, siempre preprocesar (podríamos agregar lógica inteligente)
    # Futura mejora: analizar calidad de imagen y decidir
    return True

