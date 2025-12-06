"""
🔐 Autenticación de Google Gemini

Módulo centralizado para inicializar el cliente de Google GenAI.
Soporta múltiples métodos de autenticación:
1. API Key (GOOGLE_API_KEY o GOOGLE_AI_API_KEY)
2. Service Account JSON (GOOGLE_SERVICE_ACCOUNT_JSON)
3. Application Default Credentials (ADC)

Uso:
    from invoice_extractor.utils.gemini_auth import get_gemini_client
    
    client, auth_method = get_gemini_client()
"""

import os
import logging
import tempfile
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


def get_gemini_client(api_key: Optional[str] = None) -> Tuple['genai.Client', str]:
    """
    Obtiene un cliente de Google GenAI autenticado.
    
    Intenta autenticar en el siguiente orden:
    1. API Key proporcionada como argumento
    2. API Key desde GOOGLE_API_KEY o GOOGLE_AI_API_KEY
    3. Service Account desde GOOGLE_SERVICE_ACCOUNT_JSON
    4. Application Default Credentials (ADC)
    
    Args:
        api_key: API Key opcional (si no se provee, busca en env)
    
    Returns:
        Tuple de (client, auth_method) donde auth_method es uno de:
        - "api_key"
        - "service_account_json"
        - "adc" (Application Default Credentials)
    
    Raises:
        ImportError: Si google-genai no está instalado
        Exception: Si no se puede autenticar con ningún método
    
    Example:
        >>> client, method = get_gemini_client()
        >>> print(f"Autenticado con: {method}")
        >>> response = client.models.generate_content(
        ...     model="gemini-2.5-flash",
        ...     contents=["Hello!"]
        ... )
    """
    try:
        from google import genai
    except ImportError:
        raise ImportError(
            "google-genai no está instalado. "
            "Instálalo con: pip install google-genai"
        )
    
    # Opción 1: API Key proporcionada o desde variable de entorno
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")
    
    if api_key:
        logger.info(f"🔐 Usando Google API Key: {api_key[:10]}...")
        client = genai.Client(api_key=api_key)
        logger.info("✅ GenAI Client inicializado con API Key")
        return client, "api_key"
    
    # Opción 2: Service Account desde JSON string (Railway/production)
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        logger.info("🔐 Usando Service Account desde variable de entorno JSON")
        
        # Crear archivo temporal con las credenciales
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write(service_account_json)
            temp_path = temp_file.name
        
        # Configurar GOOGLE_APPLICATION_CREDENTIALS temporalmente
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_path
        client = genai.Client()
        logger.info("✅ GenAI Client inicializado con Service Account (JSON env var)")
        return client, "service_account_json"
    
    # Opción 3: Application Default Credentials (archivo o ADC)
    logger.info("🔐 Intentando Application Default Credentials...")
    
    try:
        client = genai.Client()
        logger.info("✅ GenAI Client inicializado con ADC")
        return client, "adc"
    except Exception as e:
        logger.error(f"❌ Error inicializando GenAI Client: {e}")
        logger.error("💡 Configura una de las siguientes variables de entorno:")
        logger.error("   - GOOGLE_API_KEY: API Key de Google AI")
        logger.error("   - GOOGLE_SERVICE_ACCOUNT_JSON: JSON de Service Account")
        raise


class GeminiClientManager:
    """
    Manager singleton para el cliente de Gemini.
    
    Mantiene una única instancia del cliente para evitar
    re-autenticaciones innecesarias.
    
    Uso:
        from invoice_extractor.utils.gemini_auth import GeminiClientManager
        
        manager = GeminiClientManager()
        client = manager.get_client()
    """
    
    _instance = None
    _client = None
    _auth_method = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_client(self, api_key: Optional[str] = None) -> 'genai.Client':
        """
        Obtiene el cliente de Gemini, creándolo si no existe.
        
        Args:
            api_key: API Key opcional (solo se usa si el cliente no existe)
        
        Returns:
            Cliente de Google GenAI
        """
        if self._client is None:
            self._client, self._auth_method = get_gemini_client(api_key)
        return self._client
    
    @property
    def auth_method(self) -> Optional[str]:
        """Método de autenticación usado"""
        return self._auth_method
    
    def reset(self):
        """Resetea el cliente (útil para tests)"""
        self._client = None
        self._auth_method = None


# Instancia global del manager
_client_manager = GeminiClientManager()


def get_client(api_key: Optional[str] = None) -> 'genai.Client':
    """
    Función de conveniencia para obtener el cliente de Gemini.
    
    Usa el singleton GeminiClientManager internamente.
    
    Args:
        api_key: API Key opcional
    
    Returns:
        Cliente de Google GenAI
    """
    return _client_manager.get_client(api_key)

