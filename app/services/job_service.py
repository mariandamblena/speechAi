"""
Servicio para manejo de jobs de llamadas
Implementa lógica de negocio siguiendo principios SOLID
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from config.settings import WorkerConfig
from domain.models import JobModel, CallResult, ContactInfo
from domain.enums import JobStatus
from infrastructure.database_manager import DatabaseManager
from typing import Optional, List, Dict, Any, Protocol

# Interfaces temporales para compatibilidad
class IJobRepository(Protocol):
    def find_and_claim_pending_job(self, worker_id: str, lease_seconds: int) -> Optional[JobModel]: ...
    def update_job_status(self, job_id, status: JobStatus, **kwargs) -> bool: ...
    def save_job_result(self, job_id, call_id: str, call_data: Dict[str, Any]) -> bool: ...

class ICallResultRepository(Protocol):
    def save_call_result(self, result: CallResult) -> bool: ...

# TODO: Migrar completamente a database_manager cuando se necesite usar workers

logger = logging.getLogger(__name__)


class JobService:
    """
    Servicio para manejo de jobs de llamadas
    
    Responsabilidades:
    - Claiming de jobs pendientes
    - Actualización de estados
    - Lógica de retry
    - Guardado de resultados
    
    Sigue principios SOLID:
    - Single Responsibility: Solo maneja lógica de jobs
    - Dependency Inversion: Depende de interfaces, no implementaciones
    """
    
    def __init__(
        self,
        job_repo: IJobRepository,
        call_result_repo: ICallResultRepository,
        config: WorkerConfig
    ):
        self.job_repo = job_repo
        self.call_result_repo = call_result_repo
        self.config = config
    
    def claim_pending_job(self, worker_id: str) -> Optional[JobModel]:
        """
        Intenta reservar un job pendiente para el worker
        
        Args:
            worker_id: Identificador del worker
            
        Returns:
            JobModel si se pudo reservar un job, None caso contrario
        """
        job = self.job_repo.find_and_claim_pending_job(
            worker_id=worker_id,
            lease_seconds=self.config.lease_seconds
        )
        
        if job:
            logger.info(
                f"Job reclamado por {worker_id}: "
                f"{job.contact.dni if job.contact else 'unknown'} "
                f"(intento {job.attempts}/{job.max_attempts})"
            )
        
        return job
    
    def complete_job_successfully(
        self,
        job: JobModel,
        call_id: str,
        call_data: dict
    ) -> bool:
        """
        Marca un job como completado exitosamente
        
        Args:
            job: Job a completar
            call_id: ID de la llamada de Retell
            call_data: Datos de resultado de la llamada
            
        Returns:
            True si se completó correctamente
        """
        try:
            # Actualizar job como completado
            success = self.job_repo.update_job_status(
                job_id=job._id,
                status=JobStatus.COMPLETED,
                call_id=call_id,
                call_result=call_data
            )
            
            if not success:
                logger.error(f"No se pudo marcar job {job._id} como completado")
                return False
            
            # Guardar resultado detallado si tenemos información de contacto
            if job.contact:
                call_result = CallResult(
                    call_id=call_id,
                    job_id=str(job._id),
                    contact=job.contact,
                    call_data=call_data,
                    created_at=self._utcnow()
                )
                
                result_saved = self.call_result_repo.save_result(call_result)
                if not result_saved:
                    logger.warning(f"No se pudo guardar resultado detallado para {call_id}")
            
            logger.info(
                f"✅ Job completado: {job.contact.dni if job.contact else 'unknown'} "
                f"-> {call_data.get('call_status', 'unknown')}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error completando job {job._id}: {e}")
            return False
    
    def fail_job(
        self,
        job: JobModel,
        error_message: str,
        should_retry: bool = True
    ) -> bool:
        """
        Marca un job como fallido
        
        Args:
            job: Job que falló
            error_message: Descripción del error
            should_retry: Si el job debería reintentarse
            
        Returns:
            True si se procesó correctamente
        """
        try:
            can_retry = should_retry and job.can_retry()
            
            if can_retry:
                # Devolver a pending para retry posterior
                success = self.job_repo.update_job_status(
                    job_id=job._id,
                    status=JobStatus.PENDING,
                    last_error=error_message
                )
                
                logger.warning(
                    f"⚠️ Job devuelto a pending: {job.contact.dni if job.contact else 'unknown'} "
                    f"- {error_message} (intento {job.attempts}/{job.max_attempts})"
                )
            
            else:
                # Marcar como fallido permanentemente
                success = self.job_repo.update_job_status(
                    job_id=job._id,
                    status=JobStatus.FAILED,
                    last_error=error_message
                )
                
                logger.error(
                    f"❌ Job falló permanentemente: {job.contact.dni if job.contact else 'unknown'} "
                    f"- {error_message}"
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error marcando job {job._id} como fallido: {e}")
            return False
    
    def advance_to_next_phone(self, job: JobModel) -> bool:
        """
        Avanza al siguiente teléfono del contacto si hay más disponibles
        
        Args:
            job: Job con múltiples teléfonos
            
        Returns:
            True si hay más teléfonos disponibles
        """
        if not job.contact:
            return False
        
        has_more = job.contact.advance_to_next_phone()
        
        if has_more:
            # Resetear intentos para el nuevo teléfono
            try:
                self.job_repo.update_job_status(
                    job_id=job._id,
                    status=JobStatus.PENDING,
                    attempts=0,
                    last_error=None
                )
                
                logger.info(
                    f"📞 Cambiando a siguiente teléfono para {job.contact.dni}: "
                    f"{job.contact.current_phone}"
                )
                return True
                
            except Exception as e:
                logger.error(f"Error avanzando teléfono para job {job._id}: {e}")
                return False
        
        return False
    
    def should_retry_with_different_phone(self, job: JobModel, call_status: str) -> bool:
        """
        Determina si se debe reintentar con un teléfono diferente
        
        Args:
            job: Job actual
            call_status: Estado de la llamada que falló
            
        Returns:
            True si se debe reintentar con otro teléfono
        """
        # Estados que sugieren problema con el número específico
        phone_specific_failures = [
            "no_answer",
            "busy", 
            "failed",
            "invalid_number",
            "network_error"
        ]
        
        return (
            call_status in phone_specific_failures and
            job.contact and
            len(job.contact.phones) > 1 and
            job.contact.next_phone_index < len(job.contact.phones) - 1
        )
    
    def get_retry_delay_minutes(self, job: JobModel, call_status: str) -> int:
        """
        Calcula tiempo de espera antes del próximo intento
        
        Args:
            job: Job que necesita retry
            call_status: Estado de la llamada fallida
            
        Returns:
            Minutos a esperar antes del retry
        """
        if call_status == "no_answer":
            return self.config.retry_delay_minutes * 2  # Más tiempo para no answer
        elif call_status in ["busy", "network_error"]:
            return min(self.config.retry_delay_minutes // 2, 15)  # Menos tiempo para busy
        else:
            return self.config.retry_delay_minutes
    
    def _utcnow(self) -> datetime:
        """Obtiene datetime UTC actual"""
        return datetime.now(timezone.utc)