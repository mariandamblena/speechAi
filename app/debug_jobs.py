#!/usr/bin/env python3
"""
Script para debug detallado de jobs
"""
import os
import sys
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

# Configurar MongoDB
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB = "Debtors" 
MONGO_COLL_JOBS = "jobs"

def main():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    jobs = db[MONGO_COLL_JOBS]

    print("=== DEBUG DETALLADO DE JOBS ===")
    
    # 1. Contar jobs por status
    print("\n1. CONTEO POR STATUS:")
    pipeline = [
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]
    result = list(jobs.aggregate(pipeline))
    
    for r in result:
        print(f"   {r['_id']}: {r['count']} jobs")
    
    # 2. Mostrar primeros jobs pending
    print("\n2. PRIMEROS 3 JOBS PENDING:")
    pending_jobs = list(jobs.find({"status": "pending"}).limit(3))
    
    for i, job in enumerate(pending_jobs):
        print(f"   Job {i+1}:")
        print(f"     _id: {job['_id']}")
        print(f"     status: {job.get('status')}")
        print(f"     account_id: {job.get('account_id')}")
        print(f"     attempts: {job.get('attempts', 0)}/{job.get('max_attempts', 3)}")
        print(f"     worker_id: {job.get('worker_id', 'None')}")
        print(f"     reserved_until: {job.get('reserved_until', 'None')}")
        print(f"     last_error: {job.get('last_error', 'None')}")
        print("     ---")
    
    # 3. Probar el filtro exacto del worker
    print("\n3. PROBANDO FILTRO EXACTO DEL WORKER:")
    filter_exact = {"status": "pending"}
    
    count = jobs.count_documents(filter_exact)
    print(f"   Filtro: {filter_exact}")
    print(f"   Jobs encontrados: {count}")
    
    if count > 0:
        sample_job = jobs.find_one(filter_exact)
        print(f"   Sample job _id: {sample_job['_id']}")
        
        # 4. Simular la operación find_one_and_update
        print("\n4. SIMULANDO find_one_and_update:")
        now = datetime.utcnow()
        
        # Intentar la actualización
        updated_doc = jobs.find_one_and_update(
            filter=filter_exact,
            update={
                "$set": {
                    "status": "in_progress", 
                    "reserved_until": now,
                    "worker_id": "debug_test",
                    "started_at": now,
                    "updated_at": now,
                },
                "$inc": {"attempts": 1}
            },
            return_document=1  # AFTER
        )
        
        if updated_doc:
            print(f"   ✅ Actualización exitosa!")
            print(f"   Job actualizado: {updated_doc['_id']}")
            print(f"   Nuevo status: {updated_doc.get('status')}")
            
            # Revertir cambios
            jobs.update_one(
                {"_id": updated_doc["_id"]},
                {
                    "$set": {"status": "pending", "worker_id": None, "reserved_until": None},
                    "$inc": {"attempts": -1}
                }
            )
            print("   Cambios revertidos para testing")
        else:
            print("   ❌ find_one_and_update no encontró nada")
    else:
        print("   ❌ No hay jobs pending!")

if __name__ == "__main__":
    main()