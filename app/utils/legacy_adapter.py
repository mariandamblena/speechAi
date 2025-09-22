"""
Adaptador para migrar jobs del formato anterior al formato modular
Convierte jobs con formato legacy a JobModel compatible
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from bson import ObjectId

from domain.models import JobModel, ContactInfo, CallPayload
from domain.enums import JobStatus, CallMode

logger = logging.getLogger(__name__)


class JobLegacyAdapter:
    """
    Adaptador que convierte jobs del formato legacy al formato modular
    
    Formato Legacy:
    {
        "_id": ObjectId,
        "rut": "273272038",
        "nombre": "RICHARD RENE RAMOS PEREZ", 
        "to_number": "+5491136530246",
        "monto_total": 104050,
        "origen_empresa": "Natura",
        ...
    }
    
    Formato Nuevo:
    JobModel con ContactInfo y CallPayload
    """
    
    @staticmethod
    def can_adapt(job_data: Dict[str, Any]) -> bool:
        """
        Verifica si un job tiene formato legacy que se puede adaptar
        
        Args:
            job_data: Datos del job desde MongoDB
            
        Returns:
            True si se puede adaptar
        """
        required_fields = ["rut", "nombre", "to_number", "monto_total"]
        return all(field in job_data for field in required_fields)
    
    @staticmethod
    def adapt_to_job_model(job_data: Dict[str, Any]) -> Optional[JobModel]:
        """
        Convierte job legacy a JobModel
        
        Args:
            job_data: Job en formato legacy
            
        Returns:
            JobModel adaptado o None si no se puede convertir
        """
        try:
            if not JobLegacyAdapter.can_adapt(job_data):
                logger.warning(f"Job {job_data.get('_id')} no se puede adaptar - faltan campos requeridos")
                return None
            
            # Extraer información de contacto
            contact = ContactInfo(
                name=job_data["nombre"],
                dni=job_data["rut"],
                phones=JobLegacyAdapter._extract_phones(job_data)
            )
            
            # Extraer información de deuda  
            payload = CallPayload(
                debt_amount=float(job_data["monto_total"]),
                due_date=job_data.get("fecha_limite", ""),
                company_name=job_data.get("origen_empresa", ""),
                reference_number=job_data.get("job_id", ""),
                additional_info={
                    "rut_fmt": job_data.get("rut_fmt", ""),
                    "cantidad_cupones": job_data.get("cantidad_cupones", 1),
                    "fecha_maxima": job_data.get("fecha_maxima", ""),
                    "batch_id": job_data.get("batch_id", "")
                }
            )
            
            # Crear JobModel
            job = JobModel(
                _id=job_data.get("_id"),
                status=JobStatus(job_data.get("status", "pending")),
                contact=contact,
                payload=payload,
                mode=CallMode.SINGLE,
                attempts=job_data.get("attempts", 0),
                max_attempts=job_data.get("max_attempts", 3),
                reserved_until=job_data.get("reserved_until"),
                worker_id=job_data.get("reserved_by"),  # Mapeo de campo legacy
                created_at=job_data.get("created_at"),
                call_id=job_data.get("call_id"),
                call_result=job_data.get("call_result"),
                last_error=job_data.get("last_error")
            )
            
            logger.info(f"✅ Job adaptado: {contact.dni} ({contact.name}) -> ${payload.debt_amount:,.0f}")
            return job
            
        except Exception as e:
            logger.error(f"Error adaptando job {job_data.get('_id')}: {e}")
            return None
    
    @staticmethod
    def _extract_phones(job_data: Dict[str, Any]) -> list[str]:
        """Extrae lista de teléfonos del job legacy"""
        phones = []
        
        # Teléfono principal
        if "to_number" in job_data:
            phones.append(job_data["to_number"])
        
        # Lista adicional de teléfonos
        if "try_phones" in job_data:
            try_phones = job_data["try_phones"]
            if isinstance(try_phones, list):
                for phone in try_phones:
                    if phone and phone not in phones:
                        phones.append(phone)
        
        # Asegurar que al menos tengamos un teléfono
        if not phones and "to_number" in job_data:
            phones.append(job_data["to_number"])
            
        return phones
    
    @staticmethod
    def update_legacy_job_in_db(collection, job_model: JobModel) -> bool:
        """
        Actualiza el job legacy en la BD manteniendo compatibilidad
        
        Args:
            collection: Colección de MongoDB
            job_model: JobModel actualizado
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            # Preparar update que mantiene campos legacy y agrega nuevos
            update_data = {
                "status": job_model.status.value,
                "attempts": job_model.attempts,
                "reserved_by": job_model.worker_id,  # Mapeo reverso
                "reserved_until": job_model.reserved_until,
                "updated_at": datetime.utcnow(),
            }
            
            # Campos opcionales
            if job_model.call_id:
                update_data["call_id"] = job_model.call_id
            if job_model.call_result:
                update_data["call_result"] = job_model.call_result  
            if job_model.last_error:
                update_data["last_error"] = job_model.last_error
            if job_model.started_at:
                update_data["started_at"] = job_model.started_at
            if job_model.completed_at:
                update_data["completed_at"] = job_model.completed_at
            if job_model.failed_at:
                update_data["failed_at"] = job_model.failed_at
            
            result = collection.update_one(
                {"_id": job_model._id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error actualizando job legacy {job_model._id}: {e}")
            return False