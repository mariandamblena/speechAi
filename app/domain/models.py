"""
Modelos de dominio para la aplicación
Siguiendo principios de Domain-Driven Design (DDD)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId
import uuid

from .enums import JobStatus, CallStatus, CallMode, AccountStatus, PlanType


@dataclass
class ContactInfo:
    """Información de contacto para un deudor"""
    name: str
    dni: str
    phones: List[str]
    next_phone_index: int = 0
    
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
class CallPayload:
    """Datos específicos del contexto de la llamada de cobranza"""
    debt_amount: float
    due_date: str
    company_name: str = ""
    reference_number: str = ""
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_retell_context(self) -> Dict[str, str]:
        """Convierte el payload a contexto para Retell (todo strings)"""
        context = {
            "monto_total": str(self.debt_amount),
            "fecha_limite": self.due_date,
            "empresa": self.company_name,
            "referencia": self.reference_number,
        }
        
        # Agregar info adicional
        for key, value in self.additional_info.items():
            context[key] = str(value)
            
        return context


@dataclass
class JobModel:
    """Modelo principal de un job de llamada"""
    _id: Optional[ObjectId] = None
    job_id: Optional[str] = None  # ID único del job
    account_id: str = ""  # Vinculación con la cuenta
    batch_id: Optional[str] = None  # Opcional: agrupa jobs en lotes
    status: JobStatus = JobStatus.PENDING
    contact: Optional[ContactInfo] = None
    payload: Optional[CallPayload] = None
    mode: CallMode = CallMode.SINGLE
    
    # Campo anti-duplicación
    deduplication_key: Optional[str] = None  # Clave única para evitar duplicados
    
    # Campos de control
    attempts: int = 0
    max_attempts: int = 3
    reserved_until: Optional[datetime] = None
    worker_id: Optional[str] = None
    
    # Control de costos y límites
    estimated_cost: Optional[float] = None
    reserved_amount: Optional[float] = None  # Fondos reservados para esta llamada
    
    # Timestamps
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # Resultados
    call_id: Optional[str] = None
    call_result: Optional[Dict[str, Any]] = None
    last_error: Optional[str] = None
    
    def generate_deduplication_key(self) -> str:
        """Genera clave única para evitar duplicados"""
        if not self.contact:
            return f"job_{self.account_id}_{datetime.utcnow().isoformat()}"
        
        # Formato: account_id::rut::batch_id
        return f"{self.account_id}::{self.contact.dni}::{self.batch_id or 'single'}"
    
    def generate_job_id(self) -> str:
        """Genera un job_id único"""
        if not self.job_id:
            # Usar UUID para garantizar unicidad
            unique_id = str(uuid.uuid4())[:8]  # Primeros 8 caracteres del UUID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.job_id = f"job_{self.account_id[:8]}_{timestamp}_{unique_id}"
        return self.job_id
    
    def can_retry(self) -> bool:
        """Verifica si el job puede reintentarse"""
        return self.attempts < self.max_attempts
    
    def get_context_for_retell(self) -> Dict[str, str]:
        """Genera el contexto completo para Retell"""
        if not self.contact or not self.payload:
            return {}
            
        context = self.payload.to_retell_context()
        context.update({
            "nombre": self.contact.name,
            "rut": self.contact.dni,
        })
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el modelo a diccionario para MongoDB"""
        data = {}
        
        if self._id:
            data["_id"] = self._id
            
        data.update({
            "job_id": self.job_id or self.generate_job_id(),
            "account_id": self.account_id,
            "batch_id": self.batch_id,
            "status": self.status.value,
            "mode": self.mode.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "deduplication_key": self.deduplication_key or self.generate_deduplication_key(),
        })
        
        if self.contact:
            data["contact"] = {
                "name": self.contact.name,
                "dni": self.contact.dni,
                "phones": self.contact.phones,
                "next_phone_index": self.contact.next_phone_index,
            }
            
        if self.payload:
            data["payload"] = {
                "debt_amount": self.payload.debt_amount,
                "due_date": self.payload.due_date,
                "company_name": self.payload.company_name,
                "reference_number": self.payload.reference_number,
                "additional_info": self.payload.additional_info,
            }
        
        # Campos opcionales
        optional_fields = [
            "job_id", "reserved_until", "worker_id", "estimated_cost", "reserved_amount",
            "created_at", "started_at", "completed_at", "failed_at", "updated_at", 
            "call_id", "call_result", "last_error"
        ]
        
        for field_name in optional_fields:
            value = getattr(self, field_name)
            if value is not None:
                data[field_name] = value
                
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JobModel':
        """Crea un JobModel desde un diccionario de MongoDB"""
        contact = None
        if "contact" in data:
            contact_data = data["contact"]
            contact = ContactInfo(
                name=contact_data["name"],
                dni=contact_data["dni"],
                phones=contact_data["phones"],
                next_phone_index=contact_data.get("next_phone_index", 0)
            )
        
        payload = None
        if "payload" in data:
            payload_data = data["payload"]
            payload = CallPayload(
                debt_amount=payload_data["debt_amount"],
                due_date=payload_data["due_date"],
                company_name=payload_data.get("company_name", ""),
                reference_number=payload_data.get("reference_number", ""),
                additional_info=payload_data.get("additional_info", {})
            )
        
        return cls(
            _id=data.get("_id"),
            job_id=data.get("job_id"),
            account_id=data.get("account_id", ""),
            batch_id=data.get("batch_id"),
            status=JobStatus(data.get("status", "pending")),
            contact=contact,
            payload=payload,
            mode=CallMode(data.get("mode", "single")),
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 3),
            deduplication_key=data.get("deduplication_key"),
            reserved_until=data.get("reserved_until"),
            worker_id=data.get("worker_id"),
            estimated_cost=data.get("estimated_cost"),
            reserved_amount=data.get("reserved_amount"),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            failed_at=data.get("failed_at"),
            updated_at=data.get("updated_at"),
            call_id=data.get("call_id"),
            call_result=data.get("call_result"),
            last_error=data.get("last_error")
        )


