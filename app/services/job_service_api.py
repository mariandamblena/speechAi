"""
Servicio para manejo de jobs de llamadas (API Version)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from domain.models import JobModel
from domain.enums import JobStatus
from infrastructure.database_manager import DatabaseManager


class JobService:
    """
    Servicio para manejo de jobs para API REST
    
    Proporciona métodos para:
    - Listado y filtrado de jobs
    - Estadísticas y reportes
    - Operaciones administrativas
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.jobs_collection = db_manager.get_collection("call_jobs")
        self.logger = logging.getLogger(__name__)
    
    async def list_jobs(
        self,
        account_id: Optional[str] = None,
        batch_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[JobModel]:
        """Lista jobs con filtros opcionales"""
        
        filters = {}
        if account_id:
            filters["account_id"] = account_id
        if batch_id:
            filters["batch_id"] = batch_id
        if status:
            filters["status"] = status.value
        
        cursor = self.jobs_collection.find(filters).sort("created_at", -1).skip(skip).limit(limit)
        jobs = []
        
        async for doc in cursor:
            jobs.append(JobModel.from_dict(doc))
        
        return jobs
    
    async def get_job(self, job_id: str) -> Optional[JobModel]:
        """Obtiene un job específico por ID"""
        try:
            object_id = ObjectId(job_id)
            data = await self.jobs_collection.find_one({"_id": object_id})
            if data:
                return JobModel.from_dict(data)
        except Exception as e:
            self.logger.error(f"Error getting job {job_id}: {e}")
        return None
    
    async def retry_job(self, job_id: str) -> bool:
        """Marca un job para reintento manual"""
        try:
            object_id = ObjectId(job_id)
            
            result = await self.jobs_collection.update_one(
                {
                    "_id": object_id,
                    "status": {"$in": ["failed", "suspended"]}
                },
                {
                    "$set": {
                        "status": "pending",
                        "attempts": 0,
                        "updated_at": datetime.utcnow(),
                        "worker_id": None,
                        "reserved_until": None,
                        "last_error": None
                    }
                }
            )
            
            if result.modified_count > 0:
                self.logger.info(f"Job {job_id} marked for retry")
                return True
                
        except Exception as e:
            self.logger.error(f"Error retrying job {job_id}: {e}")
        
        return False
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancela un job pendiente"""
        try:
            object_id = ObjectId(job_id)
            
            result = await self.jobs_collection.update_one(
                {
                    "_id": object_id,
                    "status": "pending"
                },
                {
                    "$set": {
                        "status": "failed",
                        "last_error": "Cancelled by user",
                        "failed_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                self.logger.info(f"Job {job_id} cancelled")
                return True
                
        except Exception as e:
            self.logger.error(f"Error cancelling job {job_id}: {e}")
        
        return False
    
    async def get_account_job_stats(self, account_id: str) -> Dict[str, Any]:
        """Obtiene estadísticas de jobs para una cuenta"""
        
        # Agregación para obtener estadísticas
        pipeline = [
            {"$match": {"account_id": account_id}},
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
        stats_by_status = {}
        total_cost = 0
        total_minutes = 0
        
        async for stat in stats_cursor:
            status = stat["_id"]
            count = stat["count"]
            stats_by_status[status] = count
            total_cost += stat.get("total_cost", 0) / 100  # Convertir de centavos
            total_minutes += stat.get("total_minutes", 0)
        
        # Estadísticas de hoy
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_pipeline = [
            {"$match": {
                "account_id": account_id,
                "created_at": {"$gte": today_start}
            }},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        today_cursor = self.jobs_collection.aggregate(today_pipeline)
        today_stats = {}
        
        async for stat in today_cursor:
            today_stats[stat["_id"]] = stat["count"]
        
        return {
            "total_jobs": sum(stats_by_status.values()),
            "by_status": stats_by_status,
            "total_cost": total_cost,
            "total_minutes": total_minutes,
            "today": today_stats,
            "success_rate": (
                (stats_by_status.get("completed", 0) / sum(stats_by_status.values()) * 100)
                if sum(stats_by_status.values()) > 0 else 0
            )
        }
    
    async def get_call_history(
        self, 
        filters: Dict[str, Any], 
        limit: int = 100, 
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Obtiene historial de llamadas completadas"""
        
        # Agregar filtro para solo llamadas completadas
        filters["status"] = {"$in": ["completed", "failed"]}
        filters["call_result"] = {"$exists": True}
        
        cursor = self.jobs_collection.find(
            filters,
            {
                "contact.name": 1,
                "contact.dni": 1,
                "call_result": 1,
                "completed_at": 1,
                "failed_at": 1,
                "status": 1,
                "batch_id": 1,
                "attempts": 1
            }
        ).sort("completed_at", -1).skip(skip).limit(limit)
        
        history = []
        async for doc in cursor:
            call_data = doc.get("call_result", {})
            
            history_entry = {
                "job_id": str(doc["_id"]),
                "contact_name": doc.get("contact", {}).get("name", ""),
                "contact_dni": doc.get("contact", {}).get("dni", ""),
                "batch_id": doc.get("batch_id"),
                "status": doc.get("status"),
                "attempts": doc.get("attempts", 0),
                "completed_at": doc.get("completed_at"),
                "failed_at": doc.get("failed_at"),
                "call_status": call_data.get("call_status"),
                "duration_ms": call_data.get("duration_ms", 0),
                "cost": call_data.get("call_cost", {}).get("combined_cost", 0) / 100,
                "disconnect_reason": call_data.get("disconnect_reason")
            }
            
            history.append(history_entry)
        
        return history