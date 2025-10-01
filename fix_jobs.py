#!/usr/bin/env python3
"""
Script para agregar teléfonos de prueba a los jobs existentes
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "Debtors")

# Números de prueba válidos (argentinos que sabemos que funcionan)
TEST_PHONES = [
    "+5491136530246",  # Número real que funcionó antes
    "+5491158620976",  # Otro número real
]

def fix_jobs_add_phones():
    """Agrega teléfonos de prueba a jobs sin teléfonos"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        jobs_collection = db.jobs
        
        print("🔧 REPARANDO JOBS SIN TELÉFONOS")
        print("=" * 50)
        
        # Buscar jobs sin teléfonos
        jobs_without_phones = list(jobs_collection.find({
            "contact.phones": {"$size": 0}
        }))
        
        print(f"📱 Jobs sin teléfonos encontrados: {len(jobs_without_phones)}")
        
        if not jobs_without_phones:
            print("✅ No hay jobs sin teléfonos para reparar")
            return
        
        # Reparar cada job
        fixed_count = 0
        for i, job in enumerate(jobs_without_phones):
            job_id = job['_id']
            
            # Asignar teléfono de prueba (rotar entre los disponibles)
            test_phone = TEST_PHONES[i % len(TEST_PHONES)]
            
            # Actualizar job
            result = jobs_collection.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "contact.phones": [test_phone],
                        "status": "pending",  # Volver a pending para que lo procese
                        "attempts": 0,        # Resetear intentos
                        "last_error": None    # Limpiar error
                    }
                }
            )
            
            if result.modified_count > 0:
                fixed_count += 1
                print(f"✅ Job {job.get('job_id', job_id)} -> teléfono: {test_phone}")
            else:
                print(f"❌ No se pudo reparar job {job_id}")
        
        print(f"\n📊 RESUMEN:")
        print(f"  Jobs reparados: {fixed_count}")
        print(f"  Jobs pendientes de proceso: {fixed_count}")
        print(f"\n🚀 Ahora puedes ejecutar el worker de nuevo!")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    fix_jobs_add_phones()