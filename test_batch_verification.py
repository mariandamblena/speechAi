"""
Script para verificar batch creado desde el frontend
"""
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Conectar a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "speechai")

print(f"Conectando a: {MONGO_URI}")
print(f"Base de datos: {MONGO_DB_NAME}")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]

# Buscar último batch creado
batch = db.batches.find_one(sort=[("created_at", -1)])

if batch:
    print("\n" + "="*60)
    print("✅ ÚLTIMO BATCH CREADO")
    print("="*60)
    print(f"ID: {batch['_id']}")
    print(f"Nombre: {batch.get('name')}")
    print(f"Cuenta: {batch.get('account_id')}")
    print(f"Creado: {batch.get('created_at')}")
    print(f"Estado: {batch.get('status')}")
    print("\n" + "-"*60)
    print("📋 CALL SETTINGS:")
    print("-"*60)
    
    call_settings = batch.get('call_settings', {})
    if call_settings:
        print(f"  max_call_duration: {call_settings.get('max_call_duration')}s")
        print(f"  ring_timeout: {call_settings.get('ring_timeout')}s")
        print(f"  max_attempts: {call_settings.get('max_attempts')}")
        print(f"  retry_delay_hours: {call_settings.get('retry_delay_hours')}h")
        print(f"  allowed_hours: {call_settings.get('allowed_hours')}")
        print(f"  days_of_week: {call_settings.get('days_of_week')}")
        print(f"  timezone: {call_settings.get('timezone')}")
    else:
        print("  ⚠️ Sin call_settings (usará defaults globales)")
    
    # Contar jobs asociados
    job_count = db.jobs.count_documents({"batch_id": str(batch['_id'])})
    print("\n" + "-"*60)
    print(f"📞 JOBS CREADOS: {job_count}")
    print("-"*60)
    
    # Mostrar primeros 3 jobs
    jobs = list(db.jobs.find({"batch_id": str(batch['_id'])}).limit(3))
    for i, job in enumerate(jobs, 1):
        print(f"\nJob {i}:")
        print(f"  ID: {job['_id']}")
        print(f"  Status: {job.get('status')}")
        print(f"  Contacto: {job.get('contact', {}).get('name')}")
        phones = job.get('contact', {}).get('phones', [])
        print(f"  Teléfonos: {phones}")
        print(f"  Intentos: {job.get('tries', 0)}")
        
        # Variables custom
        payload = job.get('payload', {})
        if payload:
            print(f"  Variables custom:")
            for key, value in payload.items():
                if key not in ['name', 'phones']:
                    print(f"    - {key}: {value}")
    
    print("\n" + "="*60)
    print("✅ VERIFICACIÓN COMPLETA")
    print("="*60)
    
    # Próximos pasos
    print("\n📝 PRÓXIMOS PASOS:")
    print("1. Iniciar worker: python app/call_worker.py")
    print("2. Ver logs en tiempo real")
    print("3. Verificar que workers usan call_settings del batch")
    
else:
    print("❌ No se encontró ningún batch")
