#!/usr/bin/env python3
"""
Script para verificar y resetear jobs en la base de datos
"""
import os
import sys
from pymongo import MongoClient
from datetime import datetime

# Configurar MongoDB
MONGO_URI = "mongodb://localhost:27017"
MONGO_DB = "Debtors" 
MONGO_COLL_JOBS = "jobs"

def main():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    jobs = db[MONGO_COLL_JOBS]

    print("=== ESTADO ACTUAL DE JOBS ===")
    
    # Contar jobs por status
    pipeline = [
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]
    result = list(jobs.aggregate(pipeline))
    
    for r in result:
        print(f"{r['_id']}: {r['count']} jobs")
    
    print(f"\nTotal jobs en DB: {jobs.count_documents({})}")
    
    # Mostrar últimos jobs con errores
    print("\n=== ÚLTIMOS 5 JOBS CON ERROR ===")
    error_jobs = list(jobs.find({"last_error": {"$exists": True}}).sort('_id', -1).limit(5))
    
    for job in error_jobs:
        print(f"ID: {job['_id']}")
        print(f"Status: {job.get('status')}")
        print(f"Error: {job.get('last_error')}")
        print(f"Attempts: {job.get('attempts', 0)}/{job.get('max_attempts', 3)}")
        print("---")
    
    # Preguntar si resetear jobs fallidos
    response = input("\n¿Resetear jobs fallidos a 'pending'? (y/N): ")
    
    if response.lower() == 'y':
        # Resetear jobs que fallaron por saldo insuficiente o errores de import
        filter_conditions = {
            "$or": [
                {"last_error": {"$regex": "Saldo insuficiente"}},
                {"last_error": {"$regex": "No module named 'app'"}},
                {"status": "failed", "attempts": {"$lt": 3}}
            ]
        }
        
        update_data = {
            "$set": {
                "status": "pending",
                "worker_id": None,
                "started_at": None,
                "reserved_until": None,
                "updated_at": datetime.utcnow()
            },
            "$unset": {
                "last_error": ""
            }
        }
        
        result = jobs.update_many(filter_conditions, update_data)
        print(f"✅ {result.modified_count} jobs reseteados a 'pending'")
        
        # Mostrar nuevo estado
        print("\n=== NUEVO ESTADO ===")
        pipeline = [
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]
        result = list(jobs.aggregate(pipeline))
        
        for r in result:
            print(f"{r['_id']}: {r['count']} jobs")

if __name__ == "__main__":
    main()