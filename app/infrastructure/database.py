"""
Servicio de base de datos usando patrón Repository
Maneja la persistencia de jobs y resultados de llamadas
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError
from bson import ObjectId

from config.settings import DatabaseConfig
from domain.models import JobModel, CallResult
from domain.enums import JobStatus
from utils.legacy_adapter import JobLegacyAdapter

logger = logging.getLogger(__name__)


class IJobRepository(ABC):
    """Interface para repositorio de jobs (Dependency Inversion)"""
    
    @abstractmethod
    def find_and_claim_pending_job(self, worker_id: str, lease_seconds: int) -> Optional[JobModel]:
        """Busca y reserva un job pendiente"""
        pass
    
    @abstractmethod
    def update_job_status(
        self, 
        job_id: ObjectId, 
        status: JobStatus, 
        **kwargs
    ) -> bool:
        """Actualiza el estado de un job"""
        pass
    
    @abstractmethod
    def save_job_result(
        self, 
        job_id: ObjectId, 
        call_id: str, 
        call_data: Dict[str, Any]
    ) -> bool:
        """Guarda el resultado de una llamada"""
        pass


class ICallResultRepository(ABC):
    """Interface para repositorio de resultados de llamadas"""
    
    @abstractmethod
    def save_result(self, call_result: CallResult) -> bool:
        """Guarda un resultado de llamada"""
        pass
    
    @abstractmethod
    def find_results_by_contact(self, dni: str) -> List[CallResult]:
        """Busca resultados por DNI del contacto"""
        pass


class MongoJobRepository(IJobRepository):
    """
    Implementación de repositorio de jobs usando MongoDB
    Sigue principios SOLID:
    - Single Responsibility: Solo maneja persistencia de jobs
    - Open/Closed: Extensible sin modificar código
    """
    
    def __init__(self, client: MongoClient, config: DatabaseConfig):
        self.collection = client[config.database][config.jobs_collection]
        self.config = config
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Crea índices necesarios para performance"""
        try:
            indexes = [
                ([("status", 1), ("reserved_until", 1)], "status_reserved_idx"),
                ([("attempts", 1)], "attempts_idx"),
                ([("contact.dni", 1), ("status", 1)], "contact_dni_status_idx"),
                ([("call_id", 1)], "call_id_idx"),
                ([("worker_id", 1), ("status", 1)], "worker_status_idx"),
            ]
            
            for index_spec, index_name in indexes:
                self.collection.create_index(index_spec, name=index_name, background=True)
                
            logger.info("Índices de jobs verificados/creados")
            
        except PyMongoError as e:
            logger.error(f"Error creando índices de jobs: {e}")
    
    def find_and_claim_pending_job(self, worker_id: str, lease_seconds: int) -> Optional[JobModel]:
        """
        Busca un job pendiente y lo reserva atómicamente
        
        Args:
            worker_id: ID del worker que reserva el job
            lease_seconds: Segundos por los cuales se reserva
            
        Returns:
            JobModel si se encontró y reservó un job, None caso contrario
        """
        now = self._utcnow()
        reservation_until = now + timedelta(seconds=lease_seconds)
        
        try:
            # Query atómica para encontrar y reservar job
            doc = self.collection.find_one_and_update(
                filter={
                    "status": JobStatus.PENDING.value,
                    "$or": [
                        {"reserved_until": {"$lt": now}},
                        {"reserved_until": {"$exists": False}},
                        {"reserved_until": None},
                    ],
                    "$expr": {
                        "$lt": [
                            {"$ifNull": ["$attempts", 0]}, 
                            {"$ifNull": ["$max_attempts", 3]}
                        ]
                    }
                },
                update={
                    "$set": {
                        "status": JobStatus.IN_PROGRESS.value,
                        "reserved_until": reservation_until,
                        "worker_id": worker_id,
                        "started_at": now,
                        "updated_at": now,
                    },
                    "$inc": {"attempts": 1}
                },
                return_document=ReturnDocument.AFTER
            )
            
            if doc:
                # Intentar crear JobModel desde documento
                job = JobModel.from_dict(doc)
                
                # Si falla, intentar adaptar formato legacy
                if not job or not job.contact:
                    logger.info(f"Intentando adaptar job legacy: {doc.get('_id')}")
                    job = JobLegacyAdapter.adapt_to_job_model(doc)
                
                if job and job.contact:
                    logger.info(f"Job reservado: {job.contact.dni if job.contact else 'unknown'} por {worker_id}")
                    return job
                else:
                    logger.warning(f"Job {doc.get('_id')} no se pudo procesar - formato inválido")
                    return None
                
            return None
            
        except PyMongoError as e:
            logger.error(f"Error claiming job: {e}")
            return None
    
    def update_job_status(
        self, 
        job_id: ObjectId, 
        status: JobStatus,
        **kwargs
    ) -> bool:
        """
        Actualiza el estado de un job (compatible con formato legacy)
        
        Args:
            job_id: ID del job
            status: Nuevo estado
            **kwargs: Campos adicionales a actualizar
            
        Returns:
            True si se actualizó correctamente
        """
        try:
            update_data = {
                "status": status.value,
                "updated_at": self._utcnow()
            }
            
            # Campos específicos según el estado
            if status == JobStatus.COMPLETED:
                update_data["completed_at"] = self._utcnow()
                update_data["reserved_until"] = None
                update_data["reserved_by"] = None  # Campo legacy
                
            elif status == JobStatus.FAILED:
                update_data["failed_at"] = self._utcnow()
                update_data["reserved_until"] = None
                update_data["reserved_by"] = None  # Campo legacy
                
            elif status == JobStatus.PENDING:
                update_data["reserved_until"] = None
                update_data["worker_id"] = None
                update_data["reserved_by"] = None  # Campo legacy
            
            # Mapear campos nuevos a legacy si es necesario
            legacy_mappings = {
                "worker_id": "reserved_by"
            }
            
            for new_field, legacy_field in legacy_mappings.items():
                if new_field in kwargs:
                    update_data[legacy_field] = kwargs[new_field]
            
            # Agregar campos adicionales
            update_data.update(kwargs)
            
            result = self.collection.update_one(
                {"_id": job_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Job {job_id} actualizado a estado {status.value}")
            else:
                logger.warning(f"No se pudo actualizar job {job_id}")
                
            return success
            
        except PyMongoError as e:
            logger.error(f"Error actualizando job {job_id}: {e}")
            return False
    
    def save_job_result(
        self, 
        job_id: ObjectId, 
        call_id: str, 
        call_data: Dict[str, Any]
    ) -> bool:
        """Guarda resultado de llamada en el job"""
        try:
            result = self.collection.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "call_id": call_id,
                        "call_result": call_data,
                        "updated_at": self._utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Resultado guardado para job {job_id}, call {call_id}")
            
            return success
            
        except PyMongoError as e:
            logger.error(f"Error guardando resultado del job {job_id}: {e}")
            return False
    
    def _utcnow(self) -> datetime:
        """Obtiene datetime UTC actual"""
        return datetime.now(timezone.utc)


class MongoCallResultRepository(ICallResultRepository):
    """Repositorio para resultados de llamadas"""
    
    def __init__(self, client: MongoClient, config: DatabaseConfig):
        self.collection = client[config.database][config.results_collection]
        self.config = config
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Crea índices para resultados"""
        try:
            indexes = [
                ([("call_id", 1)], "call_id_unique", True),  # Único
                ([("contact.dni", 1), ("created_at", -1)], "contact_date_idx"),
                ([("call_data.call_status", 1)], "status_idx"),
                ([("is_successful", 1), ("created_at", -1)], "success_date_idx"),
            ]
            
            for index_spec, index_name, *unique in indexes:
                is_unique = unique[0] if unique else False
                self.collection.create_index(
                    index_spec, 
                    name=index_name, 
                    unique=is_unique,
                    background=True
                )
                
            logger.info("Índices de call_results verificados/creados")
            
        except PyMongoError as e:
            logger.error(f"Error creando índices de resultados: {e}")
    
    def save_result(self, call_result: CallResult) -> bool:
        """Guarda resultado de llamada"""
        try:
            self.collection.update_one(
                {"call_id": call_result.call_id},
                {"$set": call_result.to_dict()},
                upsert=True
            )
            
            logger.info(f"Resultado guardado: {call_result.call_id} -> {call_result.call_status}")
            return True
            
        except PyMongoError as e:
            logger.error(f"Error guardando resultado {call_result.call_id}: {e}")
            return False
    
    def find_results_by_contact(self, dni: str) -> List[CallResult]:
        """Busca resultados por DNI"""
        try:
            docs = self.collection.find(
                {"contact.dni": dni}
            ).sort("created_at", -1)
            
            results = []
            for doc in docs:
                # Reconstruir CallResult desde documento
                # (simplificado para este ejemplo)
                results.append(doc)
            
            return results
            
        except PyMongoError as e:
            logger.error(f"Error buscando resultados para {dni}: {e}")
            return []


class DatabaseService:
    """
    Servicio principal de base de datos
    Implementa el patrón Facade para simplificar acceso a repositorios
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.client = MongoClient(
            config.uri,
            maxPoolSize=config.max_pool_size
        )
        
        # Repositorios
        self.jobs = MongoJobRepository(self.client, config)
        self.call_results = MongoCallResultRepository(self.client, config)
        
        logger.info(f"DatabaseService inicializado: {config.database}")
    
    def health_check(self) -> bool:
        """Verifica conectividad con la base de datos"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Health check falló: {e}")
            return False
    
    def close(self):
        """Cierra conexiones"""
        if self.client:
            self.client.close()
            logger.info("Conexiones de base de datos cerradas")