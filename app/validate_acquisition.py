"""
Script de validación completa del servicio de adquisición
Verifica todos los componentes antes de la prueba final
"""

import asyncio
from datetime import datetime

# Importar servicios
import sys
sys.path.append('.')

from services.acquisition_batch_service import AcquisitionBatchService
from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings

async def validate_acquisition_service():
    """Valida que el servicio de adquisición esté completamente funcional"""
    
    print("🔍 VALIDACIÓN DEL SERVICIO DE ADQUISICIÓN")
    print("=" * 60)
    
    try:
        # 1. Configuración
        print("1️⃣ Configurando conexiones...")
        settings = get_settings()
        db_manager = DatabaseManager(settings.database.uri, settings.database.database)
        await db_manager.connect()
        print("   ✅ Conexión a MongoDB establecida")
        
        # 2. Instanciar servicio
        print("\n2️⃣ Instanciando servicio de adquisición...")
        acquisition_service = AcquisitionBatchService(db_manager)
        print("   ✅ AcquisitionBatchService creado")
        
        # 3. Verificar archivo Excel
        print("\n3️⃣ Verificando archivo Excel...")
        excel_path = "../docs/chile_usuarios.xlsx"
        
        try:
            with open(excel_path, 'rb') as f:
                file_content = f.read()
            
            file_size_mb = len(file_content) / (1024 * 1024)
            print(f"   ✅ Archivo encontrado: {file_size_mb:.2f} MB")
            
        except FileNotFoundError:
            print(f"   ❌ Archivo no encontrado: {excel_path}")
            print("   📌 Asegúrate de que el Excel esté en docs/chile_usuarios.xlsx")
            return False
        
        # 4. Verificar cuenta
        print("\n4️⃣ Verificando cuenta 'strasing'...")
        account = await acquisition_service.account_service.get_account("strasing")
        
        if account:
            print(f"   ✅ Cuenta encontrada: {account.account_name}")
            print(f"   ✅ Status: {account.status}")
            print(f"   ✅ Minutos disponibles: {account.minutes_remaining}")
        else:
            print("   ❌ Cuenta 'strasing' no encontrada")
            print("   📌 Necesitas crear la cuenta primero")
            return False
        
        # 5. Test de procesamiento (sin guardar)
        print("\n5️⃣ Test de procesamiento Excel...")
        
        try:
            # Procesar Excel con el procesador interno
            excel_result = acquisition_service.excel_processor.process_excel_data(
                file_content, "strasing"
            )
            
            print(f"   ✅ Excel procesado exitosamente")
            print(f"   ✅ Total deudores únicos: {len(excel_result['debtors'])}")
            print(f"   ✅ Batch ID generado: {excel_result['batch_id']}")
            
            # Muestra de un deudor procesado
            if excel_result['debtors']:
                sample = excel_result['debtors'][0]
                print(f"   ✅ Ejemplo deudor:")
                print(f"      - RUT: {sample.get('rut')}")
                print(f"      - Nombre: {sample.get('nombre')}")
                print(f"      - Monto: ${sample.get('monto_total'):,.0f}")
                print(f"      - Cupones: {sample.get('cantidad_cupones')}")
                print(f"      - Teléfono: {sample.get('to_number')}")
                
        except Exception as e:
            print(f"   ❌ Error procesando Excel: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        # 6. Validar métodos del DatabaseManager
        print("\n6️⃣ Validando métodos de DatabaseManager...")
        
        required_methods = ['find_documents', 'insert_document', 'update_document']
        for method_name in required_methods:
            if hasattr(db_manager, method_name):
                print(f"   ✅ {method_name}")
            else:
                print(f"   ❌ {method_name} - FALTANTE")
                return False
        
        print("\n" + "=" * 60)
        print("🎉 VALIDACIÓN COMPLETA - TODO LISTO")
        print("=" * 60)
        
        print("📋 Resumen:")
        print("   ✅ Conexión a MongoDB")
        print("   ✅ Servicio de adquisición")
        print("   ✅ Archivo Excel válido")
        print("   ✅ Cuenta 'strasing' activa")
        print("   ✅ Procesamiento de Excel funcional")
        print("   ✅ Métodos de base de datos disponibles")
        
        print("\n🚀 LISTO PARA PRUEBA REAL:")
        print("   curl -X POST \"http://localhost:8000/api/v1/batches/excel/create?account_id=strasing&processing_type=acquisition&allow_duplicates=true\" \\")
        print("     -F \"file=@docs/chile_usuarios.xlsx\"")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR DURANTE VALIDACIÓN: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await db_manager.close()
        print(f"\n🔌 Conexión cerrada")

if __name__ == "__main__":
    result = asyncio.run(validate_acquisition_service())
    if result:
        print("\n✅ ¡SISTEMA COMPLETAMENTE VALIDADO!")
    else:
        print("\n❌ Se encontraron problemas que requieren atención")