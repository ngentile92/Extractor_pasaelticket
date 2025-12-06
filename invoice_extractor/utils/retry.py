"""
🔄 Utilidad para Retry con Exponential Backoff

Función única y centralizada para manejar reintentos con backoff exponencial.
Útil para manejar errores 429 (RESOURCE_EXHAUSTED) de Google Gemini.

Uso:
    from invoice_extractor.utils.retry import retry_with_exponential_backoff
    
    result = retry_with_exponential_backoff(
        lambda: client.generate_content(...),
        max_retries=3
    )
"""

import time
import logging
from typing import Callable, TypeVar, Any

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_exponential_backoff(
    func: Callable[[], T],
    max_retries: int = 5,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = None
) -> T:
    """
    Ejecuta una función con retry automático usando exponential backoff.
    
    Útil para manejar errores 429 (RESOURCE_EXHAUSTED) de Google Gemini
    y otros errores transitorios de APIs.
    
    Args:
        func: Función a ejecutar (callable sin argumentos, usar lambda si es necesario)
        max_retries: Número máximo de reintentos (default: 5)
        initial_delay: Delay inicial en segundos (default: 1.0)
        exponential_base: Base para el cálculo exponencial (default: 2.0 = duplica cada vez)
        max_delay: Delay máximo en segundos (default: 60.0)
        retryable_exceptions: Tuple de excepciones a reintentar (default: None = auto-detectar 429)
    
    Returns:
        El resultado de la función si tiene éxito
    
    Raises:
        La última excepción si todos los reintentos fallan
    
    Example:
        >>> from google import genai
        >>> client = genai.Client(api_key="...")
        >>> 
        >>> result = retry_with_exponential_backoff(
        ...     lambda: client.models.generate_content(
        ...         model="gemini-2.5-flash",
        ...         contents=["Hello!"]
        ...     ),
        ...     max_retries=3,
        ...     initial_delay=2.0
        ... )
    """
    # Importar errores de Gemini solo si están disponibles
    try:
        from google.genai import errors as genai_errors
        GENAI_AVAILABLE = True
    except ImportError:
        GENAI_AVAILABLE = False
        genai_errors = None
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        
        except Exception as e:
            last_exception = e
            
            # Determinar si es un error recuperable (429)
            is_retryable = False
            
            # Caso 1: Es un ClientError de Gemini
            if GENAI_AVAILABLE and genai_errors and isinstance(e, genai_errors.ClientError):
                status_code = _extract_status_code(e)
                is_retryable = status_code == 429
            
            # Caso 2: El usuario especificó excepciones retryables
            elif retryable_exceptions and isinstance(e, retryable_exceptions):
                is_retryable = True
            
            # Caso 3: Buscar "429" en el mensaje de error
            elif "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                is_retryable = True
            
            # Si no es retryable, lanzar inmediatamente
            if not is_retryable:
                logger.error(f"❌ Error no recuperable: {e}")
                raise
            
            # Si ya agotamos los reintentos, lanzar la excepción
            if attempt == max_retries:
                logger.error(f"❌ Agotados {max_retries} reintentos para error 429")
                raise
            
            # Calcular delay con exponential backoff
            delay = min(initial_delay * (exponential_base ** attempt), max_delay)
            
            logger.warning(
                f"⚠️ Error 429 en intento {attempt + 1}/{max_retries + 1}. "
                f"Esperando {delay:.1f}s antes de reintentar..."
            )
            
            time.sleep(delay)
    
    # Si llegamos aquí, lanzar la última excepción
    if last_exception:
        raise last_exception


def _extract_status_code(exception: Exception) -> int:
    """
    Extrae el código de status de una excepción de Gemini.
    
    Args:
        exception: Excepción a analizar
    
    Returns:
        Código de status HTTP o 0 si no se puede determinar
    """
    # Intentar obtener de atributos directos
    status_code = getattr(exception, 'status_code', None) or getattr(exception, 'code', None)
    
    if status_code:
        return int(status_code)
    
    # Intentar extraer del string del error
    error_str = str(exception)
    if error_str.startswith('429'):
        return 429
    
    # Buscar patrón "HTTP 429" o similar
    import re
    match = re.search(r'(\d{3})\s*(RESOURCE_EXHAUSTED|Too Many Requests)', error_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    
    return 0

