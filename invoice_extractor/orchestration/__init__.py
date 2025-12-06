# invoice_extractor/orchestration/__init__.py
"""
🎯 Orchestration - Coordinación inteligente de extractores

Este paquete contiene el orchestrator que coordina
la extracción de facturas usando Gemini con estrategias inteligentes.

Uso:
    from invoice_extractor.orchestration import IntelligentExtractionOrchestrator
    
    orchestrator = IntelligentExtractionOrchestrator(gemini_extractor)
    result = orchestrator.extract_with_strategy(file_path)
"""

from .intelligent_orchestrator import IntelligentExtractionOrchestrator

__all__ = [
    'IntelligentExtractionOrchestrator',
]
