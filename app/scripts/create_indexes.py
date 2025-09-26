"""
Script para crear índices únicos para anti-duplicación
Ejecutar una vez después de implementar el sistema
"""

import asyncio
import logging
import sys
import os

# Agregar la carpeta padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def clean_conflicting_indexes():
    """Limpia índices conflictivos si es necesario"""
    settings = get_settings()
    client = AsyncIOMotorClient(settings.database.uri)
    db = client[settings.database.database]
    
    try:
        logger.info("Verificando índices conflictivos en Debtors...")
        
        # Listar índices actuales
        indexes = await db.Debtors.list_indexes().to_list(None)
        
        for index in indexes:
            index_name = index.get('name')
            index_keys = index.get('key', {})
            
            # Si encontramos el índice automático 'key_1' que está causando conflicto
            if index_name == 'key_1' and 'key' in index_keys:
                logger.info(f"Encontrado índice conflictivo: {index_name}")
                logger.info("Este índice será utilizado en lugar de crear uno nuevo")
                
                # Verificar si es único
                is_unique = index.get('unique', False)
                if not is_unique:
                    logger.warning("El índice existente 'key_1' NO es único. Considerar recrearlo manualmente.")
                else:
                    logger.info("El índice existente 'key_1' es único. ✓")
        
        logger.info("Verificación de índices conflictivos completada")
        
    except Exception as e:
        logger.error(f"Error verificando índices: {e}")
        raise
    
    finally:
        client.close()


async def create_unique_indexes():
    """Crea índices únicos para prevenir duplicados"""
    settings = get_settings()
    client = AsyncIOMotorClient(settings.database.uri)
    db = client[settings.database.database]
    
    try:
        # Función helper para crear índice con manejo de duplicados
        async def create_index_safe(collection, index_spec, **kwargs):
            try:
                result = await collection.create_index(index_spec, **kwargs)
                logger.info(f"Índice creado: {kwargs.get('name', 'unnamed')} -> {result}")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.warning(f"Índice ya existe: {kwargs.get('name', 'unnamed')} - {e}")
                else:
                    raise
        
        # Índice único para jobs por deduplication_key
        logger.info("Creando índice único para jobs.deduplication_key")
        await create_index_safe(
            db.call_jobs,
            "deduplication_key",
            unique=True,
            sparse=True,  # Permite documentos sin este campo
            name="idx_deduplication_key_unique"
        )
        
        # Índice único para deudores por key (batch_id::rut)
        logger.info("Creando índice único para debtors.key")
        await create_index_safe(
            db.Debtors,
            "key",
            unique=True,
            name="idx_debtor_key_unique"
        )
        
        # Índice único para batches por batch_id
        logger.info("Creando índice único para batches.batch_id")
        await create_index_safe(
            db.batches,
            "batch_id",
            unique=True,
            name="idx_batch_id_unique"
        )
        
        # Índice compuesto para búsquedas por cuenta y RUT
        logger.info("Creando índice compuesto para account_id + rut")
        await create_index_safe(
            db.Debtors,
            [("account_id", 1), ("rut", 1)],
            name="idx_account_rut"
        )
        
        # Índice para búsquedas de jobs por cuenta y estado
        logger.info("Creando índice compuesto para jobs por account_id + status")
        await create_index_safe(
            db.call_jobs,
            [("account_id", 1), ("status", 1), ("created_at", -1)],
            name="idx_account_status_created"
        )
        
        # Índice para búsquedas de jobs por batch
        logger.info("Creando índice para jobs por batch_id")
        await create_index_safe(
            db.call_jobs,
            [("batch_id", 1), ("status", 1)],
            name="idx_batch_status"
        )
        
        logger.info("Proceso de creación de índices completado")
        
    except Exception as e:
        logger.error(f"Error creando índices: {e}")
        raise
    
    finally:
        client.close()


async def verify_indexes():
    """Verifica que los índices estén creados correctamente"""
    settings = get_settings()
    client = AsyncIOMotorClient(settings.database.uri)
    db = client[settings.database.database]
    
    try:
        # Verificar índices de jobs
        logger.info("Verificando índices de call_jobs...")
        indexes = await db.call_jobs.list_indexes().to_list(None)
        for index in indexes:
            logger.info(f"  - {index['name']}: {index.get('key', {})}")
        
        # Verificar índices de debtors
        logger.info("Verificando índices de Debtors...")
        indexes = await db.Debtors.list_indexes().to_list(None)
        for index in indexes:
            logger.info(f"  - {index['name']}: {index.get('key', {})}")
        
        # Verificar índices de batches
        logger.info("Verificando índices de batches...")
        indexes = await db.batches.list_indexes().to_list(None)
        for index in indexes:
            logger.info(f"  - {index['name']}: {index.get('key', {})}")
        
    except Exception as e:
        logger.error(f"Error verificando índices: {e}")
        raise
    
    finally:
        client.close()


if __name__ == "__main__":
    print("Verificando índices conflictivos...")
    asyncio.run(clean_conflicting_indexes())
    
    print("\nCreando índices para anti-duplicación...")
    asyncio.run(create_unique_indexes())
    
    print("\nVerificando índices creados...")
    asyncio.run(verify_indexes())
    
    print("\n¡Índices configurados exitosamente! El sistema de anti-duplicación está listo.")