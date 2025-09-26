"""
Sistema de registro y factory para diferentes casos de uso
Permite agregar nuevos tipos de jobs sin modificar código existente
"""

from typing import Dict, List, Type, Optional, Any
from abc import ABC

from .abstract.base_models import (
    BaseJobModel, BaseBatchModel, BaseJobFactory, BaseJobProcessor
)
from .abstract.use_case_enums import UseCaseType
from .use_cases.debt_collection import (
    DebtCollectionJob, DebtCollectionBatch, 
    DebtCollectionJobFactory, DebtCollectionProcessor
)
from .use_cases.user_experience import (
    UserExperienceJob, UserExperienceBatch,
    UserExperienceJobFactory, UserExperienceProcessor
)


class UseCaseRegistry:
    """
    Registry central para todos los casos de uso
    Permite registrar y obtener factories, processors, etc. dinámicamente
    """
    
    def __init__(self):
        self._job_classes: Dict[str, Type[BaseJobModel]] = {}
        self._batch_classes: Dict[str, Type[BaseBatchModel]] = {}
        self._job_factories: Dict[str, Type[BaseJobFactory]] = {}
        self._job_processors: Dict[str, Type[BaseJobProcessor]] = {}
        
        # Registrar casos de uso por defecto
        self._register_default_use_cases()
    
    def _register_default_use_cases(self):
        """Registra los casos de uso incluidos por defecto"""
        
        # Cobranza
        self.register_use_case(
            use_case=UseCaseType.DEBT_COLLECTION.value,
            job_class=DebtCollectionJob,
            batch_class=DebtCollectionBatch,
            job_factory_class=DebtCollectionJobFactory,
            job_processor_class=DebtCollectionProcessor
        )
        
        # User Experience
        self.register_use_case(
            use_case=UseCaseType.USER_EXPERIENCE.value,
            job_class=UserExperienceJob,
            batch_class=UserExperienceBatch,
            job_factory_class=UserExperienceJobFactory,
            job_processor_class=UserExperienceProcessor
        )
    
    def register_use_case(
        self,
        use_case: str,
        job_class: Type[BaseJobModel],
        batch_class: Type[BaseBatchModel],
        job_factory_class: Type[BaseJobFactory],
        job_processor_class: Type[BaseJobProcessor]
    ):
        """Registra un nuevo caso de uso en el sistema"""
        self._job_classes[use_case] = job_class
        self._batch_classes[use_case] = batch_class
        self._job_factories[use_case] = job_factory_class
        self._job_processors[use_case] = job_processor_class
    
    def get_job_class(self, use_case: str) -> Optional[Type[BaseJobModel]]:
        """Obtiene la clase de job para un caso de uso"""
        return self._job_classes.get(use_case)
    
    def get_batch_class(self, use_case: str) -> Optional[Type[BaseBatchModel]]:
        """Obtiene la clase de batch para un caso de uso"""
        return self._batch_classes.get(use_case)
    
    def get_job_factory(self, use_case: str) -> Optional[BaseJobFactory]:
        """Obtiene una instancia de factory para un caso de uso"""
        factory_class = self._job_factories.get(use_case)
        return factory_class() if factory_class else None
    
    def get_job_processor(self, use_case: str) -> Optional[BaseJobProcessor]:
        """Obtiene una instancia de processor para un caso de uso"""
        processor_class = self._job_processors.get(use_case)
        return processor_class() if processor_class else None
    
    def get_available_use_cases(self) -> List[str]:
        """Retorna lista de casos de uso disponibles"""
        return list(self._job_classes.keys())
    
    def get_required_columns_for_use_case(self, use_case: str) -> List[str]:
        """Obtiene las columnas requeridas para un caso de uso específico"""
        factory = self.get_job_factory(use_case)
        return factory.get_required_columns() if factory else []


class UniversalJobFactory:
    """
    Factory universal que puede crear jobs de cualquier tipo
    según el caso de uso especificado
    """
    
    def __init__(self, registry: Optional[UseCaseRegistry] = None):
        self.registry = registry or UseCaseRegistry()
    
    def create_job_from_data(
        self,
        use_case: str,
        row_data: Dict[str, Any],
        batch_id: str,
        account_id: str
    ) -> Optional[BaseJobModel]:
        """Crea un job del tipo especificado"""
        
        factory = self.registry.get_job_factory(use_case)
        if not factory:
            raise ValueError(f"Caso de uso no soportado: {use_case}")
        
        return factory.create_job_from_data(row_data, batch_id, account_id)
    
    def validate_data_for_use_case(
        self,
        use_case: str,
        row_data: Dict[str, Any]
    ) -> List[str]:
        """Valida datos para un caso de uso específico"""
        
        factory = self.registry.get_job_factory(use_case)
        if not factory:
            return [f"Caso de uso no soportado: {use_case}"]
        
        return factory.validate_row_data(row_data)
    
    def get_required_columns(self, use_case: str) -> List[str]:
        """Obtiene columnas requeridas para un caso de uso"""
        return self.registry.get_required_columns_for_use_case(use_case)


class UniversalJobProcessor:
    """
    Procesador universal que puede procesar jobs de cualquier tipo
    """
    
    def __init__(self, registry: Optional[UseCaseRegistry] = None):
        self.registry = registry or UseCaseRegistry()
    
    def process_job(self, job: BaseJobModel) -> Dict[str, Any]:
        """Procesa un job usando el processor apropiado"""
        
        processor = self.registry.get_job_processor(job.use_case)
        if not processor:
            raise ValueError(f"No hay processor para caso de uso: {job.use_case}")
        
        if not processor.can_process(job):
            raise ValueError(f"Processor no puede manejar este job: {job.use_case}")
        
        return processor.process_job(job)
    
    def can_process_use_case(self, use_case: str) -> bool:
        """Verifica si puede procesar un caso de uso"""
        processor = self.registry.get_job_processor(use_case)
        return processor is not None


# Instancia global del registry (singleton)
_global_registry = None

def get_use_case_registry() -> UseCaseRegistry:
    """Obtiene la instancia global del registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = UseCaseRegistry()
    return _global_registry


def get_universal_factory() -> UniversalJobFactory:
    """Obtiene factory universal con registry global"""
    return UniversalJobFactory(get_use_case_registry())


def get_universal_processor() -> UniversalJobProcessor:
    """Obtiene processor universal con registry global"""
    return UniversalJobProcessor(get_use_case_registry())