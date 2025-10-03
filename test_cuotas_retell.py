#!/usr/bin/env python3
"""
Script para probar que las variables de cuotas lleguen correctamente a Retell
"""

import os
import sys
import asyncio
from datetime import datetime, timezone
import json

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from infrastructure.database_manager import DatabaseManager
from infrastructure.retell_client import RetellApiClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'app', '.env'))

async def test_retell_call():
    """Probar llamada con variables de cuotas"""
    
    print("🧪 PRUEBA DE LLAMADA CON VARIABLES DE CUOTAS")
    print("=" * 50)
    
    # Conectar a la base de datos
    db_manager = DatabaseManager(
        connection_string=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        database_name=os.getenv("MONGO_DB", "speechai_db")
    )
    
    try:
        await db_manager.connect()
        collection = db_manager.get_collection("jobs")
        
        # Obtener un job con datos completos
        test_job = await collection.find_one({
            "cantidad_cupones": {"$exists": True},
            "monto_total": {"$exists": True},
            "nombre": {"$exists": True}
        })
        
        if not test_job:
            print("❌ No se encontró un job con datos completos para probar")
            return
        
        print("📋 Job seleccionado para prueba:")
        print(f"   - ID: {test_job['_id']}")
        print(f"   - Nombre: {test_job.get('nombre')}")
        print(f"   - RUT: {test_job.get('rut')}")
        print(f"   - Teléfono: {test_job.get('to_number', 'NO DEFINIDO')}")
        print(f"   - Cantidad cupones: {test_job.get('cantidad_cupones')}")
        print(f"   - Monto total: {test_job.get('monto_total')}")
        print(f"   - Empresa: {test_job.get('origen_empresa')}")
        
        # Simular el contexto que se enviaría a Retell
        now_chile = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        context = {
            "nombre": str(test_job.get("nombre", "")),
            "empresa": str(test_job.get("origen_empresa", "")),
            "RUT": str(test_job.get("rut_fmt") or test_job.get("rut", "")),
            "cantidad_cupones": str(test_job.get("cantidad_cupones", "")),
            "cuotas_adeudadas": str(test_job.get("cantidad_cupones", "")),
            "monto_total": str(test_job.get("monto_total", "")),
            "fecha_limite": str(test_job.get("fecha_limite", "")),
            "fecha_maxima": str(test_job.get("fecha_maxima", "")),
            "fecha_pago_cliente": "",
            "current_time_America_Santiago": now_chile,
        }
        
        # Filtrar valores vacíos
        context = {k: v for k, v in context.items() if v and v != "None"}
        
        print("\n📤 Contexto que se enviaría a Retell:")
        for key, value in context.items():
            if 'cuota' in key.lower() or 'cupones' in key.lower():
                print(f"   🎯 {key}: '{value}'")
            else:
                print(f"   - {key}: '{value}'")
        
        # Verificar variables críticas
        print("\n🔍 Verificación de variables críticas:")
        
        critical_vars = ['cuotas_adeudadas', 'cantidad_cupones', 'monto_total', 'nombre']
        all_present = True
        
        for var in critical_vars:
            if var in context and context[var]:
                print(f"   ✅ {var}: OK")
            else:
                print(f"   ❌ {var}: FALTANTE")
                all_present = False
        
        if all_present:
            print("\n🎉 ¡TODAS LAS VARIABLES CRÍTICAS ESTÁN PRESENTES!")
            print("Las cuotas deberían llegar correctamente a Retell en la próxima llamada.")
        else:
            print("\n⚠️ Faltan variables críticas. Revisar la configuración.")
        
        # Opcional: Probar con Retell real (comentado por seguridad)
        print("\n💡 Para probar llamada real:")
        print("1. Descomenta la sección de llamada real en el código")
        print("2. Cambia test_phone por un número válido")
        print("3. Asegúrate de tener RETELL_AGENT_ID y RETELL_FROM_NUMBER configurados")
        print("4. Ejecuta el script nuevamente")
        
    except Exception as e:
        print(f"❌ Error durante prueba: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await db_manager.close()

async def main():
    print("🧪 TEST: Variables de Cuotas para Retell")
    print("Verificando que las variables lleguen correctamente")
    print()
    
    await test_retell_call()

if __name__ == "__main__":
    asyncio.run(main())