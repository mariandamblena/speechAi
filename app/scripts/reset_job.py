#!/usr/bin/env python3
"""
Script para reiniciar un job específico para testing
"""
import os
import sys
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def reset_job(job_id_str: str):
    """Reinicia un job específico para testing"""
    
    # Conectar a MongoDB
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    db = client[os.getenv("MONGO_DB", "speechai_db")]
    coll = db[os.getenv("MONGO_COLL_JOBS", "jobs")]
    
    try:
        job_id = ObjectId(job_id_str)
        
        # Obtener job actual
        job = coll.find_one({"_id": job_id})
        if not job:
            print(f"❌ Job {job_id_str} no encontrado")
            return False
            
        print(f"📋 Job encontrado: {job.get('rut')} - {job.get('nombre')}")
        print(f"📞 Teléfono: {job.get('to_number')}")
        print(f"📊 Status actual: {job.get('status')}")
        
        # Resetear job
        update_result = coll.update_one(
            {"_id": job_id},
            {
                "$set": {
                    "status": "pending",
                    "attempts": 0,
                    "reserved_by": None,
                    "reserved_until": None,
                    "is_calling": False,
                    "worker_id": None
                },
                "$unset": {
                    "call_id": 1,
                    "call_started_at": 1,
                    "call_ended_at": 1,
                    "call_result": 1,
                    "call_duration_seconds": 1,
                    "finished_at": 1,
                    "started_at": 1
                }
            }
        )
        
        if update_result.modified_count > 0:
            print("✅ Job reiniciado exitosamente")
            print("🚀 Listo para ser procesado nuevamente")
            return True
        else:
            print("❌ No se pudo reiniciar el job")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        client.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python reset_job.py <job_id>")
        print("Ejemplo: python reset_job.py 68d1713d30b0c91f2f9b5a38")
        sys.exit(1)
        
    job_id = sys.argv[1]
    reset_job(job_id)