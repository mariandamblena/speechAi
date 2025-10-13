"""
Script para probar los endpoints implementados
"""

import asyncio
import logging
from config.settings import get_settings
from infrastructure.database_manager import DatabaseManager
from services.account_service import AccountService
from services.batch_service import BatchService
from services.job_service import JobService
from services.transaction_service import TransactionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_endpoints():
    """Prueba los endpoints implementados"""
    
    # Conectar a base de datos
    settings = get_settings()
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    await db_manager.connect()
    
    # Servicios
    account_service = AccountService(db_manager)
    batch_service = BatchService(db_manager)
    job_service = JobService(db_manager)
    transaction_service = TransactionService(db_manager)
    
    logger.info("🧪 Probando endpoints implementados...")
    
    # 1. Test GET /api/v1/accounts
    logger.info("1️⃣ Probando GET /api/v1/accounts")
    accounts = await account_service.list_accounts(limit=5)
    logger.info(f"   ✅ Encontradas {len(accounts)} cuentas")
    
    if accounts:
        test_account_id = accounts[0].account_id
        logger.info(f"   📋 Usando cuenta de prueba: {test_account_id}")
        
        # 2. Test GET /api/v1/accounts/{account_id}/batches
        logger.info("2️⃣ Probando GET /api/v1/accounts/{account_id}/batches")
        batches = await batch_service.list_batches(account_id=test_account_id, limit=5)
        logger.info(f"   ✅ Encontrados {len(batches)} batches para la cuenta")
        
        # 3. Test GET /api/v1/accounts/{account_id}/transactions
        logger.info("3️⃣ Probando GET /api/v1/accounts/{account_id}/transactions")
        transactions = await transaction_service.get_account_transactions(test_account_id, limit=5)
        logger.info(f"   ✅ Encontradas {len(transactions)} transacciones para la cuenta")
        
        if batches:
            test_batch_id = batches[0].batch_id
            logger.info(f"   📋 Usando batch de prueba: {test_batch_id}")
            
            # 4. Test GET /api/v1/batches/{batch_id}/jobs
            logger.info("4️⃣ Probando GET /api/v1/batches/{batch_id}/jobs")
            jobs = await job_service.list_jobs(batch_id=test_batch_id, limit=5)
            logger.info(f"   ✅ Encontrados {len(jobs)} jobs para el batch")
        else:
            logger.warning("   ⚠️ No hay batches para probar jobs")
    else:
        logger.warning("   ⚠️ No hay cuentas en la base de datos")
        logger.info("   💡 Ejecuta 'python scripts/init_sample_data.py' para crear datos de ejemplo")
    
    await db_manager.close()
    logger.info("🎉 Prueba de endpoints completada!")

if __name__ == "__main__":
    asyncio.run(test_endpoints())