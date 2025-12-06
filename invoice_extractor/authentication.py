# invoice_extractor/authentication.py
"""
🔐 API Key Authentication System

Sistema de autenticación por API Key para proteger los endpoints.

Uso:
    1. Configurar API_KEYS en variables de entorno:
       API_KEYS=key1,key2,key3
    
    2. El cliente debe enviar el header:
       Authorization: Bearer <api_key>
       o
       X-API-Key: <api_key>

    3. Los endpoints protegidos verifican automáticamente la key.
"""

import os
import logging
from typing import Optional, Tuple
from functools import wraps

from rest_framework import authentication, exceptions, permissions
from rest_framework.request import Request
from django.conf import settings

logger = logging.getLogger(__name__)


def get_valid_api_keys() -> set:
    """
    Obtiene las API keys válidas desde variables de entorno.
    
    Formato en .env:
        API_KEYS=key1,key2,key3
        o
        API_KEY=una-sola-key
    
    Returns:
        Set de API keys válidas
    """
    # Soporta tanto API_KEYS (múltiples) como API_KEY (una sola)
    api_keys_str = os.getenv('API_KEYS', '') or os.getenv('API_KEY', '')
    
    if not api_keys_str:
        logger.warning("⚠️ API_KEYS no configuradas - endpoints no protegidos!")
        return set()
    
    # Parsear keys separadas por coma, eliminar espacios
    keys = {k.strip() for k in api_keys_str.split(',') if k.strip()}
    
    if keys:
        logger.info(f"✅ {len(keys)} API key(s) configuradas")
    
    return keys


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Autenticación por API Key.
    
    Acepta la key en:
    - Header: Authorization: Bearer <key>
    - Header: X-API-Key: <key>
    """
    
    keyword = 'Bearer'
    
    def authenticate(self, request: Request) -> Optional[Tuple]:
        """
        Autentica la request usando API Key.
        
        Returns:
            Tuple de (None, api_key) si es válida
            None si no hay header de auth (permite que otras auth lo manejen)
        
        Raises:
            AuthenticationFailed si la key es inválida
        """
        api_key = self._get_api_key(request)
        
        if not api_key:
            return None  # No auth header, dejar que otro maneje
        
        valid_keys = get_valid_api_keys()
        
        # Si no hay keys configuradas, permitir todo (dev mode)
        if not valid_keys:
            logger.warning("🔓 No API keys configuradas - permitiendo acceso")
            return (None, api_key)
        
        if api_key not in valid_keys:
            logger.warning(f"❌ API Key inválida: {api_key[:8]}...")
            raise exceptions.AuthenticationFailed('API Key inválida')
        
        logger.info(f"✅ Autenticado con API Key: {api_key[:8]}...")
        return (None, api_key)
    
    def _get_api_key(self, request: Request) -> Optional[str]:
        """Extrae la API key del request."""
        
        # Opción 1: Header Authorization: Bearer <key>
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                return parts[1]
        
        # Opción 2: Header X-API-Key: <key>
        api_key_header = request.META.get('HTTP_X_API_KEY', '')
        if api_key_header:
            return api_key_header
        
        return None
    
    def authenticate_header(self, request: Request) -> str:
        """Header a incluir en respuesta 401."""
        return 'Bearer realm="api"'


class HasValidAPIKey(permissions.BasePermission):
    """
    Permission que requiere una API Key válida.
    
    Uso en ViewSet:
        permission_classes = [HasValidAPIKey]
    """
    
    message = 'API Key requerida. Usa header: Authorization: Bearer <key>'
    
    def has_permission(self, request: Request, view) -> bool:
        """Verifica si el request tiene API Key válida."""
        
        valid_keys = get_valid_api_keys()
        
        # Si no hay keys configuradas, permitir (dev mode)
        if not valid_keys:
            return True
        
        # Extraer key del request
        api_key = self._get_api_key(request)
        
        if not api_key:
            return False
        
        return api_key in valid_keys
    
    def _get_api_key(self, request: Request) -> Optional[str]:
        """Extrae la API key del request."""
        
        # Opción 1: Authorization: Bearer <key>
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                return parts[1]
        
        # Opción 2: X-API-Key: <key>
        api_key_header = request.META.get('HTTP_X_API_KEY', '')
        if api_key_header:
            return api_key_header
        
        return None


class OptionalAPIKeyPermission(permissions.BasePermission):
    """
    Permission que permite acceso sin key en desarrollo,
    pero requiere key en producción.
    """
    
    def has_permission(self, request: Request, view) -> bool:
        # En DEBUG mode, permitir sin key
        if settings.DEBUG:
            return True
        
        # En producción, requerir key
        return HasValidAPIKey().has_permission(request, view)


# =============================================================================
# DECORADORES PARA VIEWS FUNCIONALES
# =============================================================================

def require_api_key(view_func):
    """
    Decorador para proteger views funcionales con API Key.
    
    Uso:
        @require_api_key
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        valid_keys = get_valid_api_keys()
        
        # Si no hay keys configuradas, permitir
        if not valid_keys:
            return view_func(request, *args, **kwargs)
        
        # Extraer key
        api_key = None
        
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                api_key = parts[1]
        
        if not api_key:
            api_key = request.META.get('HTTP_X_API_KEY', '')
        
        if not api_key or api_key not in valid_keys:
            from rest_framework.response import Response
            return Response(
                {'error': 'API Key requerida', 'hint': 'Usa header: Authorization: Bearer <key>'},
                status=401
            )
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

