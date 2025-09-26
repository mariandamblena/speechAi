"""
Script de prueba para la funcionalidad de creación de batches desde Excel
"""

import asyncio
import io
import pandas as pd
from datetime import datetime
import logging
import sys
import os

# Agregar la carpeta padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database_manager import DatabaseManager
from services.batch_creation_service import BatchCreationService
from services.account_service import AccountService
from config.settings import get_settings
from domain.enums import PlanType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_excel() -> bytes:
    """Crea un archivo Excel de muestra con datos de prueba únicos"""
    # Generar datos únicos basados en timestamp
    unique_suffix = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:17]  # YMD_HMS_microsec
    
    data = [
        {
            'RUT': f'12.345.{unique_suffix[-3:]}-9',
            'Nombre': f'Juan Pérez Silva {unique_suffix}',
            'Origen Empresa': 'BANCO CHILE',
            'Saldo actualizado': '1.250.000',
            'FechaVencimiento': '15/03/2024',
            'diasRetraso': 45,
            'Teléfono móvil': f'+56 9 8765 {unique_suffix[-4:]}',
            'Teléfono Residencial': '02-234-5678'
        },
        {
            'RUT': f'98.765.{unique_suffix[-3:]}-1',
            'Nombre': f'María González López {unique_suffix}',
            'Origen Empresa': 'BANCO SANTANDER',
            'Saldo actualizado': '500.750',
            'FechaVencimiento': '10/04/2024',
            'diasRetraso': 30,
            'Teléfono móvil': f'569 1234 {unique_suffix[-4:]}',
            'Teléfono Residencial': '08-419-0650'
        },
        {
            'RUT': f'11.222.{unique_suffix[-3:]}-K',
            'Nombre': f'Carlos Rodríguez Méndez {unique_suffix}',
            'Origen Empresa': 'FALABELLA',
            'Saldo actualizado': '2,500,000.50',
            'FechaVencimiento': '01/01/2024',
            'diasRetraso': 120,
            'Teléfono móvil': '',  # Sin móvil
            'Teléfono Residencial': '02-815-1807'
        }
    ]
    
    # Crear DataFrame
    df = pd.DataFrame(data)
    
    # Convertir a Excel en memoria
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    
    return buffer.getvalue()


