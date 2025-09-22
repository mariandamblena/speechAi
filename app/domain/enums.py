"""
Enums para el dominio de la aplicación
"""

from enum import Enum


class JobStatus(Enum):
    """Estados posibles de un job"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class CallStatus(Enum):
    """Estados posibles de una llamada en Retell"""
    REGISTERED = "registered"
    ONGOING = "ongoing"
    ENDED = "ended"
    ERROR = "error"
    TRANSFERRED = "transferred"
    
    @classmethod
    def is_final_status(cls, status: str) -> bool:
        """Verifica si un status indica que la llamada terminó"""
        return status in [cls.ENDED.value, cls.ERROR.value, cls.TRANSFERRED.value]


class CallMode(Enum):
    """Modos de operación para llamadas"""
    SINGLE = "single"          # Una sola llamada por job
    CONTINUOUS = "continuous"  # Múltiples intentos si falla