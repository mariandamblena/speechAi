"""
Script para cancelar jobs pendientes de batches pausados o eliminados
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Agregar el directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings
from domain.enums import JobStatus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def cancel_jobs_from_inactive_batches():
    """Cancela jobs pendientes de batches pausados o que no existen"""
    
    settings = get_settings()
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    
    try:
        await db_manager.connect()
        batches_collection = db_manager.get_collection("batches")
        jobs_collection = db_manager.get_collection("jobs")
        
        logger.info("Iniciando cancelación de jobs de batches inactivos...")
        
        # 1. Obtener IDs de batches activos
        active_batches_cursor = batches_collection.find(
            {"is_active": True},
            {"batch_id": 1}
        )
        active_batch_ids = [batch["batch_id"] async for batch in active_batches_cursor]
        
        logger.info(f"Batches activos encontrados: {len(active_batch_ids)}")
        
        # 2. Contar jobs pendientes de batches inactivos
        pending_statuses = [
            JobStatus.PENDING.value,
            JobStatus.SCHEDULED.value,
            JobStatus.IN_PROGRESS.value
        ]
        
        count_to_cancel = await jobs_collection.count_documents({
            "batch_id": {"$exists": True, "$ne": None},
            "batch_id": {"$nin": active_batch_ids},
            "status": {"$in": pending_statuses}
        })
        
        logger.info(f"Jobs pendientes de batches inactivos: {count_to_cancel}")
        
        if count_to_cancel == 0:
            logger.info("No hay jobs para cancelar")
            return
        
        # 3. Cancelar jobs
        result = await jobs_collection.update_many(
            {
                "batch_id": {"$exists": True, "$ne": None},
                "batch_id": {"$nin": active_batch_ids},
                "status": {"$in": pending_statuses}
            },
            {
                "$set": {
                    "status": JobStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow(),
                    "cancellation_reason": "Batch is paused or deleted"
                }
            }
        )
        
        logger.info(f"✅ Cancelados {result.modified_count} jobs")
        
        # 4. Mostrar estadísticas por batch
        pipeline = [
            {
                "$match": {
                    "status": JobStatus.CANCELLED.value,
                    "cancellation_reason": "Batch is paused or deleted"
                }
            },
            {
                "$group": {
                    "_id": "$batch_id",
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"count": -1}
            }
        ]
        
        stats_cursor = jobs_collection.aggregate(pipeline)
        
        logger.info("\nJobs cancelados por batch:")
        async for stat in stats_cursor:
            logger.info(f"  {stat['_id']}: {stat['count']} jobs")
        
    except Exception as e:
        logger.error(f"❌ Error cancelando jobs: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(cancel_jobs_from_inactive_batches())
