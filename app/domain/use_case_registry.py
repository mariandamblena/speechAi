"""
Registry simplificado para casos de uso
Maneja la creación y obtención de procesadores específicos
"""

from typing import Dict, List, Optional, Any
from .use_cases.debt_collection_processor import DebtCollectionProcessor
from .use_cases.marketing_processor import MarketingProcessor


class UseCaseRegistry:
    """
    Registry simple que conoce todos los procesadores de casos de uso
    Mucho más simple que la versión anterior - solo procesadores, no factories ni jobs abstractos
    """
    
    def __init__(self):
        self._processors = {
            'debt_collection': DebtCollectionProcessor(),
            'marketing': MarketingProcessor(),
        }
    
    def get_processor(self, use_case: str):
        """Obtiene el procesador para un caso de uso específico"""
        if use_case not in self._processors:
            raise ValueError(f"Caso de uso '{use_case}' no soportado. Disponibles: {self.get_available_use_cases()}")
        return self._processors[use_case]
    
    def get_available_use_cases(self) -> List[str]:
        """Lista todos los casos de uso disponibles"""
        return list(self._processors.keys())
    
    def register_processor(self, use_case: str, processor):
        """Registra un nuevo procesador (para extensión futura)"""
        self._processors[use_case] = processor
    
    def validate_use_case_config(self, use_case: str, config: Dict[str, Any]) -> List[str]:
        """Valida la configuración para un caso de uso específico"""
        processor = self.get_processor(use_case)
        return processor.validate_config(config)


# Instancia global del registry (singleton)
_global_registry = None

def get_use_case_registry() -> UseCaseRegistry:
    """Obtiene la instancia global del registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = UseCaseRegistry()
    return _global_registry