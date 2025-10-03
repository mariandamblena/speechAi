#!/usr/bin/env python3
"""
Script para debuggear variables enviadas a Retell
Busca la última llamada y muestra el contexto que se envió
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from infrastructure.database_manager import DatabaseManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'app', '.env'))

async def debug_retell_variables():
    """Debug de variables enviadas a Retell"""
    
    print("🔍 Analizando variables enviadas a Retell...")
    print("=" * 50)
    
    # Conectar a la base de datos
    db_manager = DatabaseManager(
        connection_string=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        database_name=os.getenv("MONGO_DB", "speechai_db")
    )
    
    try:
        await db_manager.connect()
        
        # Obtener los últimos jobs
        collection = db_manager.get_collection("jobs")
        
        # Buscar jobs recientes con call_result
        recent_jobs = collection.find({
            "call_result": {"$exists": True}
        }).sort("created_at", -1).limit(5)
        
        print("📋 Últimos 5 jobs con resultados de llamada:")
        print()
        
        async for job in recent_jobs:
            job_id = str(job.get("_id"))
            created_at = job.get("created_at", "")
            nombre = job.get("nombre", "N/A")
            rut = job.get("rut", "N/A")
            
            # Información básica
            print(f"🔹 Job ID: {job_id}")
            print(f"   📅 Creado: {created_at}")
            print(f"   👤 Nombre: {nombre}")
            print(f"   🆔 RUT: {rut}")
            
            # Variables importantes para cuotas
            cantidad_cupones = job.get("cantidad_cupones", "NO DEFINIDO")
            monto_total = job.get("monto_total", "NO DEFINIDO")
            
            print(f"   💳 Cantidad cupones: {cantidad_cupones}")
            print(f"   💰 Monto total: {monto_total}")
            
            # Revisar call_result si existe
            call_result = job.get("call_result", {})
            if call_result:
                summary = call_result.get("summary", {})
                retell_variables = summary.get("retell_llm_dynamic_variables", {})
                
                if retell_variables:
                    print(f"   📤 Variables enviadas a Retell:")
                    for key, value in retell_variables.items():
                        if 'cuota' in key.lower() or 'cupones' in key.lower():
                            print(f"      🎯 {key}: '{value}'")
                        else:
                            print(f"      - {key}: '{value}'")
                else:
                    print(f"   ⚠️ No hay variables de Retell registradas")
            
            print()
        
        # Análisis específico del último job
        print("🔍 ANÁLISIS DETALLADO DEL ÚLTIMO JOB:")
        print("=" * 40)
        
        last_job = await collection.find_one({}, sort=[("created_at", -1)])
        
        if last_job:
            print("📋 Datos del job en MongoDB:")
            print(f"   - _id: {last_job.get('_id')}")
            print(f"   - nombre: {last_job.get('nombre')}")
            print(f"   - rut: {last_job.get('rut')}")
            print(f"   - cantidad_cupones: {last_job.get('cantidad_cupones', 'NO DEFINIDO')}")
            print(f"   - monto_total: {last_job.get('monto_total', 'NO DEFINIDO')}")
            print(f"   - origen_empresa: {last_job.get('origen_empresa', 'NO DEFINIDO')}")
            print(f"   - fecha_limite: {last_job.get('fecha_limite', 'NO DEFINIDO')}")
            print(f"   - fecha_maxima: {last_job.get('fecha_maxima', 'NO DEFINIDO')}")
            
            # Simular el contexto que se generaría
            print()
            print("🧮 Contexto que se generaría con _context_from_job:")
            
            # Recrear la lógica de _context_from_job
            now_chile = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            context = {
                "nombre": str(last_job.get("nombre", "")),
                "empresa": str(last_job.get("origen_empresa", "")),
                "RUT": str(last_job.get("rut_fmt") or last_job.get("rut", "")),
                "cantidad_cupones": str(last_job.get("cantidad_cupones", "")),
                "cuotas_adeudadas": str(last_job.get("cantidad_cupones", "")),
                "monto_total": str(last_job.get("monto_total", "")),
                "fecha_limite": str(last_job.get("fecha_limite", "")),
                "fecha_maxima": str(last_job.get("fecha_maxima", "")),
                "fecha_pago_cliente": "",
                "current_time_America_Santiago": now_chile,
            }
            
            # Filtrar valores vacíos
            context = {k: v for k, v in context.items() if v and v != "None"}
            
            for key, value in context.items():
                if 'cuota' in key.lower() or 'cupones' in key.lower():
                    print(f"   🎯 {key}: '{value}'")
                else:
                    print(f"   - {key}: '{value}'")
            
            # Verificar si falta la variable de cuotas
            if not context.get("cuotas_adeudadas") or context.get("cuotas_adeudadas") == "":
                print()
                print("❌ PROBLEMA ENCONTRADO:")
                print("   La variable 'cuotas_adeudadas' está vacía o no definida")
                print("   Esto significa que 'cantidad_cupones' no tiene valor en el job")
                
                # Sugerir solución
                print()
                print("💡 POSIBLES CAUSAS Y SOLUCIONES:")
                print("1. El campo 'cantidad_cupones' no se está guardando en MongoDB")
                print("2. El Excel original no tiene la columna de cuotas")
                print("3. El procesamiento del Excel no está mapeando correctamente")
                print("4. La validación está rechazando el valor")
            
            else:
                print()
                print("✅ La variable 'cuotas_adeudadas' tiene valor, debería llegar a Retell")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await db_manager.close()

async def main():
    print("🧪 DEBUG: Variables de Retell")
    print("Analizando los datos enviados a Retell para encontrar el problema con cuotas")
    print()
    
    await debug_retell_variables()

if __name__ == "__main__":
    asyncio.run(main())