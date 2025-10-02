#!/usr/bin/env python3
"""
Script de prueba para verificar la conectividad y funcionamiento básico
"""

import os
import sys
import asyncio
from datetime import datetime, timezone

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from infrastructure.database_manager import DatabaseManager
from dotenv import load_dotenv

async def test_connection():
    """Probar conexión y obtener estadísticas básicas"""
    
    print("🔍 Probando conexión a la base de datos...")
    
    # Load environment variables
    load_dotenv(os.path.join(os.path.dirname(__file__), 'app', '.env'))
    
    # Conectar a la base de datos
    db_manager = DatabaseManager(
        connection_string=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        database_name=os.getenv("MONGO_DB", "speechai_db")
    )
    
    try:
        await db_manager.connect()
        print("✅ Conexión exitosa a MongoDB")
        
        # Obtener estadísticas básicas
        collection = db_manager.get_collection("jobs")
        
        total_jobs = await collection.count_documents({})
        print(f"📊 Total de jobs en la base de datos: {total_jobs}")
        
        # Jobs de los últimos 7 días
        from datetime import timedelta
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_jobs = await collection.count_documents({
            "created_at": {"$gte": seven_days_ago}
        })
        print(f"📅 Jobs de los últimos 7 días: {recent_jobs}")
        
        # Jobs con call_result
        completed_jobs = await collection.count_documents({
            "call_result": {"$exists": True}
        })
        print(f"📞 Jobs con resultado de llamada: {completed_jobs}")
        
        # Obtener un ejemplo de job para verificar estructura
        sample_job = await collection.find_one({}, {"_id": 1, "account_id": 1, "status": 1, "created_at": 1})
        if sample_job:
            print(f"🔍 Ejemplo de job:")
            print(f"   - ID: {sample_job.get('_id')}")
            print(f"   - Account: {sample_job.get('account_id', 'N/A')}")
            print(f"   - Status: {sample_job.get('status', 'N/A')}")
            print(f"   - Created: {sample_job.get('created_at', 'N/A')}")
        
        if recent_jobs > 0:
            print("✅ ¡Hay datos disponibles para generar reportes!")
            return True
        else:
            print("⚠️ No hay jobs recientes. Los reportes estarán vacíos.")
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False
        
    finally:
        await db_manager.close()

async def main():
    print("🧪 Test de Generador de Reportes")
    print("=" * 40)
    
    # Verificar dependencias
    try:
        import pandas as pd
        import openpyxl
        print("✅ Dependencias pandas y openpyxl encontradas")
    except ImportError as e:
        print(f"❌ Dependencia faltante: {e}")
        print("Ejecutar: pip install pandas openpyxl")
        return
    
    # Verificar archivo .env
    env_path = os.path.join(os.path.dirname(__file__), 'app', '.env')
    if os.path.exists(env_path):
        print(f"✅ Archivo .env encontrado: {env_path}")
    else:
        print(f"⚠️ Archivo .env no encontrado: {env_path}")
    
    # Probar conexión
    success = await test_connection()
    
    print("=" * 40)
    if success:
        print("🎉 ¡Todo listo para generar reportes!")
        print("\nEjecutar reportes:")
        print("• Script simple: python simple_report.py")
        print("• Script completo: python generate_call_report.py --days 7")
    else:
        print("⚠️ Revisar configuración antes de generar reportes")

if __name__ == "__main__":
    asyncio.run(main())