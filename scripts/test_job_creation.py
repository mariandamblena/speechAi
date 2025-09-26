#!/usr/bin/env python3
"""
Script para probar la creación de jobs desde Excel sin la API
Simula el flujo completo: Excel → Batch → Jobs
"""

import asyncio
import sys
import os
from datetime import datetime
import logging

# Agregar el directorio app al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

async def test_job_creation():
    """Prueba la creación de jobs desde Excel"""
    try:
        # Imports después de configurar el path
        from infrastructure.database_manager import DatabaseManager
        from services.batch_creation_service import BatchCreationService
        from config.settings import get_settings
        
        logger.info("=== INICIANDO PRUEBA DE CREACIÓN DE JOBS ===")
        
        # 1. Configurar conexión a DB
        settings = get_settings()
        db_manager = DatabaseManager(settings.database.uri, settings.database.database)
        await db_manager.connect()
        
        logger.info(f"Conectado a MongoDB: {settings.database.database}")
        
        # 2. Crear servicio
        batch_service = BatchCreationService(db_manager)
        
        # 3. Verificar si hay archivos Excel en el directorio
        excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx') or f.endswith('.xls')]
        if not excel_files:
            logger.error("No se encontraron archivos Excel (.xlsx/.xls) en el directorio actual")
            logger.info("Coloque un archivo Excel con datos de deudores en el directorio raíz")
            return
        
        excel_file = excel_files[0]  # Usar el primero que encuentre
        logger.info(f"Usando archivo Excel: {excel_file}")
        
        # 4. Leer archivo Excel
        with open(excel_file, 'rb') as f:
            file_content = f.read()
        
        # 5. Probar previsualización primero
        logger.info("--- PRUEBA DE PREVISUALIZACIÓN ---")
        preview = await batch_service.get_batch_preview(file_content, "test-account")
        
        if preview['success']:
            logger.info(f"Previsualización exitosa:")
            logger.info(f"  - Filas totales: {preview['preview']['total_rows']}")
            logger.info(f"  - Deudores válidos: {preview['preview']['valid_debtors']}")
            logger.info(f"  - Con teléfono: {preview['preview']['with_valid_phone']}")
            logger.info(f"  - Sin teléfono: {preview['preview']['without_phone']}")
            logger.info(f"  - Monto total: ${preview['preview']['total_debt_amount']:,.2f}")
            logger.info(f"  - Duplicados: {preview['preview']['duplicates_found']}")
        else:
            logger.error(f"Error en previsualización: {preview['error']}")
            return
        
        # 6. Crear cuenta de prueba si no existe
        logger.info("--- VERIFICANDO CUENTA DE PRUEBA ---")
        from services.account_service import AccountService
        account_service = AccountService(db_manager)
        
        account = await account_service.get_account("test-account")
        if not account:
            logger.info("Creando cuenta de prueba...")
            from domain.models import AccountModel
            from domain.enums import PlanType
            
            account = AccountModel(
                account_id="test-account",
                name="Cuenta de Prueba",
                plan_type=PlanType.UNLIMITED,
                credit_balance=1000.0,
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            await account_service.create_account(account)
            logger.info("Cuenta de prueba creada")
        else:
            logger.info("Cuenta de prueba ya existe")
        
        # 7. Crear batch completo
        logger.info("--- CREANDO BATCH COMPLETO CON JOBS ---")
        result = await batch_service.create_batch_from_excel(
            file_content=file_content,
            account_id="test-account",
            batch_name=f"Prueba Excel {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            batch_description="Batch de prueba para verificar creación de jobs",
            allow_duplicates=False
        )
        
        if result['success']:
            logger.info(f"✅ BATCH CREADO EXITOSAMENTE:")
            logger.info(f"  - Batch ID: {result['batch_id']}")
            logger.info(f"  - Nombre: {result['batch_name']}")
            logger.info(f"  - Deudores: {result['total_debtors']}")
            logger.info(f"  - Jobs: {result['total_jobs']}")
            logger.info(f"  - Costo estimado: ${result['estimated_cost']:,.2f}")
            logger.info(f"  - Duplicados: {result['duplicates_found']}")
            
            # 8. Verificar jobs en DB
            logger.info("--- VERIFICANDO JOBS EN BASE DE DATOS ---")
            jobs_collection = db_manager.get_collection("jobs")
            jobs = await jobs_collection.find({"batch_id": result['batch_id']}).to_list(None)
            
            logger.info(f"Jobs encontrados en DB: {len(jobs)}")
            
            if jobs:
                for i, job in enumerate(jobs[:3], 1):  # Mostrar primeros 3
                    contact = job.get('contact', {})
                    logger.info(f"  {i}. Job ID: {job.get('job_id', 'N/A')}")
                    logger.info(f"     RUT: {contact.get('dni', 'N/A')}")
                    logger.info(f"     Nombre: {contact.get('name', 'N/A')}")
                    logger.info(f"     Status: {job.get('status', 'N/A')}")
                    logger.info(f"     Dedup Key: {job.get('deduplication_key', 'N/A')}")
                    logger.info("")
                
                logger.info("🎉 JOBS CREADOS EXITOSAMENTE!")
            else:
                logger.error("❌ NO SE ENCONTRARON JOBS EN LA BASE DE DATOS!")
                
                # Verificar si se creó el batch
                batches_collection = db_manager.get_collection("batches")
                batch = await batches_collection.find_one({"batch_id": result['batch_id']})
                if batch:
                    logger.info("El batch sí fue creado, problema específico con jobs")
                else:
                    logger.error("Tampoco se creó el batch!")
        
        else:
            logger.error(f"❌ ERROR CREANDO BATCH: {result['error']}")
        
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Error en la prueba: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Iniciando prueba de creación de jobs desde Excel...")
    asyncio.run(test_job_creation())