@dataclass
class CallResult:
    """Resultado de una llamada completada"""
    call_id: str
    job_id: str
    contact: ContactInfo
    call_data: Dict[str, Any]
    created_at: datetime
    
    @property
    def call_status(self) -> str:
        """Status de la llamada desde los datos de Retell"""
        return self.call_data.get("call_status", "unknown")
    
    @property
    def duration_ms(self) -> int:
        """Duración en milisegundos"""
        return self.call_data.get("duration_ms", 0)
    
    @property
    def is_successful(self) -> bool:
        """Determina si la llamada fue exitosa"""
        return self.call_status == CallStatus.ENDED.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para MongoDB"""
        return {
            "call_id": self.call_id,
            "job_id": self.job_id,
            "contact": {
                "name": self.contact.name,
                "dni": self.contact.dni,
                "phone_used": self.contact.current_phone,
            },
            "call_data": self.call_data,
            "call_status": self.call_status,
            "duration_ms": self.duration_ms,
            "is_successful": self.is_successful,
            "created_at": self.created_at,
        }


@dataclass
class AccountModel:
    """Modelo para cuentas de usuario con sistema de créditos"""
    _id: Optional[ObjectId] = None
    account_id: str = ""
    account_name: str = ""
    plan_type: PlanType = PlanType.MINUTES_BASED
    status: AccountStatus = AccountStatus.PENDING_ACTIVATION
    
    # Balance para planes basados en minutos
    minutes_purchased: float = 0.0
    minutes_used: float = 0.0
    minutes_reserved: float = 0.0  # Minutos reservados para llamadas en progreso
    
    # Balance para planes basados en créditos
    credit_balance: float = 0.0
    credit_used: float = 0.0
    credit_reserved: float = 0.0  # Créditos reservados para llamadas en progreso
    
    # Configuración de precios
    cost_per_minute: float = 0.15  # USD por minuto
    cost_per_call_setup: float = 0.02  # USD por llamada iniciada
    cost_failed_call: float = 0.01  # USD por llamada fallida
    
    # Límites operacionales
    max_concurrent_calls: int = 3
    daily_call_limit: int = 1000
    calls_today: int = 0
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_topup_at: Optional[datetime] = None
    
    @property
    def minutes_remaining(self) -> float:
        """Minutos disponibles (sin reservas)"""
        return max(0, self.minutes_purchased - self.minutes_used - self.minutes_reserved)
    
    @property
    def credit_available(self) -> float:
        """Créditos disponibles (sin reservas)"""
        return max(0, self.credit_balance - self.credit_reserved)
    
    @property
    def has_sufficient_balance(self) -> bool:
        """Verifica si tiene saldo suficiente para llamadas"""
        if self.plan_type == PlanType.UNLIMITED:
            return True
        elif self.plan_type == PlanType.MINUTES_BASED:
            return self.minutes_remaining > 0
        else:  # CREDIT_BASED
            return self.credit_available >= self.cost_per_call_setup
    
    @property
    def can_make_calls(self) -> bool:
        """Verifica si puede hacer llamadas (saldo + límites + status)"""
        return (
            self.status == AccountStatus.ACTIVE and
            self.has_sufficient_balance and
            self.calls_today < self.daily_call_limit
        )
    
    def estimate_call_cost(self, estimated_minutes: float = 3.0) -> float:
        """Estima el costo de una llamada"""
        if self.plan_type == PlanType.MINUTES_BASED:
            return estimated_minutes  # En minutos
        else:  # CREDIT_BASED
            return self.cost_per_call_setup + (estimated_minutes * self.cost_per_minute)
    
    def reserve_funds(self, estimated_minutes: float = 3.0) -> bool:
        """Reserva fondos para una llamada. Retorna True si fue exitoso"""
        if not self.can_make_calls:
            return False
        
        if self.plan_type == PlanType.MINUTES_BASED:
            if self.minutes_remaining >= estimated_minutes:
                self.minutes_reserved += estimated_minutes
                return True
        else:  # CREDIT_BASED
            estimated_cost = self.estimate_call_cost(estimated_minutes)
            if self.credit_available >= estimated_cost:
                self.credit_reserved += estimated_cost
                return True
        
        return False
    
    def consume_funds(self, actual_minutes: float, actual_cost: float = None) -> None:
        """Consume fondos después de una llamada completada"""
        if self.plan_type == PlanType.MINUTES_BASED:
            # Liberar reserva y consumir minutos reales
            self.minutes_reserved = max(0, self.minutes_reserved - actual_minutes)
            self.minutes_used += actual_minutes
        else:  # CREDIT_BASED
            if actual_cost is None:
                actual_cost = self.cost_per_call_setup + (actual_minutes * self.cost_per_minute)
            
            # Liberar reserva y consumir costo real
            self.credit_reserved = max(0, self.credit_reserved - actual_cost)
            self.credit_used += actual_cost
        
        self.calls_today += 1
        self.updated_at = datetime.utcnow()
    
    def release_reservation(self, reserved_amount: float) -> None:
        """Libera una reserva (ej: cuando una llamada falla al iniciarse)"""
        if self.plan_type == PlanType.MINUTES_BASED:
            self.minutes_reserved = max(0, self.minutes_reserved - reserved_amount)
        else:  # CREDIT_BASED
            self.credit_reserved = max(0, self.credit_reserved - reserved_amount)
    
    def add_minutes(self, minutes: float) -> None:
        """Agrega minutos comprados"""
        self.minutes_purchased += minutes
        self.last_topup_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_credits(self, amount: float) -> None:
        """Agrega créditos comprados"""
        self.credit_balance += amount
        self.last_topup_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para MongoDB"""
        data = {
            "account_id": self.account_id,
            "account_name": self.account_name,
            "plan_type": self.plan_type.value,
            "status": self.status.value,
            "minutes_purchased": self.minutes_purchased,
            "minutes_used": self.minutes_used,
            "minutes_reserved": self.minutes_reserved,
            "credit_balance": self.credit_balance,
            "credit_used": self.credit_used,
            "credit_reserved": self.credit_reserved,
            "cost_per_minute": self.cost_per_minute,
            "cost_per_call_setup": self.cost_per_call_setup,
            "cost_failed_call": self.cost_failed_call,
            "max_concurrent_calls": self.max_concurrent_calls,
            "daily_call_limit": self.daily_call_limit,
            "calls_today": self.calls_today,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
            "last_topup_at": self.last_topup_at,
        }
        
        # Solo incluir _id si existe
        if self._id is not None:
            data["_id"] = self._id
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountModel":
        """Crea una AccountModel desde un diccionario de MongoDB"""
        return cls(
            _id=data.get("_id"),
            account_id=data.get("account_id", ""),
            account_name=data.get("account_name", ""),
            plan_type=PlanType(data.get("plan_type", "minutes_based")),
            status=AccountStatus(data.get("status", "pending_activation")),
            minutes_purchased=data.get("minutes_purchased", 0.0),
            minutes_used=data.get("minutes_used", 0.0),
            minutes_reserved=data.get("minutes_reserved", 0.0),
            credit_balance=data.get("credit_balance", 0.0),
            credit_used=data.get("credit_used", 0.0),
            credit_reserved=data.get("credit_reserved", 0.0),
            cost_per_minute=data.get("cost_per_minute", 0.15),
            cost_per_call_setup=data.get("cost_per_call_setup", 0.02),
            cost_failed_call=data.get("cost_failed_call", 0.01),
            max_concurrent_calls=data.get("max_concurrent_calls", 3),
            daily_call_limit=data.get("daily_call_limit", 1000),
            calls_today=data.get("calls_today", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            expires_at=data.get("expires_at"),
            last_topup_at=data.get("last_topup_at"),
        )


@dataclass
class DebtorModel:
    """Modelo para deudores consolidados (equivale a la lógica del workflow Adquisicion_v3)"""
    _id: Optional[ObjectId] = None
    batch_id: str = ""
    rut: str = ""  # RUT sin formato (ej: "123456789K")
    rut_fmt: str = ""  # RUT con formato (ej: "12.345.678-9")
    nombre: str = ""
    origen_empresa: Optional[str] = None
    
    # Información de contacto (teléfonos normalizados)
    phones: Dict[str, Optional[str]] = field(default_factory=lambda: {
        "raw_mobile": None,
        "raw_landline": None,
        "mobile_e164": None,
        "landline_e164": None,
        "best_e164": None
    })
    
    # Datos consolidados por RUT
    cantidad_cupones: int = 0  # Cantidad de deudas/cuotas
    monto_total: float = 0.0  # Total en pesos (no centavos)
    
    # Fechas calculadas según lógica del workflow
    fecha_limite: Optional[str] = None  # fecha_vencimiento_max + dias_retraso + 3 días
    fecha_maxima: Optional[str] = None  # fecha_vencimiento_min + dias_retraso + 7 días
    
    # Número de teléfono seleccionado para llamadas
    to_number: Optional[str] = None
    
    # Clave única para identificar este deudor en el batch
    key: str = ""  # Formato: batch_id::rut
    
    # Timestamps
    created_at: Optional[datetime] = None
    
    def generate_key(self) -> str:
        """Genera la clave única para este deudor"""
        return f"{self.batch_id}::{self.rut}"
    
    def get_best_phone(self) -> Optional[str]:
        """Selecciona el mejor número de teléfono disponible"""
        return (
            self.phones.get("mobile_e164") or 
            self.phones.get("landline_e164") or 
            self.phones.get("best_e164")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para MongoDB"""
        data = {
            "batch_id": self.batch_id,
            "rut": self.rut,
            "rut_fmt": self.rut_fmt,
            "nombre": self.nombre,
            "origen_empresa": self.origen_empresa,
            "phones": self.phones,
            "cantidad_cupones": self.cantidad_cupones,
            "monto_total": self.monto_total,
            "fecha_limite": self.fecha_limite,
            "fecha_maxima": self.fecha_maxima,
            "to_number": self.to_number or self.get_best_phone(),
            "key": self.key or self.generate_key(),
            "created_at": self.created_at or datetime.utcnow(),
        }
        
        if self._id is not None:
            data["_id"] = self._id
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebtorModel":
        """Crea un DebtorModel desde un diccionario de MongoDB"""
        return cls(
            _id=data.get("_id"),
            batch_id=data.get("batch_id", ""),
            rut=data.get("rut", ""),
            rut_fmt=data.get("rut_fmt", ""),
            nombre=data.get("nombre", ""),
            origen_empresa=data.get("origen_empresa"),
            phones=data.get("phones", {}),
            cantidad_cupones=data.get("cantidad_cupones", 0),
            monto_total=data.get("monto_total", 0.0),
            fecha_limite=data.get("fecha_limite"),
            fecha_maxima=data.get("fecha_maxima"),
            to_number=data.get("to_number"),
            key=data.get("key", ""),
            created_at=data.get("created_at"),
        )


@dataclass
class BatchModel:
    """Modelo para lotes de llamadas"""
    _id: Optional[ObjectId] = None
    account_id: str = ""
    batch_id: str = ""
    name: str = ""
    description: str = ""
    
    # Estadísticas del batch
    total_jobs: int = 0
    pending_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    suspended_jobs: int = 0
    
    # Costos y tiempos
    total_cost: float = 0.0
    total_minutes: float = 0.0
    estimated_cost: float = 0.0
    
    # Control de ejecución
    is_active: bool = True
    priority: int = 1  # 1 = normal, 2 = alta, 3 = urgente
    
    # Timestamps
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @property
    def completion_rate(self) -> float:
        """Porcentaje de completitud"""
        if self.total_jobs == 0:
            return 0.0
        return (self.completed_jobs / self.total_jobs) * 100
    
    @property
    def is_completed(self) -> bool:
        """Verifica si el batch está completado"""
        return self.pending_jobs == 0 and self.total_jobs > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para MongoDB"""
        data = {
            "account_id": self.account_id,
            "batch_id": self.batch_id,
            "name": self.name,
            "description": self.description,
            "total_jobs": self.total_jobs,
            "pending_jobs": self.pending_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "suspended_jobs": self.suspended_jobs,
            "total_cost": self.total_cost,
            "total_minutes": self.total_minutes,
            "estimated_cost": self.estimated_cost,
            "is_active": self.is_active,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
        
        # Solo incluir _id si existe
        if self._id is not None:
            data["_id"] = self._id
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchModel":
        """Crea un BatchModel desde un diccionario de MongoDB"""
        return cls(
            _id=data.get("_id"),
            account_id=data.get("account_id", ""),
            batch_id=data.get("batch_id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            total_jobs=data.get("total_jobs", 0),
            pending_jobs=data.get("pending_jobs", 0),
            completed_jobs=data.get("completed_jobs", 0),
            failed_jobs=data.get("failed_jobs", 0),
            suspended_jobs=data.get("suspended_jobs", 0),
            total_cost=data.get("total_cost", 0.0),
            total_minutes=data.get("total_minutes", 0.0),
            estimated_cost=data.get("estimated_cost", 0.0),
            is_active=data.get("is_active", True),
            priority=data.get("priority", 1),
            created_at=data.get("created_at"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )