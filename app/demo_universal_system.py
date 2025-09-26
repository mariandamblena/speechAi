"""
Demo del sistema universal - Muestra cómo crear batches de diferentes casos de uso
"""
import asyncio
import aiohttp
import json
import pandas as pd
from io import BytesIO
import os

# URL base de la API (ajustar según tu configuración)
API_BASE = "http://localhost:8000"

async def demo_universal_system():
    """Demostración completa del sistema universal"""
    
    print("🎯 DEMO: SISTEMA UNIVERSAL SPEECHAI")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        
        # 1. Obtener información del sistema
        print("\n1. 📋 INFORMACIÓN DEL SISTEMA")
        async with session.get(f"{API_BASE}/") as response:
            info = await response.json()
            print(f"✅ API Version: {info['version']}")
            print(f"✅ Casos de uso soportados: {len(info['supported_use_cases'])}")
        
        # 2. Listar casos de uso disponibles
        print("\n2. 🎯 CASOS DE USO DISPONIBLES")
        async with session.get(f"{API_BASE}/use-cases") as response:
            use_cases = await response.json()
            
            for use_case_name, details in use_cases['use_cases'].items():
                print(f"\n🔹 {details['name']}")
                print(f"   📝 {details['description']}")
                print(f"   📊 Columnas requeridas: {details['required_columns']}")
        
        # 3. Generar templates Excel
        print("\n3. 📊 GENERANDO TEMPLATES EXCEL")
        
        # Template para cobranza
        await generate_excel_template(session, "debt_collection", "template_cobranza.xlsx")
        
        # Template para user experience  
        await generate_excel_template(session, "user_experience", "template_ux.xlsx")
        
        # 4. Crear batch de cobranza
        print("\n4. 💰 CREANDO BATCH DE COBRANZA")
        cobranza_batch_id = await create_demo_batch(
            session, 
            "debt_collection",
            "template_cobranza.xlsx",
            "test_cobranza_account",
            "Demo Cobranza Batch"
        )
        
        # 5. Crear batch de user experience
        print("\n5. 😊 CREANDO BATCH DE USER EXPERIENCE")
        ux_batch_id = await create_demo_batch(
            session,
            "user_experience", 
            "template_ux.xlsx",
            "test_ux_account",
            "Demo UX Batch"
        )
        
        # 6. Verificar batches creados
        print("\n6. 📈 VERIFICANDO BATCHES CREADOS")
        if cobranza_batch_id:
            await check_batch_status(session, cobranza_batch_id, "Cobranza")
        
        if ux_batch_id:
            await check_batch_status(session, ux_batch_id, "User Experience")
        
        # 7. Listar todos los batches
        print("\n7. 📋 LISTADO GENERAL DE BATCHES")
        async with session.get(f"{API_BASE}/batches") as response:
            batches = await response.json()
            
            if batches['success']:
                print(f"📊 Total de batches: {batches['pagination']['total']}")
                
                for batch in batches['batches'][:5]:  # Mostrar solo primeros 5
                    print(f"\n🔹 {batch['name']}")
                    print(f"   📝 Caso de uso: {batch['use_case']}")
                    print(f"   👤 Account: {batch['account_id']}")
                    print(f"   📊 Jobs: {batch['stats']['total_jobs']}")
                    print(f"   ✅ Success rate: {batch['stats']['success_rate']:.1f}%")
    
    print("\n🎉 DEMO COMPLETADO")
    print("📝 Archivos generados:")
    print("   - template_cobranza.xlsx")  
    print("   - template_ux.xlsx")
    print("\n🤖 Para procesar los batches, ejecuta:")
    print("   python app/universal_call_worker.py")


async def generate_excel_template(session, use_case: str, filename: str):
    """Genera y guarda template Excel"""
    try:
        async with session.get(f"{API_BASE}/use-cases/{use_case}/template") as response:
            template_data = await response.json()
            
            if template_data['success']:
                # Crear DataFrame con el template
                df = pd.DataFrame(template_data['template'])
                
                # Guardar Excel
                df.to_excel(filename, index=False)
                print(f"✅ Template generado: {filename}")
                print(f"   📊 Columnas: {template_data['required_columns']}")
            else:
                print(f"❌ Error generando template para {use_case}")
                
    except Exception as e:
        print(f"❌ Error: {e}")


