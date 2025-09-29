"""
API REST principal usando FastAPI
"""

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import csv
import io
from pydantic import BaseModel

from domain.models import JobModel, AccountModel, BatchModel, ContactInfo, CallPayload
from domain.enums import JobStatus, AccountStatus, PlanType, CallMode
from services.account_service import AccountService
from services.batch_service import BatchService
from services.batch_creation_service import BatchCreationService
from services.chile_batch_service import ChileBatchService
from services.job_service import JobService
from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings
from utils.helpers import serialize_objectid

# ============================================================================
# REQUEST MODELS (Pydantic)
# ============================================================================

class CreateAccountRequest(BaseModel):
    account_id: str
    account_name: str
    plan_type: str = "minutes_based"
    initial_minutes: float = 0.0
    initial_credits: float = 0.0

class TopupRequest(BaseModel):
    minutes: Optional[float] = None
    credits: Optional[float] = None

class CreateBatchRequest(BaseModel):
    account_id: str
    name: str
    description: str = ""
    priority: int = 1

class CreateJobRequest(BaseModel):
    job_id: str
    batch_id: str
    account_id: str
    call_mode: str
    prompt: str
    contacts: List[ContactInfo]
    metadata: Optional[Dict[str, Any]] = None

class ExcelBatchRequest(BaseModel):
    account_id: str
    batch_name: Optional[str] = None
    batch_description: Optional[str] = None
    allow_duplicates: bool = False

# ============================================================================
# CONFIGURACIÓN Y STARTUP
# ============================================================================

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

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
batch_creation_service = None
chile_batch_service = None
job_service = None

