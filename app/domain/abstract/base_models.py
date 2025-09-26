"""
Modelos base abstractos para diferentes casos de uso
Permite crear sistemas genéricos y extensibles
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Type
from bson import ObjectId
import uuid

from ..enums import JobStatus


@dataclass
class BaseJobPayload(ABC):
    """
    Clase base para todos los payloads de trabajos
    Define la interfaz común que deben implementar todos los casos de uso
    """
    
    @abstractmethod
    def to_retell_context(self) -> Dict[str, str]:
        """Convierte el payload a contexto para Retell (todo strings)"""
        pass
    
    @abstractmethod
    def get_script_template_id(self) -> str:
        """Retorna el ID del template de script para este caso de uso"""
        pass
    
    @abstractmethod
    def validate(self) -> List[str]:
        """Valida el payload y retorna lista de errores. Lista vacía = válido"""
        pass
    
    @abstractmethod
    def get_summary(self) -> str:
        """Retorna resumen del payload para logging/display"""
        pass


@dataclass
class BaseContactInfo(ABC):
    """
    Información de contacto base (genérica para cualquier caso de uso)
    """
    name: str
    identifier: str  # Puede ser DNI, RUT, email, user_id, etc.
    phones: List[str]
    next_phone_index: int = 0
    additional_contact_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def current_phone(self) -> Optional[str]:
        """Obtiene el teléfono actual a usar"""
        if 0 <= self.next_phone_index < len(self.phones):
            return self.phones[self.next_phone_index]
        return None
    
    def advance_to_next_phone(self) -> bool:
        """Avanza al siguiente teléfono. Retorna True si hay más teléfonos"""
        self.next_phone_index += 1
        return self.next_phone_index < len(self.phones)


@dataclass
class BaseJobModel(ABC):
    """
    Modelo base para todos los tipos de trabajos/jobs
    Define estructura común independientemente del caso de uso
    """
    _id: str
    account_id: str
    batch_id: str
    use_case: str  # 'debt_collection', 'user_experience', 'survey', etc.
    status: JobStatus
    contact: BaseContactInfo
    payload: BaseJobPayload
    
    # Metadatos comunes
    created_at: datetime
    updated_at: datetime
    tries: int = 0
    max_tries: int = 3
    
    # Campos de procesamiento
    worker_id: Optional[str] = None
    reserved_until: Optional[datetime] = None
    last_error: Optional[str] = None
    call_result: Optional[Dict[str, Any]] = None
    
    # Campos específicos del lease system
    lease_expires: Optional[datetime] = None
    
    def __post_init__(self):
        if not self._id:
            self._id = str(uuid.uuid4())
    
    @abstractmethod
    def get_processor_class(self) -> str:
        """Retorna el nombre de la clase procesadora para este tipo de job"""
        pass
    
    def to_mongo_dict(self) -> Dict[str, Any]:
        """Convierte el job a diccionario para almacenar en MongoDB"""
        return {
            "_id": self._id,
            "account_id": self.account_id,
            "batch_id": self.batch_id,
            "use_case": self.use_case,
            "status": self.status.value,
            "contact": {
                "name": self.contact.name,
                "identifier": self.contact.identifier,
                "phones": self.contact.phones,
                "next_phone_index": self.contact.next_phone_index,
                "additional_contact_data": self.contact.additional_contact_data
            },
            "payload": self.payload.__dict__,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tries": self.tries,
            "max_tries": self.max_tries,
            "worker_id": self.worker_id,
            "reserved_until": self.reserved_until,
            "last_error": self.last_error,
            "call_result": self.call_result,
            "lease_expires": self.lease_expires
        }


@dataclass
class BaseBatchModel(ABC):
    """
    Modelo base para batches de cualquier caso de uso
    """
    _id: str
    account_id: str
    use_case: str
    name: str
    description: str
    
    # Configuración específica del caso de uso
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Estadísticas
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Estado
    status: str = "created"  # created, processing, completed, failed
    
    def __post_init__(self):
        if not self._id:
            self._id = str(uuid.uuid4())
    
    @property
    def success_rate(self) -> float:
        """Calcula tasa de éxito del batch"""
        if self.total_jobs == 0:
            return 0.0
        return (self.completed_jobs / self.total_jobs) * 100
    
    @abstractmethod
    def get_job_factory(self) -> 'BaseJobFactory':
        """Retorna la factory para crear jobs de este batch"""
        pass


class BaseJobFactory(ABC):
    """
    Factory base para crear jobs según el caso de uso
    """
    
    @abstractmethod
    def create_job_from_data(self, row_data: Dict[str, Any], batch_id: str, account_id: str) -> BaseJobModel:
        """Crea un job a partir de datos raw (Excel, CSV, API, etc.)"""
        pass
    
    @abstractmethod
    def get_required_columns(self) -> List[str]:
        """Retorna las columnas requeridas para este tipo de job"""
        pass
    
    @abstractmethod
    def validate_row_data(self, row_data: Dict[str, Any]) -> List[str]:
        """Valida una fila de datos y retorna errores encontrados"""
        pass


class BaseJobProcessor(ABC):
    """
    Procesador base para diferentes tipos de jobs
    """
    
    @abstractmethod
    def process_job(self, job: BaseJobModel) -> Dict[str, Any]:
        """Procesa un job específico y retorna el resultado"""
        pass
    
    @abstractmethod
    def can_process(self, job: BaseJobModel) -> bool:
        """Determina si este procesador puede manejar el job dado"""
        pass
    
    @abstractmethod
    def get_supported_use_cases(self) -> List[str]:
        """Retorna lista de casos de uso soportados"""
        pass