async def create_demo_batch(session, use_case: str, template_file: str, account_id: str, batch_name: str):
    """Crea batch demo usando template"""
    try:
        # Verificar que existe el template
        if not os.path.exists(template_file):
            print(f"⚠️  Template {template_file} no encontrado, saltando...")
            return None
        
        # Preparar datos para envío
        data = {
            'use_case': use_case,
            'account_id': account_id,
            'batch_name': batch_name,
            'batch_description': f"Batch demo de {use_case} generado automáticamente"
        }
        
        # Enviar archivo
        with open(template_file, 'rb') as f:
            files = {'file': f}
            
            async with session.post(f"{API_BASE}/batches/create", data=data, data=files) as response:
                result = await response.json()
                
                if result.get('success'):
                    batch_id = result['batch_id']
                    stats = result['stats']
                    
                    print(f"✅ Batch creado: {batch_id}")
                    print(f"   📊 Jobs creados: {stats['successful_jobs']}")
                    print(f"   ⚠️  Errores: {stats['failed_rows']}")
                    
                    return batch_id
                else:
                    print(f"❌ Error creando batch: {result.get('message', 'Unknown error')}")
                    if result.get('errors'):
                        for error in result['errors'][:3]:  # Mostrar solo primeros 3 errores
                            print(f"   💥 {error}")
                    
                    return None
                    
    except Exception as e:
        print(f"❌ Error creando batch: {e}")
        return None


async def check_batch_status(session, batch_id: str, batch_type: str):
    """Verifica estado de un batch"""
    try:
        async with session.get(f"{API_BASE}/batches/{batch_id}") as response:
            batch_data = await response.json()
            
            if batch_data['success']:
                batch = batch_data['batch']
                stats = batch_data['stats']
                
                print(f"\n📊 BATCH {batch_type.upper()}: {batch_id}")
                print(f"   📝 Nombre: {batch['name']}")
                print(f"   📅 Creado: {batch['created_at']}")
                print(f"   📊 Total jobs: {stats['total_jobs']}")
                print(f"   ✅ Completados: {stats['completed_jobs']}")
                print(f"   ❌ Fallidos: {stats['failed_jobs']}")
                print(f"   ⏳ Pendientes: {stats['pending_jobs']}")
                print(f"   📈 Success rate: {stats['success_rate']}%")
            else:
                print(f"❌ Error obteniendo batch {batch_id}")
                
    except Exception as e:
        print(f"❌ Error verificando batch: {e}")


def create_sample_data():
    """Crea datos de ejemplo en los templates"""
    
    # Datos de ejemplo para cobranza
    cobranza_data = {
        'nombre': ['Juan Pérez', 'María González', 'Carlos Rodriguez'],
        'rut': ['12345678-9', '98765432-1', '11223344-5'],
        'telefono': ['+56912345678', '+56987654321', '+56955566677'],
        'deuda': [150000, 89000, 245000],
        'fecha_vencimiento': ['2024-01-15', '2024-01-20', '2024-01-10'],
        'empresa': ['Empresa ABC', 'Empresa XYZ', 'Empresa 123'],
        'telefono2': ['+56922334455', '', '+56933445566'],
        'email': ['juan@example.com', 'maria@example.com', 'carlos@example.com']
    }
    
    # Datos de ejemplo para UX
    ux_data = {
        'nombre': ['Ana Silva', 'Pedro Martínez', 'Laura Castro'],
        'customer_id': ['CUST001', 'CUST002', 'CUST003'],
        'telefono': ['+56911223344', '+56922334455', '+56933445566'],
        'interaction_type': ['post_purchase', 'feedback', 'survey'],
        'producto_servicio': ['Smartphone Pro', 'Laptop Gaming', 'Tablet Mini'],
        'fecha_compra': ['2024-01-10', '2024-01-12', '2024-01-08'],
        'email': ['ana@example.com', 'pedro@example.com', 'laura@example.com']
    }
    
    # Sobrescribir templates con datos de ejemplo
    pd.DataFrame(cobranza_data).to_excel('template_cobranza.xlsx', index=False)
    pd.DataFrame(ux_data).to_excel('template_ux.xlsx', index=False)
    
    print("📝 Templates actualizados con datos de ejemplo")


if __name__ == "__main__":
    print("🚀 Iniciando demo del sistema universal...")
    print("⚠️  Asegúrate de que la API esté corriendo en http://localhost:8000")
    print()
    
    # Crear datos de ejemplo
    create_sample_data()
    
    # Ejecutar demo
    asyncio.run(demo_universal_system())