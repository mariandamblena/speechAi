"""
Implementaciones concretas para el caso de uso de COBRANZA
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from ..abstract.base_models import (
    BaseJobPayload, BaseContactInfo, BaseJobModel, 
    BaseBatchModel, BaseJobFactory, BaseJobProcessor
)
from ..abstract.use_case_enums import UseCaseType
from ..enums import JobStatus


@dataclass
class DebtCollectionPayload(BaseJobPayload):
    """Payload específico para cobranza de deudas"""
    debt_amount: float
    due_date: str
    company_name: str = ""
    reference_number: str = ""
    debt_type: str = "general"  # general, credit_card, loan, etc.
    days_overdue: int = 0
    additional_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_retell_context(self) -> Dict[str, str]:
        """Convierte el payload a contexto para Retell (cobranza)"""
        return {
            "tipo_llamada": "cobranza",
            "monto_total": str(self.debt_amount),
            "fecha_limite": self.due_date,
            "empresa": self.company_name,
            "numero_referencia": self.reference_number,
            "tipo_deuda": self.debt_type,
            "dias_vencidos": str(self.days_overdue),
            "informacion_adicional": str(self.additional_info)
        }
    
    def get_script_template_id(self) -> str:
        """Template específico para cobranza"""
        return "debt_collection_script_v1"
    
    def validate(self) -> List[str]:
        """Validación específica para cobranza"""
        errors = []
        
        if self.debt_amount <= 0:
            errors.append("El monto de la deuda debe ser mayor a 0")
        
        if not self.due_date:
            errors.append("La fecha de vencimiento es requerida")
            
        if not self.company_name:
            errors.append("El nombre de la empresa es requerido")
        
        return errors
    
    def get_summary(self) -> str:
        """Resumen para cobranza"""
        return f"Cobranza: ${self.debt_amount:,.0f} - {self.company_name} - Vence: {self.due_date}"


@dataclass
class DebtContactInfo(BaseContactInfo):
    """Información de contacto específica para deudores"""
    rut: str = ""  # Específico para Chile
    email: str = ""
    address: str = ""
    
    def __post_init__(self):
        # En este caso, el identifier es el RUT
        if self.rut and not self.identifier:
            self.identifier = self.rut


@dataclass
class DebtCollectionJob(BaseJobModel):
    """Job específico para cobranza"""
    
    def __post_init__(self):
        super().__post_init__()
        self.use_case = UseCaseType.DEBT_COLLECTION.value
    
    def get_processor_class(self) -> str:
        return "DebtCollectionProcessor"


@dataclass
class DebtCollectionBatch(BaseBatchModel):
    """Batch específico para cobranza"""
    
    # Configuración específica de cobranza
    max_attempts_per_debtor: int = 3
    call_window_hours: str = "09:00-18:00"
    exclude_weekends: bool = True
    
    def __post_init__(self):
        super().__post_init__()
        self.use_case = UseCaseType.DEBT_COLLECTION.value
        
        # Configuración específica
        self.config.update({
            "max_attempts": self.max_attempts_per_debtor,
            "call_window": self.call_window_hours,
            "exclude_weekends": self.exclude_weekends
        })
    
    def get_job_factory(self) -> 'DebtCollectionJobFactory':
        return DebtCollectionJobFactory()


class DebtCollectionJobFactory(BaseJobFactory):
    """Factory para crear jobs de cobranza desde Excel/datos"""
    
    def get_required_columns(self) -> List[str]:
        """Columnas requeridas para cobranza"""
        return [
            "nombre", "rut", "telefono", "deuda", 
            "fecha_vencimiento", "empresa"
        ]
    
    def validate_row_data(self, row_data: Dict[str, Any]) -> List[str]:
        """Validación específica de datos de cobranza"""
        errors = []
        
        required_fields = self.get_required_columns()
        for field in required_fields:
            if field not in row_data or not row_data[field]:
                errors.append(f"Campo requerido faltante: {field}")
        
        # Validaciones específicas
        if "deuda" in row_data:
            try:
                debt = float(row_data["deuda"])
                if debt <= 0:
                    errors.append("La deuda debe ser mayor a 0")
            except (ValueError, TypeError):
                errors.append("La deuda debe ser un número válido")
        
        return errors
    
    def create_job_from_data(self, row_data: Dict[str, Any], batch_id: str, account_id: str) -> DebtCollectionJob:
        """Crea job de cobranza desde datos Excel/CSV"""
        
        # Procesar teléfonos
        phones = []
        phone_fields = ["telefono", "telefono2", "telefono3", "celular", "movil"]
        for field in phone_fields:
            if field in row_data and row_data[field]:
                phones.append(str(row_data[field]))
        
        # Crear contacto
        contact = DebtContactInfo(
            name=str(row_data.get("nombre", "")),
            rut=str(row_data.get("rut", "")),
            identifier=str(row_data.get("rut", "")),
            phones=phones,
            email=str(row_data.get("email", "")),
            address=str(row_data.get("direccion", ""))
        )
        
        # Crear payload
        payload = DebtCollectionPayload(
            debt_amount=float(row_data.get("deuda", 0)),
            due_date=str(row_data.get("fecha_vencimiento", "")),
            company_name=str(row_data.get("empresa", "")),
            reference_number=str(row_data.get("numero_referencia", "")),
            additional_info=row_data.get("info_adicional", {})
        )
        
        # Crear job
        job = DebtCollectionJob(
            _id="",  # Se auto-genera
            account_id=account_id,
            batch_id=batch_id,
            use_case=UseCaseType.DEBT_COLLECTION.value,
            status=JobStatus.PENDING,
            contact=contact,
            payload=payload,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return job


class DebtCollectionProcessor(BaseJobProcessor):
    """Procesador específico para jobs de cobranza"""
    
    def can_process(self, job: BaseJobModel) -> bool:
        return job.use_case == UseCaseType.DEBT_COLLECTION.value
    
    def get_supported_use_cases(self) -> List[str]:
        return [UseCaseType.DEBT_COLLECTION.value]
    
    def process_job(self, job: BaseJobModel) -> Dict[str, Any]:
        """Procesamiento específico para cobranza"""
        if not isinstance(job.payload, DebtCollectionPayload):
            raise ValueError("Job payload debe ser DebtCollectionPayload")
        
        # Aquí iría la lógica específica de procesamiento de cobranza
        # Por ejemplo: validaciones adicionales, preparación de contexto específico, etc.
        
        context = job.payload.to_retell_context()
        
        # Agregar contexto adicional específico de cobranza
        context.update({
            "nombre_deudor": job.contact.name,
            "identificador": job.contact.identifier,
            "script_template": job.payload.get_script_template_id()
        })
        
        return {
            "context": context,
            "phone": job.contact.current_phone,
            "processor_type": "debt_collection",
            "job_summary": job.payload.get_summary()
        }