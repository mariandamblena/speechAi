"""
Implementaciones concretas para el caso de uso de USER EXPERIENCE
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
class UserExperiencePayload(BaseJobPayload):
    """Payload específico para llamadas de user experience"""
    interaction_type: str  # post_purchase, feedback, survey, notification
    customer_id: str
    product_or_service: str = ""
    purchase_date: Optional[str] = None
    satisfaction_target: str = "general"  # general, specific_issue, follow_up
    custom_message: str = ""
    survey_questions: List[str] = field(default_factory=list)
    expected_duration_minutes: int = 5
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_retell_context(self) -> Dict[str, str]:
        """Convierte el payload a contexto para Retell (UX)"""
        return {
            "tipo_llamada": "experiencia_usuario",
            "tipo_interaccion": self.interaction_type,
            "cliente_id": self.customer_id,
            "producto_servicio": self.product_or_service,
            "fecha_compra": self.purchase_date or "",
            "objetivo_satisfaccion": self.satisfaction_target,
            "mensaje_personalizado": self.custom_message,
            "preguntas_encuesta": "|".join(self.survey_questions),
            "duracion_esperada": str(self.expected_duration_minutes),
            "contexto_adicional": str(self.additional_context)
        }
    
    def get_script_template_id(self) -> str:
        """Template específico según tipo de interacción UX"""
        template_map = {
            "post_purchase": "ux_post_purchase_v1",
            "feedback": "ux_feedback_collection_v1", 
            "survey": "ux_survey_v1",
            "notification": "ux_notification_v1"
        }
        return template_map.get(self.interaction_type, "ux_general_v1")
    
    def validate(self) -> List[str]:
        """Validación específica para UX"""
        errors = []
        
        valid_types = ["post_purchase", "feedback", "survey", "notification"]
        if self.interaction_type not in valid_types:
            errors.append(f"Tipo de interacción debe ser uno de: {valid_types}")
        
        if not self.customer_id:
            errors.append("ID de cliente es requerido")
            
        if self.expected_duration_minutes <= 0:
            errors.append("Duración esperada debe ser mayor a 0")
        
        if self.interaction_type == "survey" and not self.survey_questions:
            errors.append("Las encuestas requieren al menos una pregunta")
        
        return errors
    
    def get_summary(self) -> str:
        """Resumen para UX"""
        return f"UX: {self.interaction_type} - Cliente: {self.customer_id} - {self.product_or_service}"


@dataclass 
class UserExperienceContactInfo(BaseContactInfo):
    """Información de contacto específica para UX"""
    customer_id: str = ""
    email: str = ""
    preferred_contact_time: str = ""
    language_preference: str = "es"
    
    def __post_init__(self):
        # En este caso, el identifier es el customer_id
        if self.customer_id and not self.identifier:
            self.identifier = self.customer_id


@dataclass
class UserExperienceJob(BaseJobModel):
    """Job específico para user experience"""
    
    def __post_init__(self):
        super().__post_init__()
        self.use_case = UseCaseType.USER_EXPERIENCE.value
    
    def get_processor_class(self) -> str:
        return "UserExperienceProcessor"


@dataclass
class UserExperienceBatch(BaseBatchModel):
    """Batch específico para user experience"""
    
    # Configuración específica de UX
    interaction_type: str = "feedback"
    target_completion_rate: float = 80.0
    max_attempts_per_customer: int = 2
    respect_do_not_call: bool = True
    preferred_time_window: str = "10:00-20:00"
    
    def __post_init__(self):
        super().__post_init__()
        self.use_case = UseCaseType.USER_EXPERIENCE.value
        
        # Configuración específica
        self.config.update({
            "interaction_type": self.interaction_type,
            "target_completion_rate": self.target_completion_rate,
            "max_attempts": self.max_attempts_per_customer,
            "respect_dnc": self.respect_do_not_call,
            "time_window": self.preferred_time_window
        })
    
    def get_job_factory(self) -> 'UserExperienceJobFactory':
        return UserExperienceJobFactory()


class UserExperienceJobFactory(BaseJobFactory):
    """Factory para crear jobs de UX desde datos"""
    
    def get_required_columns(self) -> List[str]:
        """Columnas requeridas para UX"""
        return [
            "nombre", "customer_id", "telefono", 
            "interaction_type", "producto_servicio"
        ]
    
    def validate_row_data(self, row_data: Dict[str, Any]) -> List[str]:
        """Validación específica de datos de UX"""
        errors = []
        
        required_fields = self.get_required_columns()
        for field in required_fields:
            if field not in row_data or not row_data[field]:
                errors.append(f"Campo requerido faltante: {field}")
        
        # Validaciones específicas de UX
        if "interaction_type" in row_data:
            valid_types = ["post_purchase", "feedback", "survey", "notification"]
            if row_data["interaction_type"] not in valid_types:
                errors.append(f"Tipo de interacción inválido. Debe ser: {valid_types}")
        
        return errors
    
    def create_job_from_data(self, row_data: Dict[str, Any], batch_id: str, account_id: str) -> UserExperienceJob:
        """Crea job de UX desde datos Excel/CSV"""
        
        # Procesar teléfonos
        phones = []
        phone_fields = ["telefono", "telefono2", "celular", "movil"]
        for field in phone_fields:
            if field in row_data and row_data[field]:
                phones.append(str(row_data[field]))
        
        # Crear contacto
        contact = UserExperienceContactInfo(
            name=str(row_data.get("nombre", "")),
            customer_id=str(row_data.get("customer_id", "")),
            identifier=str(row_data.get("customer_id", "")),
            phones=phones,
            email=str(row_data.get("email", "")),
            preferred_contact_time=str(row_data.get("hora_preferida", "")),
            language_preference=str(row_data.get("idioma", "es"))
        )
        
        # Procesar preguntas de encuesta si existen
        survey_questions = []
        if "preguntas" in row_data and row_data["preguntas"]:
            questions_str = str(row_data["preguntas"])
            survey_questions = [q.strip() for q in questions_str.split("|") if q.strip()]
        
        # Crear payload
        payload = UserExperiencePayload(
            interaction_type=str(row_data.get("interaction_type", "feedback")),
            customer_id=str(row_data.get("customer_id", "")),
            product_or_service=str(row_data.get("producto_servicio", "")),
            purchase_date=str(row_data.get("fecha_compra", "")),
            satisfaction_target=str(row_data.get("objetivo", "general")),
            custom_message=str(row_data.get("mensaje_personalizado", "")),
            survey_questions=survey_questions,
            expected_duration_minutes=int(row_data.get("duracion_minutos", 5)),
            additional_context=row_data.get("contexto_adicional", {})
        )
        
        # Crear job
        job = UserExperienceJob(
            _id="",  # Se auto-genera
            account_id=account_id,
            batch_id=batch_id,
            use_case=UseCaseType.USER_EXPERIENCE.value,
            status=JobStatus.PENDING,
            contact=contact,
            payload=payload,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        return job


class UserExperienceProcessor(BaseJobProcessor):
    """Procesador específico para jobs de user experience"""
    
    def can_process(self, job: BaseJobModel) -> bool:
        return job.use_case == UseCaseType.USER_EXPERIENCE.value
    
    def get_supported_use_cases(self) -> List[str]:
        return [UseCaseType.USER_EXPERIENCE.value]
    
    def process_job(self, job: BaseJobModel) -> Dict[str, Any]:
        """Procesamiento específico para UX"""
        if not isinstance(job.payload, UserExperiencePayload):
            raise ValueError("Job payload debe ser UserExperiencePayload")
        
        context = job.payload.to_retell_context()
        
        # Agregar contexto adicional específico de UX
        context.update({
            "nombre_cliente": job.contact.name,
            "identificador": job.contact.identifier,
            "script_template": job.payload.get_script_template_id(),
            "hora_preferida": getattr(job.contact, 'preferred_contact_time', ''),
            "idioma": getattr(job.contact, 'language_preference', 'es')
        })
        
        return {
            "context": context,
            "phone": job.contact.current_phone,
            "processor_type": "user_experience", 
            "job_summary": job.payload.get_summary()
        }