#!/usr/bin/env python3
"""
Script para diagnosticar jobs sin teléfonos en MongoDB
"""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "Debtors")

def diagnose_jobs():
    """Diagnostica jobs en la base de datos"""
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        jobs_collection = db.jobs
        
        print("📊 DIAGNÓSTICO DE JOBS EN BD")
        print("=" * 50)
        
        # Total de jobs
        total_jobs = jobs_collection.count_documents({})
        print(f"Total jobs: {total_jobs}")
        
        # Jobs por status
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = list(jobs_collection.aggregate(pipeline))
        print(f"\n📈 Jobs por status:")
        for item in status_counts:
            print(f"  {item['_id']}: {item['count']}")
        
        # Jobs sin teléfonos
        jobs_without_phones = jobs_collection.count_documents({
            "$or": [
                {"contact.phones": {"$exists": False}},
                {"contact.phones": {"$size": 0}},
                {"contact.phones": []}
            ]
        })
        print(f"\n❌ Jobs sin teléfonos: {jobs_without_phones}")
        
        # Jobs con teléfonos
        jobs_with_phones = jobs_collection.count_documents({
            "contact.phones": {"$exists": True, "$ne": [], "$not": {"$size": 0}}
        })
        print(f"✅ Jobs con teléfonos: {jobs_with_phones}")
        
        # Muestra de jobs sin teléfonos
        print(f"\n🔍 Muestra de jobs sin teléfonos:")
        sample_jobs = jobs_collection.find({
            "contact.phones": {"$size": 0}
        }).limit(3)
        
        for job in sample_jobs:
            print(f"\n  Job ID: {job.get('job_id', 'N/A')}")
            print(f"  RUT: {job.get('contact', {}).get('dni', 'N/A')}")
            print(f"  Nombre: {job.get('contact', {}).get('name', 'N/A')}")
            print(f"  Phones: {job.get('contact', {}).get('phones', 'N/A')}")
            print(f"  Status: {job.get('status', 'N/A')}")
            print(f"  Batch: {job.get('batch_id', 'N/A')}")
        
        # Verificar si hay jobs con teléfonos para comparar
        print(f"\n🔍 Muestra de jobs CON teléfonos (para comparar):")
        sample_with_phones = jobs_collection.find({
            "contact.phones": {"$exists": True, "$ne": []}
        }).limit(2)
        
        for job in sample_with_phones:
            print(f"\n  Job ID: {job.get('job_id', 'N/A')}")
            print(f"  RUT: {job.get('contact', {}).get('dni', 'N/A')}")
            print(f"  Phones: {job.get('contact', {}).get('phones', 'N/A')}")
            print(f"  Status: {job.get('status', 'N/A')}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error conectando a MongoDB: {e}")

if __name__ == "__main__":
    diagnose_jobs()