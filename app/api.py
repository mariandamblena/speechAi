"""
API REST principal usando FastAPI
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import csv
import io

from domain.models import JobModel, AccountModel, BatchModel, ContactInfo, CallPayload
from domain.enums import JobStatus, AccountStatus, PlanType, CallMode
from services.account_service import AccountService
from services.batch_service import BatchService
from services.job_service_api import JobService
from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

# Crear app FastAPI
app = FastAPI(
    title="Speech AI Call Tracking API",
    description="API REST para gestión de llamadas automatizadas con sistema de créditos",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios exactos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependencias globales
settings = get_settings()
db_manager = None
account_service = None
batch_service = None
job_service = None

@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al arrancar la API"""
    global db_manager, account_service, batch_service, job_service
    
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    await db_manager.connect()
    
    account_service = AccountService(db_manager)
    batch_service = BatchService(db_manager)
    job_service = JobService(db_manager)
    
    logging.info("API initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cerrar conexiones al apagar la API"""
    if db_manager:
        await db_manager.close()
    logging.info("API shutdown completed")

# Dependencias para inyectar servicios
async def get_account_service() -> AccountService:
    return account_service

async def get_batch_service() -> BatchService:
    return batch_service

async def get_job_service() -> JobService:
    return job_service


# ============================================================================
# ENDPOINTS - HEALTH CHECK
# ============================================================================

@app.get("/")
async def root():
    """Endpoint raíz"""
    return {
        "message": "Speech AI Call Tracking API",
        "version": "1.0.0",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Verificar conexión a MongoDB
        if db_manager:
            await db_manager.db.command("ping")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# ============================================================================
# ENDPOINTS - ACCOUNT MANAGEMENT
# ============================================================================

@app.post("/api/v1/accounts", response_model=Dict)
async def create_account(
    account_id: str,
    account_name: str,
    plan_type: str = "minutes_based",
    initial_minutes: float = 0.0,
    initial_credits: float = 0.0,
    service: AccountService = Depends(get_account_service)
):
    """Crear una nueva cuenta"""
    try:
        plan_enum = PlanType(plan_type)
        account = await service.create_account(
            account_id, account_name, plan_enum, initial_minutes, initial_credits
        )
        return {"success": True, "account": account.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/accounts/{account_id}")
async def get_account(
    account_id: str,
    service: AccountService = Depends(get_account_service)
):
    """Obtener información de una cuenta"""
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account.to_dict()

@app.get("/api/v1/accounts/{account_id}/balance")
async def get_account_balance(
    account_id: str,
    service: AccountService = Depends(get_account_service)
):
    """Consultar saldo de una cuenta"""
    balance = await service.check_balance(account_id)
    if "error" in balance:
        raise HTTPException(status_code=404, detail=balance["error"])
    
    return balance

@app.post("/api/v1/accounts/{account_id}/topup")
async def topup_account(
    account_id: str,
    minutes: float = None,
    credits: float = None,
    service: AccountService = Depends(get_account_service)
):
    """Agregar minutos o créditos a una cuenta"""
    if minutes is None and credits is None:
        raise HTTPException(status_code=400, detail="Must provide either minutes or credits")
    
    success = False
    if minutes is not None:
        success = await service.add_minutes(account_id, minutes)
    if credits is not None:
        success = await service.add_credits(account_id, credits) or success
    
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return {"success": True, "message": "Account topped up successfully"}

@app.get("/api/v1/accounts/{account_id}/stats")
async def get_account_stats(
    account_id: str,
    service: AccountService = Depends(get_account_service)
):
    """Obtener estadísticas detalladas de una cuenta"""
    stats = await service.get_account_stats(account_id)
    if "error" in stats:
        raise HTTPException(status_code=404, detail=stats["error"])
    
    return stats

@app.put("/api/v1/accounts/{account_id}/suspend")
async def suspend_account(
    account_id: str,
    reason: str = "",
    service: AccountService = Depends(get_account_service)
):
    """Suspender una cuenta"""
    success = await service.suspend_account(account_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return {"success": True, "message": "Account suspended"}

@app.put("/api/v1/accounts/{account_id}/activate")
async def activate_account(
    account_id: str,
    service: AccountService = Depends(get_account_service)
):
    """Activar una cuenta suspendida"""
    success = await service.activate_account(account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return {"success": True, "message": "Account activated"}


# ============================================================================
# ENDPOINTS - BATCH MANAGEMENT
# ============================================================================

@app.post("/api/v1/batches")
async def create_batch(
    account_id: str,
    name: str,
    description: str = "",
    priority: int = 1,
    service: BatchService = Depends(get_batch_service)
):
    """Crear un nuevo batch"""
    try:
        batch = await service.create_batch(account_id, name, description, priority)
        return {"success": True, "batch": batch.to_dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/batches")
async def list_batches(
    account_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0, ge=0),
    service: BatchService = Depends(get_batch_service)
):
    """Listar batches con filtros opcionales"""
    batches = await service.list_batches(account_id, is_active, limit, skip)
    return [batch.to_dict() for batch in batches]

@app.get("/api/v1/batches/{batch_id}")
async def get_batch(
    batch_id: str,
    service: BatchService = Depends(get_batch_service)
):
    """Obtener información de un batch"""
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return batch.to_dict()

@app.get("/api/v1/batches/{batch_id}/summary")
async def get_batch_summary(
    batch_id: str,
    service: BatchService = Depends(get_batch_service)
):
    """Obtener resumen completo de un batch"""
    summary = await service.get_batch_summary(batch_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    
    return summary

@app.post("/api/v1/batches/{batch_id}/upload")
async def upload_jobs_to_batch(
    batch_id: str,
    file: UploadFile = File(...),
    service: BatchService = Depends(get_batch_service),
    account_svc: AccountService = Depends(get_account_service)
):
    """Subir jobs desde archivo CSV a un batch"""
    
    # Verificar que el batch existe
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Verificar que la cuenta existe
    account = await account_svc.get_account(batch.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Leer archivo CSV
    try:
        content = await file.read()
        csv_content = io.StringIO(content.decode('utf-8'))
        reader = csv.DictReader(csv_content)
        
        jobs = []
        for row in reader:
            # Parsear teléfonos (pueden venir separados por ;)
            phones = [p.strip() for p in row.get('telefonos', row.get('phones', '')).split(';') if p.strip()]
            
            contact = ContactInfo(
                name=row.get('nombre', row.get('name', '')),
                dni=row.get('rut', row.get('dni', row.get('cedula', ''))),
                phones=phones
            )
            
            payload = CallPayload(
                debt_amount=float(row.get('monto_deuda', row.get('debt_amount', 0))),
                due_date=row.get('fecha_limite', row.get('due_date', '')),
                company_name=row.get('empresa', row.get('company', '')),
                reference_number=row.get('referencia', row.get('reference', ''))
            )
            
            job = JobModel(
                account_id=account.account_id,
                contact=contact,
                payload=payload,
                mode=CallMode.CONTINUOUS  # Por defecto, múltiples intentos
            )
            
            # Estimar costo
            estimated_minutes = 3.0  # Estimación promedio
            job.estimated_cost = account.estimate_call_cost(estimated_minutes)
            
            jobs.append(job)
        
        # Agregar jobs al batch
        count = await service.add_jobs_to_batch(batch_id, jobs)
        
        return {
            "success": True,
            "message": f"Added {count} jobs to batch {batch_id}",
            "jobs_added": count
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

@app.put("/api/v1/batches/{batch_id}/pause")
async def pause_batch(
    batch_id: str,
    service: BatchService = Depends(get_batch_service)
):
    """Pausar un batch"""
    success = await service.pause_batch(batch_id)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return {"success": True, "message": "Batch paused"}

@app.put("/api/v1/batches/{batch_id}/resume")
async def resume_batch(
    batch_id: str,
    service: BatchService = Depends(get_batch_service)
):
    """Reanudar un batch pausado"""
    success = await service.resume_batch(batch_id)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return {"success": True, "message": "Batch resumed"}

@app.delete("/api/v1/batches/{batch_id}")
async def delete_batch(
    batch_id: str,
    delete_jobs: bool = Query(False),
    service: BatchService = Depends(get_batch_service)
):
    """Eliminar un batch"""
    success = await service.delete_batch(batch_id, delete_jobs)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return {"success": True, "message": "Batch deleted"}


# ============================================================================
# ENDPOINTS - JOB MANAGEMENT
# ============================================================================

@app.get("/api/v1/jobs")
async def list_jobs(
    account_id: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0, ge=0),
    service: JobService = Depends(get_job_service)
):
    """Listar jobs con filtros opcionales"""
    status_enum = JobStatus(status) if status else None
    jobs = await service.list_jobs(account_id, batch_id, status_enum, limit, skip)
    return [job.to_dict() for job in jobs]

@app.get("/api/v1/jobs/{job_id}")
async def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service)
):
    """Obtener información de un job específico"""
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.to_dict()

@app.put("/api/v1/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    service: JobService = Depends(get_job_service)
):
    """Reintentar un job manualmente"""
    success = await service.retry_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be retried")
    
    return {"success": True, "message": "Job marked for retry"}

@app.delete("/api/v1/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    service: JobService = Depends(get_job_service)
):
    """Cancelar un job pendiente"""
    success = await service.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    
    return {"success": True, "message": "Job cancelled"}


# ============================================================================
# ENDPOINTS - DASHBOARD & REPORTING
# ============================================================================

@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats(
    account_id: Optional[str] = Query(None),
    job_service: JobService = Depends(get_job_service),
    account_svc: AccountService = Depends(get_account_service)
):
    """Obtener estadísticas para el dashboard"""
    
    stats = {}
    
    if account_id:
        # Stats específicas de una cuenta
        account_stats = await account_svc.get_account_stats(account_id)
        balance = await account_svc.check_balance(account_id)
        job_stats = await job_service.get_account_job_stats(account_id)
        
        stats = {
            "account": account_stats,
            "balance": balance,
            "jobs": job_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    else:
        # Stats globales del sistema
        all_accounts = await account_svc.list_accounts(limit=1000)
        total_accounts = len(all_accounts)
        active_accounts = len([a for a in all_accounts if a.status == AccountStatus.ACTIVE])
        
        stats = {
            "system": {
                "total_accounts": total_accounts,
                "active_accounts": active_accounts,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    return stats

@app.get("/api/v1/calls/history")
async def get_call_history(
    account_id: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0, ge=0),
    service: JobService = Depends(get_job_service)
):
    """Obtener historial de llamadas"""
    
    filters = {}
    if account_id:
        filters["account_id"] = account_id
    if batch_id:
        filters["batch_id"] = batch_id
    
    # Filtros de fecha (si se proporcionan)
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = datetime.fromisoformat(start_date)
        if end_date:
            date_filter["$lte"] = datetime.fromisoformat(end_date)
        filters["completed_at"] = date_filter
    
    history = await service.get_call_history(filters, limit, skip)
    return history


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )