"""
Enums para el dominio de la aplicación
"""

from enum import Enum


class JobStatus(Enum):
    """Estados posibles de un job"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DONE = "done"  # Agregado para compatibilidad con call_worker
    FAILED = "failed"
    SUSPENDED = "suspended"  # Nuevo: Para jobs sin créditos


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


class AccountStatus(Enum):
    """Estados de cuenta"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    PENDING_ACTIVATION = "pending_activation"


class PlanType(Enum):
    """Tipos de planes de facturación"""
    MINUTES_BASED = "minutes_based"    # Por minutos comprados
    CREDIT_BASED = "credit_based"      # Por créditos en dinero
    UNLIMITED = "unlimited"            # Sin límites


class TransactionType(Enum):
    """Tipos de transacciones financieras"""
    TOPUP_CREDITS = "topup_credits"         # Recarga de créditos
    TOPUP_MINUTES = "topup_minutes"         # Recarga de minutos
    CALL_USAGE = "call_usage"               # Uso en llamadas
    CALL_SETUP = "call_setup"               # Costo setup de llamada
    BONUS = "bonus"                         # Bonos promocionales
    REFUND = "refund"                       # Reembolsos
    PENALTY = "penalty"                     # Penalizaciones
    PLAN_UPGRADE = "plan_upgrade"           # Upgrade de plan
    PLAN_RENEWAL = "plan_renewal"           # Renovación de plan


class UseCaseType(Enum):
    """Tipos de casos de uso soportados"""
    DEBT_COLLECTION = "debt_collection"
    MARKETING = "marketing"
    SURVEY = "survey"
    REMINDER = "reminder"
    NOTIFICATION = "notification"

