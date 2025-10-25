"""
Script para actualizar batches existentes agregando el campo is_active
Ejecutar una sola vez después de implementar la funcionalidad de pausar batches
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


async def update_batches_add_is_active():
    """Agrega el campo is_active a todos los batches que no lo tengan"""
    
    settings = get_settings()
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    
    try:
        await db_manager.connect()
        batches_collection = db_manager.get_collection("batches")
        
        logger.info("Iniciando actualización de batches...")
        
        # Contar batches sin el campo is_active
        count_without_field = await batches_collection.count_documents({
            "is_active": {"$exists": False}
        })
        
        logger.info(f"Encontrados {count_without_field} batches sin campo is_active")
        
        if count_without_field == 0:
            logger.info("Todos los batches ya tienen el campo is_active")
            return
        
        # Actualizar todos los batches sin el campo is_active
        result = await batches_collection.update_many(
            {"is_active": {"$exists": False}},
            {
                "$set": {
                    "is_active": True,  # Por defecto, todos los batches existentes están activos
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"✅ Actualizados {result.modified_count} batches")
        logger.info(f"Total batches procesados: {result.matched_count}")
        
        # Verificar resultado
        total_batches = await batches_collection.count_documents({})
        active_batches = await batches_collection.count_documents({"is_active": True})
        inactive_batches = await batches_collection.count_documents({"is_active": False})
        
        logger.info("\nEstadísticas finales:")
        logger.info(f"  Total batches: {total_batches}")
        logger.info(f"  Batches activos: {active_batches}")
        logger.info(f"  Batches pausados: {inactive_batches}")
        
    except Exception as e:
        logger.error(f"❌ Error actualizando batches: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(update_batches_add_is_active())
