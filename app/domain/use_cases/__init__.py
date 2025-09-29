"""
Casos de uso del sistema - Lógica de negocio específica
Procesadores que convierten datos normalizados en jobs específicos por industria
"""

from .debt_collection_processor import DebtCollectionProcessor
from .marketing_processor import MarketingProcessor

__all__ = [
    'DebtCollectionProcessor',
    'MarketingProcessor'
]