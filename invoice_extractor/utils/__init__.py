# invoice_extractor/utils/__init__.py
"""
📦 Utilidades para el extractor de facturas

Este paquete contiene utilidades compartidas:
- retry: Retry con exponential backoff para APIs
- gemini_auth: Autenticación centralizada de Google Gemini
- image_preprocessor: Preprocesamiento de imágenes para OCR
- normalization: Normalización de datos extraídos
- corrections: Correcciones automáticas de datos
- post_processor: Pipeline de post-procesamiento
- fiscal_logic_inferencer: Inferencia de lógica contable

Uso:
    from invoice_extractor.utils import (
        retry_with_exponential_backoff,
        get_gemini_client,
        preprocess_invoice_image,
        normalize_all,
        apply_all_corrections,
        process_invoice,
    )
"""

# Retry con exponential backoff
from .retry import retry_with_exponential_backoff

# Autenticación de Gemini
from .gemini_auth import (
    get_gemini_client,
    get_client,
    GeminiClientManager,
)

# Preprocesamiento de imágenes
from .image_preprocessor import (
    ImagePreprocessor,
    preprocess_invoice_image,
    should_preprocess,
)

# Normalización de datos
from .normalization import normalize_all

# Correcciones automáticas
from .corrections import apply_all_corrections

# Post-procesamiento (pipeline completo)
from .post_processor import (
    InvoicePostProcessor,
    process_invoice,
    get_validation_score,
    get_validation_errors,
    transform_to_legacy_format,
    BatchPostProcessor,
)

# Inferencia de lógica fiscal (opcional)
try:
    from .fiscal_logic_inferencer import FiscalLogicInferencer
except ImportError:
    FiscalLogicInferencer = None


__all__ = [
    # Retry
    'retry_with_exponential_backoff',
    
    # Gemini Auth
    'get_gemini_client',
    'get_client',
    'GeminiClientManager',
    
    # Image preprocessing
    'ImagePreprocessor',
    'preprocess_invoice_image',
    'should_preprocess',
    
    # Normalization
    'normalize_all',
    
    # Corrections
    'apply_all_corrections',
    
    # Post-processing
    'InvoicePostProcessor',
    'process_invoice',
    'get_validation_score',
    'get_validation_errors',
    'transform_to_legacy_format',
    'BatchPostProcessor',
    
    # Fiscal inference (optional)
    'FiscalLogicInferencer',
]