async def test_excel_processing():
    """Prueba completa de procesamiento de Excel"""
    try:
        # Inicializar conexión
        settings = get_settings()
        db_manager = DatabaseManager(settings.database.uri, settings.database.database)
        await db_manager.connect()
        
        # Servicios
        account_service = AccountService(db_manager)
        batch_creation_service = BatchCreationService(db_manager)
        
        # 1. Crear cuenta de prueba
        test_account_id = f"test_excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Creando cuenta de prueba: {test_account_id}")
        
        account = await account_service.create_account(
            account_id=test_account_id,
            account_name="Cuenta de Prueba Excel",
            plan_type=PlanType.CREDIT_BASED,
            initial_credits=100.0
        )
        logger.info(f"Cuenta creada: {account.account_id}")
        
        # 2. Crear Excel de muestra
        excel_content = create_sample_excel()
        logger.info(f"Excel de muestra creado ({len(excel_content)} bytes)")
        
        # 3. Vista previa del Excel
        logger.info("Generando vista previa...")
        preview = await batch_creation_service.get_batch_preview(excel_content, test_account_id)
        
        if preview['success']:
            logger.info("Vista previa exitosa:")
            p = preview['preview']
            logger.info(f"  - Total filas: {p['total_rows']}")
            logger.info(f"  - Deudores válidos: {p['valid_debtors']}")
            logger.info(f"  - Con teléfono: {p['with_valid_phone']}")
            logger.info(f"  - Sin teléfono: {p['without_phone']}")
            logger.info(f"  - Monto total: ${p['total_debt_amount']:,.2f}")
            logger.info(f"  - Duplicados encontrados: {p['duplicates_found']}")
            
            if p['duplicates_preview']:
                logger.info("  - Vista previa duplicados:")
                for dup in p['duplicates_preview']:
                    logger.info(f"    * RUT {dup['rut']}: {dup['nombre']}")
        else:
            logger.error(f"Error en vista previa: {preview['error']}")
            return
        
        # 4. Crear batch (primera vez)
        logger.info("Creando batch desde Excel...")
        result = await batch_creation_service.create_batch_from_excel(
            file_content=excel_content,
            account_id=test_account_id,
            batch_name="Batch de Prueba Excel",
            batch_description="Prueba de importación desde Excel con lógica Adquisicion_v3",
            allow_duplicates=False
        )
        
        if result['success']:
            logger.info("Batch creado exitosamente:")
            logger.info(f"  - Batch ID: {result['batch_id']}")
            logger.info(f"  - Nombre: {result['batch_name']}")
            logger.info(f"  - Deudores: {result['total_debtors']}")
            logger.info(f"  - Jobs: {result['total_jobs']}")
            logger.info(f"  - Costo estimado: ${result['estimated_cost']:,.2f}")
            logger.info(f"  - Duplicados encontrados: {result['duplicates_found']}")
            
            batch_id = result['batch_id']
            
            # 5. Obtener estado del batch
            logger.info("Consultando estado del batch...")
            status = await batch_creation_service.get_batch_status(batch_id, test_account_id)
            
            if status:
                logger.info("Estado del batch:")
                logger.info(f"  - Nombre: {status['name']}")
                logger.info(f"  - Total jobs: {status['total_jobs']}")
                logger.info(f"  - Pendientes: {status['pending_jobs']}")
                logger.info(f"  - Completados: {status['completed_jobs']}")
                logger.info(f"  - Fallidos: {status['failed_jobs']}")
                logger.info(f"  - Tasa completitud: {status['completion_rate']:.1f}%")
            
            # 6. Intentar crear batch duplicado (debería detectar duplicados)
            logger.info("Intentando crear batch duplicado (debería fallar)...")
            duplicate_result = await batch_creation_service.create_batch_from_excel(
                file_content=excel_content,
                account_id=test_account_id,
                batch_name="Batch Duplicado",
                allow_duplicates=False
            )
            
            if duplicate_result['success']:
                logger.warning("¡ATENCIÓN! El batch duplicado se creó (no debería)")
            else:
                logger.info(f"Correcto: Batch duplicado rechazado - {duplicate_result['error']}")
            
            # 7. Crear batch duplicado permitiendo duplicados (con batch_id diferente)
            logger.info("Creando batch duplicado con allow_duplicates=True...")
            allowed_dup_result = await batch_creation_service.create_batch_from_excel(
                file_content=excel_content,
                account_id=test_account_id,
                batch_name="Batch Duplicado Permitido",
                batch_description="Segundo batch con duplicados permitidos",
                allow_duplicates=True
            )
            
            if allowed_dup_result['success']:
                logger.info(f"Batch duplicado creado correctamente: {allowed_dup_result['batch_id']}")
            else:
                logger.error(f"Error creando batch duplicado: {allowed_dup_result['error']}")
            
        else:
            logger.error(f"Error creando batch: {result['error']}")
        
        # 8. Verificar datos en MongoDB
        logger.info("Verificando datos en MongoDB...")
        
        # Contar deudores
        debtors_count = await db_manager.debtors.count_documents({
            "batch_id": {"$regex": f"^batch-{datetime.now().strftime('%Y-%m-%d')}"}
        })
        logger.info(f"Deudores en DB: {debtors_count}")
        
        # Contar jobs
        jobs_count = await db_manager.jobs.count_documents({
            "account_id": test_account_id
        })
        logger.info(f"Jobs en DB: {jobs_count}")
        
        # Contar batches
        batches_count = await db_manager.batches.count_documents({
            "account_id": test_account_id
        })
        logger.info(f"Batches en DB: {batches_count}")
        
        logger.info("🎉 Prueba completada exitosamente!")
        
    except Exception as e:
        logger.error(f"Error en prueba: {e}", exc_info=True)
    
    finally:
        if 'db_manager' in locals():
            await db_manager.close()


if __name__ == "__main__":
    print("Iniciando prueba de procesamiento de Excel...")
    asyncio.run(test_excel_processing())