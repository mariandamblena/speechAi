"""
Servicio para gestión de batches/lotes de llamadas
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
from bson import ObjectId
import uuid

from domain.models import BatchModel, JobModel
from domain.enums import JobStatus
from infrastructure.database_manager import DatabaseManager


class BatchService:
    """Servicio para gestión de batches de llamadas"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.batches_collection = db_manager.get_collection("batches")
        self.jobs_collection = db_manager.get_collection("jobs")
        self.logger = logging.getLogger(__name__)
    
    def _get_batch_filter(self, batch_id: str) -> Dict[str, Any]:
        """
        Genera filtro para buscar batch por batch_id o _id
        
        Args:
            batch_id: Puede ser batch_id personalizado o _id de MongoDB
        
        Returns:
            Filtro MongoDB
        """
        # Intentar como ObjectId primero
        try:
            if ObjectId.is_valid(batch_id):
                return {"_id": ObjectId(batch_id)}
        except:
            pass
        
        # Si no es ObjectId válido, buscar por batch_id
        return {"batch_id": batch_id}
    
    async def create_batch(
        self,
        account_id: str,
        name: str,
        description: str = "",
        priority: int = 1,
        call_settings: Optional[Dict[str, Any]] = None
    ) -> BatchModel:
        """Crea un nuevo batch con configuración de llamadas opcional"""
        
        batch_id = f"batch-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        
        batch = BatchModel(
            account_id=account_id,
            batch_id=batch_id,
            name=name,
            description=description,
            priority=priority,
            call_settings=call_settings,  # Incluir call_settings
            created_at=datetime.utcnow()
        )
        
        result = await self.batches_collection.insert_one(batch.to_dict())
        batch._id = result.inserted_id
        
        self.logger.info(f"Created batch {batch_id} for account {account_id}")
        if call_settings:
            self.logger.info(f"Batch {batch_id} has custom call_settings: {call_settings}")
        
        return batch
    
    async def get_batch(self, batch_id: str) -> Optional[BatchModel]:
        """
        Obtiene un batch por ID (acepta batch_id o _id de MongoDB)
        """
        batch_filter = self._get_batch_filter(batch_id)
        data = await self.batches_collection.find_one(batch_filter)
        if data:
            return BatchModel.from_dict(data)
        return None
    
    async def get_batch_by_object_id(self, object_id: ObjectId) -> Optional[BatchModel]:
        """Obtiene un batch por ObjectId de MongoDB"""
        data = await self.batches_collection.find_one({"_id": object_id})
        if data:
            return BatchModel.from_dict(data)
        return None
    
    async def update_batch_stats(self, batch_id: str) -> bool:
        """Actualiza estadísticas del batch basándose en sus jobs"""
        
        # Agregación para obtener estadísticas
        pipeline = [
            {"$match": {"batch_id": batch_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1},
                "total_cost": {"$sum": {"$ifNull": ["$call_result.call_cost.combined_cost", 0]}},
                "total_minutes": {"$sum": {"$divide": [
                    {"$ifNull": ["$call_result.duration_ms", 0]}, 
                    60000
                ]}}
            }}
        ]
        
        stats_cursor = self.jobs_collection.aggregate(pipeline)
        stats = {}
        total_cost = 0
        total_minutes = 0
        
        async for stat in stats_cursor:
            status = stat["_id"]
            count = stat["count"]
            stats[status] = count
            total_cost += stat.get("total_cost", 0) / 100  # Convertir de centavos
            total_minutes += stat.get("total_minutes", 0)
        
        # Calcular totales
        total_jobs = sum(stats.values())
        pending_jobs = stats.get("pending", 0)
        completed_jobs = stats.get("completed", 0)
        failed_jobs = stats.get("failed", 0)
        suspended_jobs = stats.get("suspended", 0)
        
        # Actualizar batch
        update_data = {
            "total_jobs": total_jobs,
            "pending_jobs": pending_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "suspended_jobs": suspended_jobs,
            "total_cost": total_cost,
            "total_minutes": total_minutes,
        }
        
        # Marcar como completado si no hay jobs pendientes
        if pending_jobs == 0 and total_jobs > 0:
            update_data["completed_at"] = datetime.utcnow()
        
        result = await self.batches_collection.update_one(
            {"batch_id": batch_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            self.logger.info(f"Updated stats for batch {batch_id}: {total_jobs} total, {completed_jobs} completed")
        
        return result.modified_count > 0
    
    async def add_jobs_to_batch(self, batch_id: str, jobs: List[JobModel]) -> int:
        """Agrega jobs a un batch existente"""
        
        if not jobs:
            return 0
        
        # Verificar que el batch existe
        batch = await self.get_batch(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        # Agregar batch_id a todos los jobs
        for job in jobs:
            job.batch_id = batch_id
            job.created_at = datetime.utcnow()
        
        # Insertar jobs
        job_docs = [job.to_dict() for job in jobs]
        result = await self.jobs_collection.insert_many(job_docs)
        
        # Actualizar estadísticas del batch
        await self.update_batch_stats(batch_id)
        
        self.logger.info(f"Added {len(jobs)} jobs to batch {batch_id}")
        return len(result.inserted_ids)
    
    async def get_batch_jobs(
        self, 
        batch_id: str,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[JobModel]:
        """Obtiene jobs de un batch"""
        
        filters = {"batch_id": batch_id}
        if status:
            filters["status"] = status.value
        
        cursor = self.jobs_collection.find(filters).skip(skip).limit(limit)
        jobs = []
        
        async for doc in cursor:
            jobs.append(JobModel.from_dict(doc))
        
        return jobs
    
    async def pause_batch(self, batch_id: str) -> bool:
        """Pausa un batch (marca como inactivo)"""
        result = await self.batches_collection.update_one(
            {"batch_id": batch_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            self.logger.info(f"Paused batch {batch_id}")
        
        return result.modified_count > 0
    
    async def resume_batch(self, batch_id: str) -> bool:
        """Reanuda un batch pausado"""
        result = await self.batches_collection.update_one(
            {"batch_id": batch_id},
            {"$set": {"is_active": True, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            self.logger.info(f"Resumed batch {batch_id}")
        
        return result.modified_count > 0
    
    async def update_batch(self, batch_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Actualiza propiedades de un batch
        
        Args:
            batch_id: ID del batch a actualizar (puede ser batch_id o _id de MongoDB)
            update_data: Diccionario con los campos a actualizar
        
        Returns:
            True si se actualizó, False si no se encontró el batch
        """
        # Agregar timestamp de actualización
        update_data["updated_at"] = datetime.utcnow()
        
        # Usar filtro que acepta ambos formatos
        batch_filter = self._get_batch_filter(batch_id)
        
        result = await self.batches_collection.update_one(
            batch_filter,
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            self.logger.info(f"Updated batch {batch_id} with fields: {list(update_data.keys())}")
        
        return result.matched_count > 0
    
    async def cancel_batch(self, batch_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancela un batch completamente (diferente de pause)
        
        Diferencias:
        - pause: Temporal, se puede reanudar
        - cancel: Permanente, marca jobs pendientes como cancelled
        
        Args:
            batch_id: ID del batch
            reason: Razón de cancelación (opcional)
        """
        # 1. Marcar batch como inactivo
        update_data = {
            "is_active": False,
            "completed_at": datetime.utcnow()
        }
        
        # Agregar razón si se proporciona
        if reason:
            update_data["cancellation_reason"] = reason
        
        batch_result = await self.batches_collection.update_one(
            {"batch_id": batch_id},
            {"$set": update_data}
        )
        
        if batch_result.matched_count == 0:
            return False
        
        # 2. Cancelar todos los jobs pendientes
        jobs_result = await self.jobs_collection.update_many(
            {
                "batch_id": batch_id,
                "status": {"$in": [JobStatus.PENDING.value, JobStatus.SCHEDULED.value]}
            },
            {
                "$set": {
                    "status": JobStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow(),
                    "cancellation_reason": reason or "Batch cancelled"
                }
            }
        )
        
        # 3. Actualizar estadísticas del batch
        await self.update_batch_stats(batch_id)
        
        self.logger.info(
            f"Cancelled batch {batch_id}. "
            f"Jobs cancelled: {jobs_result.modified_count}. "
            f"Reason: {reason or 'Not specified'}"
        )
        
        return True
    
    async def delete_batch(self, batch_id: str, delete_jobs: bool = False) -> bool:
        """
        Elimina un batch y cancela o elimina sus jobs
        
        Args:
            batch_id: ID del batch a eliminar
            delete_jobs: Si True, elimina los jobs; si False, solo los cancela
        """
        
        if delete_jobs:
            # Eliminar todos los jobs del batch
            jobs_result = await self.jobs_collection.delete_many({"batch_id": batch_id})
            self.logger.info(f"Deleted {jobs_result.deleted_count} jobs from batch {batch_id}")
        else:
            # Cancelar jobs pendientes y en progreso (no eliminar completados/failed)
            jobs_result = await self.jobs_collection.update_many(
                {
                    "batch_id": batch_id,
                    "status": {"$in": [
                        JobStatus.PENDING.value, 
                        JobStatus.SCHEDULED.value,
                        JobStatus.IN_PROGRESS.value
                    ]}
                },
                {
                    "$set": {
                        "status": JobStatus.CANCELLED.value,
                        "updated_at": datetime.utcnow(),
                        "cancellation_reason": "Batch deleted"
                    }
                }
            )
            self.logger.info(f"Cancelled {jobs_result.modified_count} jobs from batch {batch_id}")
        
        # Eliminar el batch
        result = await self.batches_collection.delete_one({"batch_id": batch_id})
        
        if result.deleted_count > 0:
            self.logger.info(f"Deleted batch {batch_id}")
        
        return result.deleted_count > 0
    
    async def list_batches(
        self,
        account_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[BatchModel]:
        """Lista batches con filtros opcionales"""
        
        filters = {}
        if account_id:
            filters["account_id"] = account_id
        if is_active is not None:
            filters["is_active"] = is_active
        
        cursor = self.batches_collection.find(filters).sort("created_at", -1).skip(skip).limit(limit)
        batches = []
        
        async for doc in cursor:
            batches.append(BatchModel.from_dict(doc))
        
        return batches
    
    async def get_batch_summary(self, batch_id: str) -> Dict:
        """Obtiene resumen completo de un batch"""
        
        batch = await self.get_batch(batch_id)
        if not batch:
            return {"error": "Batch not found"}
        
        # Obtener estadísticas actualizadas
        await self.update_batch_stats(batch_id)
        batch = await self.get_batch(batch_id)  # Recargar después de actualizar
        
        # Resumen por hora (últimas 24 horas)
        pipeline = [
            {"$match": {"batch_id": batch_id, "completed_at": {"$exists": True}}},
            {"$group": {
                "_id": {
                    "hour": {"$hour": "$completed_at"},
                    "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$completed_at"}}
                },
                "count": {"$sum": 1},
                "success_count": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}
            }},
            {"$sort": {"_id.date": -1, "_id.hour": -1}},
            {"$limit": 24}
        ]
        
        hourly_cursor = self.jobs_collection.aggregate(pipeline)
        hourly_stats = []
        
        async for hour_stat in hourly_cursor:
            hourly_stats.append({
                "hour": hour_stat["_id"]["hour"],
                "date": hour_stat["_id"]["date"],
                "total_calls": hour_stat["count"],
                "successful_calls": hour_stat["success_count"],
                "success_rate": (hour_stat["success_count"] / hour_stat["count"] * 100) if hour_stat["count"] > 0 else 0
            })
        
        return {
            "batch_id": batch.batch_id,
            "name": batch.name,
            "account_id": batch.account_id,
            "status": "completed" if batch.is_completed else ("paused" if not batch.is_active else "active"),
            "total_jobs": batch.total_jobs,
            "pending_jobs": batch.pending_jobs,
            "completed_jobs": batch.completed_jobs,
            "failed_jobs": batch.failed_jobs,
            "suspended_jobs": batch.suspended_jobs,
            "completion_rate": batch.completion_rate,
            "total_cost": batch.total_cost,
            "total_minutes": batch.total_minutes,
            "priority": batch.priority,
            "created_at": batch.created_at,
            "started_at": batch.started_at,
            "completed_at": batch.completed_at,
            "hourly_stats": hourly_stats
        }