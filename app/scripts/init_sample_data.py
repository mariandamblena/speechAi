"""
Script para inicializar datos de ejemplo en el sistema
Crea cuentas, batches, jobs y transacciones de prueba
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
from datetime import datetime, timedelta
from config.settings import get_settings
from infrastructure.database_manager import DatabaseManager
from services.account_service import AccountService
from services.batch_service import BatchService
from services.job_service import JobService
from services.transaction_service import TransactionService
from domain.enums import PlanType, TransactionType, JobStatus
from domain.models import ContactInfo, CallPayload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_sample_data():
    """Crea datos de ejemplo para desarrollo"""
    
    # Conectar a base de datos
    settings = get_settings()
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    await db_manager.connect()
    
    # Servicios
    account_service = AccountService(db_manager)
    batch_service = BatchService(db_manager)
    job_service = JobService(db_manager)
    transaction_service = TransactionService(db_manager)
    
    logger.info("🚀 Creando datos de ejemplo...")
    
    # 1. Crear cuentas de ejemplo
    sample_accounts = [
        {
            "account_id": "strasing",
            "account_name": "Strasing Corp",
            "plan_type": PlanType.CREDIT_BASED,
            "initial_credits": 1500.0
        },
        {
            "account_id": "fintech_solutions",
            "account_name": "Fintech Solutions Ltda.",
            "plan_type": PlanType.MINUTES_BASED,
            "initial_minutes": 850.0
        },
        {
            "account_id": "retail_express",
            "account_name": "Retail Express Corp",
            "plan_type": PlanType.CREDIT_BASED,
            "initial_credits": 50.0
        }
    ]
    
    for account_data in sample_accounts:
        try:
            # Verificar si ya existe
            existing = await account_service.get_account(account_data["account_id"])
            if existing:
                logger.info(f"✅ Cuenta {account_data['account_id']} ya existe")
                continue
                
            account = await account_service.create_account(**account_data)
            logger.info(f"✅ Creada cuenta: {account.account_name}")
            
            # Crear transacciones de ejemplo para cada cuenta
            await create_sample_transactions(transaction_service, account.account_id, account.plan_type)
            
        except Exception as e:
            logger.error(f"❌ Error creando cuenta {account_data['account_id']}: {e}")
    
    # 2. Crear batches de ejemplo
    sample_batches = [
        {
            "account_id": "strasing",
            "name": "Basic Batch 2025-10-03 16:49",
            "description": "Importado desde Excel con 12 deudores"
        },
        {
            "account_id": "strasing", 
            "name": "recaudando plata",
            "description": "la primera muestra"
        },
        {
            "account_id": "strasing",
            "name": "Prueba_100_llamadas",
            "description": "lote de 100 llamadas"
        }
    ]
    
    for batch_data in sample_batches:
        try:
            batch = await batch_service.create_batch(**batch_data)
            logger.info(f"✅ Creado batch: {batch.name}")
            
            # Crear algunos jobs de ejemplo para cada batch
            await create_sample_jobs(job_service, batch.batch_id, batch.account_id)
            
        except Exception as e:
            logger.error(f"❌ Error creando batch {batch_data['name']}: {e}")
    
    await db_manager.close()
    logger.info("🎉 Datos de ejemplo creados exitosamente!")

async def create_sample_transactions(transaction_service, account_id, plan_type):
    """Crea transacciones de ejemplo para una cuenta"""
    
    # Fechas de ejemplo (últimos 30 días)
    now = datetime.utcnow()
    dates = [
        now - timedelta(days=25),  # Recarga inicial
        now - timedelta(days=20),  # Uso campaña 1
        now - timedelta(days=15),  # Bono promocional
        now - timedelta(days=10),  # Uso campaña 2
        now - timedelta(days=5),   # Recarga adicional
        now - timedelta(days=2),   # Uso reciente
    ]
    
    if plan_type == PlanType.CREDIT_BASED:
        # Transacciones para cuenta basada en créditos
        transactions = [
            {
                "type": TransactionType.TOPUP_CREDITS,
                "amount": 1000.0,
                "cost": 50000,  # $500.00
                "description": "Recarga plan mensual - 1000 créditos",
                "created_at": dates[0]
            },
            {
                "type": TransactionType.CALL_USAGE,
                "amount": -180.0,
                "cost": 9000,  # $90.00
                "description": "Uso en campaña: Basic Batch 2025-10-03",
                "created_at": dates[1]
            },
            {
                "type": TransactionType.BONUS,
                "amount": 500.0,
                "cost": 0,
                "description": "Bono por renovación - Cliente premium",
                "created_at": dates[2]
            },
            {
                "type": TransactionType.CALL_USAGE,
                "amount": -240.0,
                "cost": 12000,  # $120.00
                "description": "Uso en campaña: recaudando plata",
                "created_at": dates[3]
            },
            {
                "type": TransactionType.TOPUP_CREDITS,
                "amount": 500.0,
                "cost": 25000,  # $250.00
                "description": "Recarga adicional - 500 créditos",
                "created_at": dates[4]
            },
            {
                "type": TransactionType.CALL_USAGE,
                "amount": -80.0,
                "cost": 4000,  # $40.00
                "description": "Uso en campaña: Prueba_100_llamadas",
                "created_at": dates[5]
            }
        ]
    else:
        # Transacciones para cuenta basada en minutos
        transactions = [
            {
                "type": TransactionType.TOPUP_MINUTES,
                "amount": 600.0,
                "cost": 30000,  # $300.00
                "description": "Recarga plan mensual - 600 minutos",
                "created_at": dates[0]
            },
            {
                "type": TransactionType.CALL_USAGE,
                "amount": -45.5,
                "cost": 2275,  # $22.75
                "description": "Uso en campaña: Cobranza Fintech Q1",
                "created_at": dates[1]
            },
            {
                "type": TransactionType.BONUS,
                "amount": 250.0,
                "cost": 0,
                "description": "Bono por loyalty program",
                "created_at": dates[2]
            },
            {
                "type": TransactionType.TOPUP_MINUTES,
                "amount": 300.0,
                "cost": 15000,  # $150.00
                "description": "Recarga adicional - 300 minutos",
                "created_at": dates[4]
            }
        ]
    
    for txn_data in transactions:
        try:
            # Crear transacción con fecha específica
            transaction = await transaction_service.create_transaction(
                account_id=account_id,
                transaction_type=txn_data["type"],
                amount=txn_data["amount"],
                cost=txn_data["cost"],
                description=txn_data["description"]
            )
            
            # Actualizar fecha manualmente (para simular histórico)
            await transaction_service.transactions_collection.update_one(
                {"transaction_id": transaction.transaction_id},
                {"$set": {"created_at": txn_data["created_at"]}}
            )
            
        except Exception as e:
            logger.error(f"Error creando transacción: {e}")

async def create_sample_jobs(job_service, batch_id, account_id):
    """Crea jobs de ejemplo para un batch"""
    
    # Datos de contactos de ejemplo
    sample_contacts = [
        {
            "name": "MAGALY IVETTE MORALES IVETTE MORALES TAPIA",
            "dni": "12345678",
            "phones": ["+56992125907", "+56987654321"]
        },
        {
            "name": "Carol Espinoza Chandia", 
            "dni": "87654321",
            "phones": ["+56998765432"]
        },
        {
            "name": "Marcela Alejandra Neira Obreque",
            "dni": "11223344",
            "phones": ["+56991234567", "+56987654321"]
        },
        {
            "name": "CAROLA BELEN ORELLANA SANDOVAL",
            "dni": "44332211",
            "phones": ["+56995555555"]
        },
        {
            "name": "ISABEL ALEJANDRA GALLEGUILLOS AGUILAR",
            "dni": "55667788",
            "phones": ["+56996666666"]
        }
    ]
    
    # Estados variados para simular progreso
    statuses = [JobStatus.FAILED, JobStatus.FAILED, JobStatus.FAILED, JobStatus.COMPLETED, JobStatus.FAILED]
    attempts = [3, 3, 3, 1, 3]
    
    for i, contact_data in enumerate(sample_contacts):
        try:
            contact = ContactInfo(**contact_data)
            
            payload = CallPayload(
                debt_amount=150000 + (i * 25000),
                due_date="2025-02-15",
                company_name="Banco Chile",
                reference_number=f"REF{123456 + i}",
                additional_info={
                    "cantidad_cupones": 3,
                    "fecha_maxima": "2025-03-01"
                }
            )
            
            # Crear job usando JobService directamente
            job_dict = {
                "account_id": account_id,
                "batch_id": batch_id,
                "contact": contact.to_dict(),
                "payload": payload.to_dict(),
                "status": statuses[i].value,
                "attempts": attempts[i],
                "max_attempts": 3,
                "created_at": datetime.utcnow(),
                "estimated_cost": 2.5
            }
            
            await job_service.jobs_collection.insert_one(job_dict)
            
        except Exception as e:
            logger.error(f"Error creando job: {e}")

if __name__ == "__main__":
    asyncio.run(create_sample_data())