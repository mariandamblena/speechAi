#!/usr/bin/env python3
"""
Script para analizar discrepancias entre deudores y jobs
Diagnostica por qué puede haber diferencias en las cantidades
"""

import asyncio
import sys
import os
from datetime import datetime
import logging
from collections import Counter

# Agregar el directorio app al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

async def analyze_batch_discrepancies(batch_id: str):
    """Analiza discrepancias en un batch específico"""
    try:
        from infrastructure.database_manager import DatabaseManager
        from config.settings import get_settings
        
        logger.info(f"=== ANÁLISIS DE DISCREPANCIAS PARA BATCH {batch_id} ===")
        
        # Conectar a DB
        settings = get_settings()
        db_manager = DatabaseManager(settings.database.uri, settings.database.database)
        await db_manager.connect()
        
        # 1. ANALIZAR EL BATCH
        logger.info("1. Analizando información del batch...")
        batch_collection = db_manager.get_collection("batches")
        batch = await batch_collection.find_one({"batch_id": batch_id})
        
        if not batch:
            logger.error(f"Batch {batch_id} no encontrado!")
            return
        
        logger.info(f"📦 Batch Info:")
        logger.info(f"  - Nombre: {batch.get('name', 'N/A')}")
        logger.info(f"  - Total jobs (según batch): {batch.get('total_jobs', 0)}")
        logger.info(f"  - Pending jobs: {batch.get('pending_jobs', 0)}")
        logger.info(f"  - Account: {batch.get('account_id', 'N/A')}")
        logger.info(f"  - Creado: {batch.get('created_at', 'N/A')}")
        
        # 2. CONTAR DEUDORES REALES
        logger.info("\n2. Contando deudores en colección 'Debtors'...")
        debtors_collection = db_manager.get_collection("Debtors")
        debtors = await debtors_collection.find({"batch_id": batch_id}).to_list(None)
        
        logger.info(f"👤 Deudores encontrados: {len(debtors)}")
        
        if debtors:
            # Analizar deudores
            with_phone = 0
            without_phone = 0
            phone_types = Counter()
            
            for debtor in debtors[:10]:  # Muestra de 10
                to_number = debtor.get('to_number')
                if to_number:
                    with_phone += 1
                    if to_number.startswith('+569'):
                        phone_types['mobile'] += 1
                    elif to_number.startswith('+562'):
                        phone_types['landline'] += 1
                    else:
                        phone_types['other'] += 1
                else:
                    without_phone += 1
                    logger.warning(f"  Deudor sin teléfono: RUT={debtor.get('rut', 'N/A')}, Nombre={debtor.get('nombre', 'N/A')}")
            
            logger.info(f"  - Con teléfono válido: {with_phone}/{min(len(debtors), 10)} (muestra)")
            logger.info(f"  - Sin teléfono: {without_phone}/{min(len(debtors), 10)} (muestra)")
            logger.info(f"  - Tipos teléfono: {dict(phone_types)}")
        
        # 3. CONTAR JOBS REALES
        logger.info("\n3. Contando jobs en colección 'call_jobs'...")
        jobs_collection = db_manager.get_collection("call_jobs")
        jobs = await jobs_collection.find({"batch_id": batch_id}).to_list(None)
        
        logger.info(f"📞 Jobs encontrados: {len(jobs)}")
        
        if jobs:
            # Analizar jobs
            status_counts = Counter()
            dedup_keys = set()
            duplicate_keys = []
            ruts_in_jobs = set()
            
            for job in jobs:
                # Contar por status
                status = job.get('status', 'unknown')
                status_counts[status] += 1
                
                # Verificar claves de deduplicación duplicadas
                dedup_key = job.get('deduplication_key')
                if dedup_key:
                    if dedup_key in dedup_keys:
                        duplicate_keys.append(dedup_key)
                    else:
                        dedup_keys.add(dedup_key)
                
                # Contar RUTs únicos
                contact = job.get('contact', {})
                rut = contact.get('dni') if contact else None
                if rut:
                    ruts_in_jobs.add(rut)
            
            logger.info(f"  - Status distribution: {dict(status_counts)}")
            logger.info(f"  - RUTs únicos en jobs: {len(ruts_in_jobs)}")
            logger.info(f"  - Claves deduplicación duplicadas: {len(duplicate_keys)}")
            
            if duplicate_keys:
                logger.warning(f"  - Ejemplos claves duplicadas: {duplicate_keys[:3]}")
        
        # 4. COMPARAR RUTS
        logger.info("\n4. Comparando RUTs entre deudores y jobs...")
        ruts_in_debtors = {debtor.get('rut') for debtor in debtors if debtor.get('rut')}
        
        logger.info(f"  - RUTs únicos en deudores: {len(ruts_in_debtors)}")
        logger.info(f"  - RUTs únicos en jobs: {len(ruts_in_jobs) if jobs else 0}")
        
        if jobs and debtors:
            missing_in_jobs = ruts_in_debtors - ruts_in_jobs
            extra_in_jobs = ruts_in_jobs - ruts_in_debtors
            
            logger.info(f"  - RUTs en deudores pero NO en jobs: {len(missing_in_jobs)}")
            logger.info(f"  - RUTs en jobs pero NO en deudores: {len(extra_in_jobs)}")
            
            if missing_in_jobs:
                logger.warning("  - Ejemplos RUTs faltantes en jobs:")
                for rut in list(missing_in_jobs)[:5]:
                    debtor = next((d for d in debtors if d.get('rut') == rut), None)
                    if debtor:
                        logger.warning(f"    * RUT: {rut}, Nombre: {debtor.get('nombre', 'N/A')}, Tel: {debtor.get('to_number', 'N/A')}")
        
        # 5. RESUMEN Y DIAGNÓSTICO
        logger.info("\n5. DIAGNÓSTICO FINAL:")
        logger.info("="*60)
        
        debtors_count = len(debtors)
        jobs_count = len(jobs) if jobs else 0
        
        if jobs_count < debtors_count:
            logger.warning(f"⚠️  MENOS JOBS QUE DEUDORES: {jobs_count} < {debtors_count}")
            logger.warning("   Posibles causas:")
            logger.warning("   - Deudores sin teléfono válido (se saltan)")
            logger.warning("   - Errores durante creación de jobs")
            logger.warning("   - Problemas de validación de datos")
            
        elif jobs_count > debtors_count:
            logger.warning(f"⚠️  MÁS JOBS QUE DEUDORES: {jobs_count} > {debtors_count}")
            logger.warning("   Posibles causas:")
            logger.warning("   - Claves de deduplicación duplicadas")
            logger.warning("   - Múltiples ejecuciones del mismo batch")
            logger.warning("   - Logic error en anti-duplicación")
            
        else:
            logger.info(f"✅ CANTIDADES COINCIDEN: {jobs_count} = {debtors_count}")
        
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Error en análisis: {str(e)}")
        import traceback
        traceback.print_exc()

async def find_recent_batch():
    """Encuentra el batch más reciente para análisis"""
    try:
        from infrastructure.database_manager import DatabaseManager
        from config.settings import get_settings
        
        settings = get_settings()
        db_manager = DatabaseManager(settings.database.uri, settings.database.database)
        await db_manager.connect()
        
        batch_collection = db_manager.get_collection("batches")
        recent_batch = await batch_collection.find().sort("created_at", -1).limit(1).to_list(1)
        
        if recent_batch:
            batch_id = recent_batch[0]['batch_id']
            logger.info(f"Batch más reciente encontrado: {batch_id}")
            await db_manager.close()
            return batch_id
        
        await db_manager.close()
        return None
        
    except Exception as e:
        logger.error(f"Error buscando batch: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        batch_id = sys.argv[1]
    else:
        logger.info("Buscando el batch más reciente...")
        batch_id = asyncio.run(find_recent_batch())
        
        if not batch_id:
            logger.error("No se encontró ningún batch. Especifica un batch_id como argumento.")
            sys.exit(1)
    
    asyncio.run(analyze_batch_discrepancies(batch_id))