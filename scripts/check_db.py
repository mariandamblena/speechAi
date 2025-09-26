#!/usr/bin/env python3
"""Script para verificar batches y jobs en la DB"""

import asyncio
import sys
import os

# Agregar el directorio app al path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app'))

from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings

async def check_db():
    try:
        settings = get_settings()
        db = DatabaseManager(settings.database.uri, settings.database.database)
        await db.connect()
        
        print("=== VERIFICACIÓN DE BASE DE DATOS ===\n")
        
        # Verificar si hay batches
        batches = await db.get_collection('batches').find().to_list(None)
        print(f"📦 Batches encontrados: {len(batches)}")
        
        if batches:
            for i, batch in enumerate(batches, 1):
                print(f"  {i}. ID: {batch.get('batch_id', 'N/A')}")
                print(f"     Nombre: {batch.get('name', 'N/A')}")
                print(f"     Account: {batch.get('account_id', 'N/A')}")
                print(f"     Jobs Total: {batch.get('total_jobs', 0)}")
                print(f"     Jobs Pendientes: {batch.get('pending_jobs', 0)}")
                print(f"     Creado: {batch.get('created_at', 'N/A')}")
                print()
        
        # Verificar si hay jobs
        jobs = await db.get_collection('call_jobs').find().to_list(None)
        print(f"📞 Jobs encontrados: {len(jobs)}")
        
        if jobs:
            for i, job in enumerate(jobs[:10], 1):  # Solo primeros 10
                contact = job.get('contact', {})
                print(f"  {i}. Job ID: {job.get('job_id', job.get('_id', 'N/A'))}")
                print(f"     Batch: {job.get('batch_id', 'N/A')}")
                print(f"     Nombre: {contact.get('name', 'N/A') if contact else 'N/A'}")
                print(f"     Status: {job.get('status', 'N/A')}")
                print(f"     Account: {job.get('account_id', 'N/A')}")
                print()
        
        # Verificar si hay deudores
        debtors = await db.get_collection('Debtors').find().to_list(None)
        print(f"👤 Deudores encontrados: {len(debtors)}")
        
        if debtors:
            for i, debtor in enumerate(debtors[:5], 1):  # Solo primeros 5
                print(f"  {i}. RUT: {debtor.get('rut', 'N/A')}")
                print(f"     Nombre: {debtor.get('nombre', 'N/A')}")
                print(f"     Batch: {debtor.get('batch_id', 'N/A')}")
                print(f"     Monto: {debtor.get('monto_total', 'N/A')}")
                print()
        
        await db.close()
        
    except Exception as e:
        print(f"❌ Error verificando DB: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_db())