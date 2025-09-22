"""
Modelos de dominio para la aplicación
Siguiendo principios de Domain-Driven Design (DDD)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId

from .enums import JobStatus, CallStatus, CallMode


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
    status: JobStatus = JobStatus.PENDING
    contact: Optional[ContactInfo] = None
    payload: Optional[CallPayload] = None
    mode: CallMode = CallMode.SINGLE
    
    # Campos de control
    attempts: int = 0
    max_attempts: int = 3
    reserved_until: Optional[datetime] = None
    worker_id: Optional[str] = None
    
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
            "status": self.status.value,
            "mode": self.mode.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
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
            "reserved_until", "worker_id", "created_at", "started_at", 
            "completed_at", "failed_at", "updated_at", "call_id", 
            "call_result", "last_error"
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
            status=JobStatus(data.get("status", "pending")),
            contact=contact,
            payload=payload,
            mode=CallMode(data.get("mode", "single")),
            attempts=data.get("attempts", 0),
            max_attempts=data.get("max_attempts", 3),
            reserved_until=data.get("reserved_until"),
            worker_id=data.get("worker_id"),
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