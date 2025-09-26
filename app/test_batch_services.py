"""
Script de prueba para los nuevos servicios de carga de batches
Compara procesamiento básico vs adquisición
"""

import asyncio
import aiofiles
from datetime import datetime

# Importar servicios
import sys
sys.path.append('.')

from services.batch_creation_service import BatchCreationService
from services.acquisition_batch_service import AcquisitionBatchService
from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings

async def test_batch_services():
    """Prueba ambos servicios con el Excel de Chile"""
    
    # Configuración
    settings = get_settings()
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    await db_manager.connect()
    
    # Servicios
    basic_service = BatchCreationService(db_manager)
    acquisition_service = AcquisitionBatchService(db_manager)
    
    # Leer archivo Excel
    excel_path = "../docs/chile_usuarios.xlsx"
    
    try:
        async with aiofiles.open(excel_path, mode='rb') as f:
            file_content = await f.read()
        
        print(f"📁 Archivo cargado: {len(file_content)} bytes")
        print("=" * 60)
        
        # TEST 1: Procesamiento básico
        print("🔵 PRUEBA 1: Procesamiento Básico")
        print("-" * 40)
        
        basic_result = await basic_service.create_batch_from_excel(
            file_content=file_content,
            account_id="strasing",
            batch_name=f"Test Básico {datetime.now().strftime('%H:%M:%S')}",
            batch_description="Prueba del procesamiento básico",
            allow_duplicates=True
        )
        
        print(f"✅ Resultado básico:")
        print(f"   - Success: {basic_result['success']}")
        if basic_result['success']:
            print(f"   - Batch ID: {basic_result['batch_id']}")
            print(f"   - Stats: {basic_result.get('stats', 'No disponible')}")
        else:
            print(f"   - Error: {basic_result.get('error')}")
        
        print("\n" + "=" * 60)
        
        # TEST 2: Procesamiento de adquisición
        print("🟢 PRUEBA 2: Procesamiento de Adquisición")
        print("-" * 40)
        
        acquisition_result = await acquisition_service.create_batch_from_excel_acquisition(
            file_content=file_content,
            account_id="strasing",
            batch_name=f"Test Adquisición {datetime.now().strftime('%H:%M:%S')}",
            batch_description="Prueba del procesamiento de adquisición",
            allow_duplicates=True
        )
        
        print(f"✅ Resultado adquisición:")
        print(f"   - Success: {acquisition_result['success']}")
        if acquisition_result['success']:
            print(f"   - Batch ID: {acquisition_result['batch_id']}")
            print(f"   - Processing Type: {acquisition_result.get('processing_type')}")
            stats = acquisition_result.get('stats', {})
            print(f"   - Total filas procesadas: {stats.get('total_rows_processed')}")
            print(f"   - Deudores únicos encontrados: {stats.get('unique_debtors_found')}")
            print(f"   - Jobs creados: {stats.get('jobs_created')}")
            print(f"   - Duplicados filtrados: {stats.get('duplicates_filtered')}")
        else:
            print(f"   - Error: {acquisition_result.get('error')}")
        
        print("\n" + "=" * 60)
        print("🏆 COMPARACIÓN FINAL")
        print("-" * 40)
        
        if basic_result['success'] and acquisition_result['success']:
            basic_jobs = basic_result.get('stats', {}).get('jobs_created', 0)
            acq_jobs = acquisition_result.get('stats', {}).get('jobs_created', 0)
            
            print(f"📊 Jobs creados:")
            print(f"   - Básico: {basic_jobs}")
            print(f"   - Adquisición: {acq_jobs}")
            print(f"   - Diferencia: {basic_jobs - acq_jobs} (agrupación por RUT)")
            
            print(f"\n🎯 El procesamiento de adquisición:")
            print(f"   - Agrupa {basic_jobs} filas en {acq_jobs} deudores únicos")
            print(f"   - Reduce duplicados por RUT en {basic_jobs - acq_jobs} jobs")
            print(f"   - Aplica normalización chilena avanzada")
            print(f"   - Calcula fechas límite según reglas de negocio")
        
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo: {excel_path}")
        print("   Asegúrate de que existe el archivo Excel en docs/")
    
    except Exception as e:
        print(f"❌ Error durante las pruebas: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db_manager.close()
        print(f"\n🔌 Conexión cerrada")

if __name__ == "__main__":
    print("🚀 INICIANDO PRUEBAS DE SERVICIOS DE BATCH")
    print("=" * 60)
    asyncio.run(test_batch_services())
    print("=" * 60)
    print("✅ PRUEBAS COMPLETADAS")