@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al arrancar la API"""
    global db_manager, account_service, batch_service, batch_creation_service, chile_batch_service, job_service
    
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    await db_manager.connect()
    
    account_service = AccountService(db_manager)
    batch_service = BatchService(db_manager)
    batch_creation_service = BatchCreationService(db_manager)
    chile_batch_service = ChileBatchService(db_manager)
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

async def get_batch_creation_service() -> BatchCreationService:
    return batch_creation_service

async def get_chile_batch_service() -> ChileBatchService:
    return chile_batch_service

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
    request: CreateAccountRequest,
    service: AccountService = Depends(get_account_service)
):
    """Crear una nueva cuenta"""
    try:
        plan_enum = PlanType(request.plan_type)
        account = await service.create_account(
            request.account_id, 
            request.account_name, 
            plan_enum, 
            request.initial_minutes, 
            request.initial_credits
        )
        return {"success": True, "account": serialize_objectid(account.to_dict())}
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
    
    return serialize_objectid(account.to_dict())

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
    request: TopupRequest,
    service: AccountService = Depends(get_account_service)
):
    """Agregar minutos o créditos a una cuenta"""
    if request.minutes is None and request.credits is None:
        raise HTTPException(status_code=400, detail="Must provide either minutes or credits")
    
    success = False
    if request.minutes is not None:
        success = await service.add_minutes(account_id, request.minutes)
    if request.credits is not None:
        success = await service.add_credits(account_id, request.credits) or success
    
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
    request: CreateBatchRequest,
    service: BatchService = Depends(get_batch_service)
):
    """Crear un nuevo batch"""
    try:
        batch = await service.create_batch(
            request.account_id, 
            request.name, 
            request.description, 
            request.priority
        )
        return {"success": True, "batch": serialize_objectid(batch.to_dict())}
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
    return [serialize_objectid(batch.to_dict()) for batch in batches]

@app.get("/api/v1/batches/{batch_id}")
async def get_batch(
    batch_id: str,
    service: BatchService = Depends(get_batch_service)
):
    """Obtener información de un batch"""
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return serialize_objectid(batch.to_dict())

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
# ENDPOINTS - EXCEL BATCH CREATION (Implementa lógica del workflow Adquisicion_v3)
# ============================================================================

@app.post("/api/v1/batches/excel/preview")
async def preview_excel_batch(
    file: UploadFile = File(...),
    account_id: str = Query(..., description="ID de la cuenta"),
    service: BatchCreationService = Depends(get_batch_creation_service)
):
    """
    Vista previa de archivo Excel sin crear el batch
    Muestra qué se va a procesar y detecta duplicados
    """
    try:
        # Verificar tipo de archivo
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel (.xlsx, .xls)")
        
        # Leer contenido del archivo
        content = await file.read()
        
        # Generar vista previa
        preview = await service.get_batch_preview(content, account_id)
        
        if not preview['success']:
            raise HTTPException(status_code=400, detail=preview['error'])
        
        return {
            "success": True,
            "filename": file.filename,
            "preview": preview['preview']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")

@app.post("/api/v1/batches/excel/create")
async def create_batch_from_excel(
    file: UploadFile = File(...),
    account_id: str = Query(..., description="ID de la cuenta"),
    batch_name: Optional[str] = Query(None, description="Nombre del batch"),
    batch_description: Optional[str] = Query(None, description="Descripción del batch"),
    allow_duplicates: bool = Query(False, description="Permitir duplicados"),
    processing_type: str = Query("basic", description="Tipo de procesamiento: 'basic' o 'acquisition'"),
    basic_service: BatchCreationService = Depends(get_batch_creation_service),
    chile_service: ChileBatchService = Depends(get_chile_batch_service)
):
    """
    Crear batch completo desde archivo Excel con opción de procesamiento
    
    Tipos de procesamiento:
    - 'basic': Procesamiento simple y directo (por defecto)
    - 'acquisition': Lógica avanzada con agrupación por RUT, normalización chilena,
                     cálculo de fechas límite según workflow N8N de adquisición
    """
    try:
        # Verificar tipo de archivo
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel (.xlsx, .xls)")
        
        # Verificar tipo de procesamiento
        if processing_type not in ["basic", "acquisition"]:
            raise HTTPException(
                status_code=400, 
                detail="processing_type debe ser 'basic' o 'acquisition'"
            )
        
        # Leer contenido del archivo
        content = await file.read()
        
        # Seleccionar servicio según tipo de procesamiento
        if processing_type == "acquisition":
            # Usar lógica de adquisición avanzada
            result = await chile_service.create_batch_from_excel_acquisition(
                file_content=content,
                account_id=account_id,
                batch_name=batch_name or f"Acquisition Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                batch_description=batch_description,
                allow_duplicates=allow_duplicates
            )
        else:
            # Usar lógica básica (por defecto)
            result = await basic_service.create_batch_from_excel(
                file_content=content,
                account_id=account_id,
                batch_name=batch_name or f"Basic Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                batch_description=batch_description,
                allow_duplicates=allow_duplicates
            )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return {
            "success": True,
            "message": f"Batch '{result['batch_name']}' creado exitosamente con procesamiento {processing_type}",
            "batch_id": result['batch_id'],
            "batch_name": result['batch_name'],
            "processing_type": result.get('processing_type', processing_type),
            "stats": result.get('stats', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating batch from Excel: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creando batch: {str(e)}")

@app.get("/api/v1/batches/{batch_id}/status")
async def get_batch_detailed_status(
    batch_id: str,
    account_id: str = Query(..., description="ID de la cuenta"),
    service: BatchCreationService = Depends(get_batch_creation_service)
):
    """
    Obtener estado detallado de un batch creado desde Excel
    Incluye estadísticas actualizadas de jobs y progreso
    """
    try:
        status = await service.get_batch_status(batch_id, account_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        return {
            "success": True,
            "batch": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting batch status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado del batch: {str(e)}")


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
    return [serialize_objectid(job.to_dict()) for job in jobs]

@app.get("/api/v1/jobs/{job_id}")
async def get_job(
    job_id: str,
    service: JobService = Depends(get_job_service)
):
    """Obtener información de un job específico"""
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Serializar ObjectId para JSON
    return serialize_objectid(job.to_dict())

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


# ============================================================================
# ENDPOINTS - NEW USE CASE ARCHITECTURE
# ============================================================================

@app.post("/api/v1/batches/chile/{use_case}")
async def create_chile_batch_for_use_case(
    use_case: str,
    file: UploadFile = File(...),
    account_id: str = Form(...),
    company_name: str = Form(...),
    batch_name: Optional[str] = Form(None),
    batch_description: Optional[str] = Form(None),
    allow_duplicates: bool = Form(False),
    # Campos específicos por caso de uso
    discount_percentage: Optional[float] = Form(0.0),  # Para marketing
    offer_description: Optional[str] = Form(""),       # Para marketing
    product_category: Optional[str] = Form("general"), # Para marketing
    retell_agent_id: Optional[str] = Form(None),
    chile_service: ChileBatchService = Depends(get_chile_batch_service)
):
    """
    NUEVO: Crea batch chileno para cualquier caso de uso
    
    Casos de uso soportados:
    - debt_collection: Cobranza de deudas
    - marketing: Campañas de marketing
    
    Normalización chilena automática:
    - RUT: 12.345.678-9 → 123456789
    - Teléfonos: 09-2125907 → +56992125907
    - Fechas: 01/09/2025 → 2025-09-01
    """
    try:
        # Validar caso de uso
        valid_use_cases = ['debt_collection', 'marketing']
        if use_case not in valid_use_cases:
            raise HTTPException(
                status_code=400,
                detail=f"Caso de uso '{use_case}' no válido. Disponibles: {valid_use_cases}"
            )
        
        # Leer archivo
        file_content = await file.read()
        
        # Configuración específica por caso de uso
        if use_case == 'debt_collection':
            use_case_config = {
                'company_name': company_name,
                'retell_agent_id': retell_agent_id,
                'max_attempts': 3
            }
        elif use_case == 'marketing':
            use_case_config = {
                'company_name': company_name,
                'offer_description': offer_description,
                'discount_percentage': discount_percentage,
                'product_category': product_category,
                'retell_agent_id': retell_agent_id,
                'max_attempts': 2,
                'campaign_type': 'promotional'
            }
        
        # Procesar con ChileBatchService
        result = await chile_service.create_batch_for_use_case(
            file_content=file_content,
            account_id=account_id,
            use_case=use_case,
            use_case_config=use_case_config,
            batch_name=batch_name,
            batch_description=batch_description,
            allow_duplicates=allow_duplicates
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": f"Batch chileno de {use_case} creado exitosamente",
                "batch_id": result["batch_id"],
                "use_case": use_case,
                "country": "CL",
                "stats": result["stats"]
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Error desconocido"))
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating Chile batch for {use_case}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/api/v1/use-cases")
async def get_available_use_cases():
    """Lista todos los casos de uso disponibles"""
    try:
        from domain.use_case_registry import get_use_case_registry
        registry = get_use_case_registry()
        
        return {
            "success": True,
            "use_cases": registry.get_available_use_cases(),
            "description": {
                "debt_collection": "Cobranza de deudas con normalización chilena",
                "marketing": "Campañas de marketing personalizadas"
            }
        }
    except Exception as e:
        logging.error(f"Error getting use cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )