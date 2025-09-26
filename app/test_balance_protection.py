#!/usr/bin/env python3
"""
Script de prueba para validar la protección de balance del SaaS
"""
import os
from pymongo import MongoClient
from datetime import datetime, timezone
import uuid

# Configuración de MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "Debtors")
MONGO_COLL_JOBS = os.getenv("MONGO_COLL_JOBS", "call_jobs")

def setup_test_account_and_job():
    """Crear cuenta de prueba con 0 minutos y job asociado"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    # ID de cuenta de prueba
    test_account_id = "test_account_zero_minutes"
    test_job_id = str(uuid.uuid4())
    
    print(f"🧪 CONFIGURANDO PRUEBA DE PROTECCIÓN SAAS")
    print(f"Account ID: {test_account_id}")
    print(f"Job ID: {test_job_id}")
    print("="*50)
    
    # 1. Crear/actualizar cuenta con 0 minutos
    account_data = {
        "account_id": test_account_id,
        "plan_type": "minutes_based",
        "minutes_remaining": 0,  # 🔥 SIN MINUTOS - DEBE BLOQUEAR LLAMADAS
        "minutes_purchased": 100,
        "owner_email": "test@example.com",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "status": "active"
    }
    
    result = db.accounts.update_one(
        {"account_id": test_account_id},
        {"$set": account_data},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"✅ Cuenta creada: {test_account_id} (minutos: 0)")
    else:
        print(f"✅ Cuenta actualizada: {test_account_id} (minutos: 0)")
    
    # 2. Crear job de prueba asociado a la cuenta
    job_data = {
        "_id": test_job_id,
        "account_id": test_account_id,  # 🔗 ASOCIADO A CUENTA SIN MINUTOS
        "batch_id": "test_batch_protection",
        "status": "pending",
        "rut": "12345678-9",
        "nombre": "TEST USER",
        "contacto": {
            "phones": ["+56912345678", "+56987654321"],
            "next_phone_index": 0
        },
        "deuda": 150000,
        "created_at": datetime.now(timezone.utc),
        "lease_expires": None,
        "worker_id": None,
        "tries": 0,
        "max_tries": 3
    }
    
    result = db[MONGO_COLL_JOBS].update_one(
        {"_id": test_job_id},
        {"$set": job_data},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"✅ Job creado: {test_job_id}")
    else:
        print(f"✅ Job actualizado: {test_job_id}")
    
    print("\n🎯 EXPECTATIVA:")
    print("- El worker debe detectar que la cuenta tiene 0 minutos")
    print("- Debe marcar el job como 'failed' con error de saldo insuficiente")  
    print("- NO debe ejecutar ninguna llamada a Retell")
    print("- Debe loggear: 🚫 SALDO INSUFICIENTE")
    
    print(f"\n🚀 EJECUTA AHORA: python call_worker.py")
    print(f"Y observa que el job {test_job_id} sea rechazado por falta de balance")
    
    client.close()

def check_test_result():
    """Verificar resultado de la prueba"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    print(f"\n📊 VERIFICANDO RESULTADOS DE LA PRUEBA")
    print("="*50)
    
    # Buscar jobs de prueba
    jobs = list(db[MONGO_COLL_JOBS].find({"account_id": "test_account_zero_minutes"}))
    
    for job in jobs:
        job_id = job["_id"]
        status = job["status"]
        error = job.get("last_error", "Sin error")  # Campo correcto para errores
        
        print(f"Job ID: {job_id}")
        print(f"Status: {status}")
        print(f"Error: {error}")
        
        if status == "failed" and "saldo insuficiente" in error.lower():
            print("✅ ¡PROTECCIÓN FUNCIONANDO! Job bloqueado por falta de balance")
        elif status == "pending":
            print("⚠️  Job aún pendiente - ejecuta el worker para ver el resultado")
        else:
            print("❌ PROTECCIÓN FALLANDO - El job debería estar marcado como failed")
        
        print("-" * 30)
    
    client.close()

def cleanup_test():
    """Limpiar datos de prueba"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    # Eliminar cuenta de prueba
    result1 = db.accounts.delete_one({"account_id": "test_account_zero_minutes"})
    print(f"Cuentas eliminadas: {result1.deleted_count}")
    
    # Eliminar jobs de prueba
    result2 = db[MONGO_COLL_JOBS].delete_many({"account_id": "test_account_zero_minutes"})
    print(f"Jobs eliminados: {result2.deleted_count}")
    
    client.close()
    print("🧹 Datos de prueba eliminados")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python test_balance_protection.py setup    # Configurar prueba")
        print("  python test_balance_protection.py check    # Verificar resultado")
        print("  python test_balance_protection.py cleanup  # Limpiar datos")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "setup":
        setup_test_account_and_job()
    elif action == "check":
        check_test_result()
    elif action == "cleanup":
        cleanup_test()
    else:
        print(f"Acción desconocida: {action}")