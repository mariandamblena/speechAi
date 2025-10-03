#!/usr/bin/env python3
"""
Script para migrar jobs existentes y extraer campos anidados al nivel raíz
Esto arregla el problema de variables faltantes en Retell
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, Any

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from infrastructure.database_manager import DatabaseManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'app', '.env'))

async def migrate_jobs():
    """Migrar jobs existentes para extraer campos anidados"""
    
    print("🔄 Migrando jobs existentes...")
    print("=" * 50)
    
    # Conectar a la base de datos
    db_manager = DatabaseManager(
        connection_string=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        database_name=os.getenv("MONGO_DB", "speechai_db")
    )
    
    try:
        await db_manager.connect()
        collection = db_manager.get_collection("jobs")
        
        # Buscar jobs que necesitan migración
        jobs_to_migrate = collection.find({
            "$or": [
                {"cantidad_cupones": {"$exists": False}},
                {"monto_total": {"$exists": False}},
                {"nombre": {"$exists": False}}
            ]
        })
        
        updated_count = 0
        
        async for job in jobs_to_migrate:
            job_id = job.get("_id")
            print(f"🔹 Migrando job: {job_id}")
            
            # Preparar actualización
            update_fields = {}
            
            # Extraer campos de contacto
            contact = job.get("contact", {})
            if contact:
                if contact.get("name") and not job.get("nombre"):
                    update_fields["nombre"] = contact["name"]
                
                if contact.get("dni") and not job.get("rut"):
                    update_fields["rut"] = contact["dni"]
                    update_fields["rut_fmt"] = contact["dni"]
                
                # Teléfono actual
                phones = contact.get("phones", [])
                next_phone_index = contact.get("next_phone_index", 0)
                if phones and 0 <= next_phone_index < len(phones):
                    update_fields["to_number"] = phones[next_phone_index]
            
            # Extraer campos de payload
            payload = job.get("payload", {})
            if payload:
                if payload.get("debt_amount") and not job.get("monto_total"):
                    update_fields["monto_total"] = payload["debt_amount"]
                    update_fields["deuda"] = payload["debt_amount"]
                
                if payload.get("due_date") and not job.get("fecha_limite"):
                    update_fields["fecha_limite"] = payload["due_date"]
                
                if payload.get("company_name") and not job.get("origen_empresa"):
                    update_fields["origen_empresa"] = payload["company_name"]
                
                # Campos del additional_info
                additional_info = payload.get("additional_info", {})
                for key in ['cantidad_cupones', 'fecha_maxima']:
                    if additional_info.get(key) and not job.get(key):
                        update_fields[key] = additional_info[key]
            
            # Aplicar actualización si hay campos que migrar
            if update_fields:
                print(f"   📝 Actualizando campos: {list(update_fields.keys())}")
                
                await collection.update_one(
                    {"_id": job_id},
                    {"$set": update_fields}
                )
                updated_count += 1
                
                # Mostrar algunos campos importantes
                if 'cantidad_cupones' in update_fields:
                    print(f"      🎯 cantidad_cupones: {update_fields['cantidad_cupones']}")
                if 'monto_total' in update_fields:
                    print(f"      💰 monto_total: {update_fields['monto_total']}")
            else:
                print(f"   ✅ Job ya migrado o sin datos para extraer")
        
        print("=" * 50)
        print(f"✅ Migración completada: {updated_count} jobs actualizados")
        
        # Verificar migración
        print("\n🔍 Verificando migración...")
        test_job = await collection.find_one({}, sort=[("created_at", -1)])
        
        if test_job:
            print("📋 Último job después de migración:")
            print(f"   - nombre: {test_job.get('nombre', 'NO DEFINIDO')}")
            print(f"   - rut: {test_job.get('rut', 'NO DEFINIDO')}")
            print(f"   - cantidad_cupones: {test_job.get('cantidad_cupones', 'NO DEFINIDO')}")
            print(f"   - monto_total: {test_job.get('monto_total', 'NO DEFINIDO')}")
            print(f"   - origen_empresa: {test_job.get('origen_empresa', 'NO DEFINIDO')}")
            
    except Exception as e:
        print(f"❌ Error durante migración: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await db_manager.close()

async def main():
    print("🔄 MIGRACIÓN DE JOBS PARA RETELL")
    print("Este script extrae campos anidados al nivel raíz para compatibilidad")
    print()
    
    await migrate_jobs()

if __name__ == "__main__":
    asyncio.run(main())