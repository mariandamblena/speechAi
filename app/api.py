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
from pydantic import BaseModel

from domain.models import JobModel, AccountModel, BatchModel, ContactInfo, CallPayload
from domain.enums import JobStatus, AccountStatus, PlanType, CallMode
from services.account_service import AccountService
from services.batch_service import BatchService
from services.batch_creation_service import BatchCreationService
from services.acquisition_batch_service import AcquisitionBatchService
from services.job_service_api import JobService
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
acquisition_batch_service = None
job_service = None

@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al arrancar la API"""
    global db_manager, account_service, batch_service, batch_creation_service, acquisition_batch_service, job_service
    
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    await db_manager.connect()
    
    account_service = AccountService(db_manager)
    batch_service = BatchService(db_manager)
    batch_creation_service = BatchCreationService(db_manager)
    acquisition_batch_service = AcquisitionBatchService(db_manager)
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

async def get_acquisition_batch_service() -> AcquisitionBatchService:
    return acquisition_batch_service

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
    acquisition_service: AcquisitionBatchService = Depends(get_acquisition_batch_service)
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
            result = await acquisition_service.create_batch_from_excel_acquisition(
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
# GOOGLE SHEETS ENDPOINTS - Integración del workflow de adquisición
# ============================================================================

class GoogleSheetsRequest(BaseModel):
    account_id: str
    spreadsheet_id: str
    sheet_name: str = "Sheet1"
    batch_name: Optional[str] = None
    batch_description: Optional[str] = ""
    credentials_json_path: Optional[str] = None
    token_path: Optional[str] = None

@app.post("/api/v1/batches/googlesheets/preview")
async def preview_google_sheets_batch(request: GoogleSheetsRequest):
    """
    Preview de batch desde Google Sheets
    Procesa la hoja y muestra resumen sin crear el batch
    """
    try:
        from services.google_sheets_service import GoogleSheetsService
        
        logger.info(f"Previewing Google Sheets batch for account: {request.account_id}")
        
        # Verificar cuenta
        db_manager = DatabaseManager()
        account_service = AccountService(db_manager)
        account = await account_service.get_account(request.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Inicializar servicio Google Sheets
        gs_service = GoogleSheetsService()
        
        # Autenticar (si se proporcionan credenciales)
        if request.credentials_json_path:
            authenticated = gs_service.authenticate(
                request.credentials_json_path, 
                request.token_path
            )
            if not authenticated:
                raise HTTPException(
                    status_code=400, 
                    detail="Failed to authenticate with Google Sheets API"
                )
        
        # Leer datos de la hoja
        try:
            rows = gs_service.read_sheet_data(request.spreadsheet_id, request.sheet_name)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error reading Google Sheets data: {str(e)}"
            )
        
        if not rows:
            raise HTTPException(
                status_code=400,
                detail="No data found in the specified sheet"
            )
        
        # Procesar datos (sin guardar)
        try:
            debtors = gs_service.process_debt_collection_data(rows)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing sheet data: {str(e)}"
            )
        
        # Generar estadísticas de preview
        total_debtors = len(debtors)
        total_coupons = sum(d.get('cantidad_cupones', 0) for d in debtors)
        total_amount = sum(d.get('monto_total', 0) for d in debtors)
        
        # Estadísticas de teléfonos
        with_mobile = sum(1 for d in debtors if d['phones'].get('mobile_e164'))
        with_landline = sum(1 for d in debtors if d['phones'].get('landline_e164'))
        with_any_phone = sum(1 for d in debtors if d['phones'].get('best_e164'))
        
        # Muestra de datos (primeros 5)
        sample_data = debtors[:5] if debtors else []
        
        return {
            "success": True,
            "preview": {
                "spreadsheet_id": request.spreadsheet_id,
                "sheet_name": request.sheet_name,
                "raw_rows": len(rows),
                "processed_debtors": total_debtors,
                "statistics": {
                    "total_coupons": total_coupons,
                    "total_amount_pesos": total_amount,
                    "with_mobile_phone": with_mobile,
                    "with_landline_phone": with_landline,
                    "with_any_phone": with_any_phone,
                    "without_phone": total_debtors - with_any_phone
                },
                "sample_data": sample_data
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in Google Sheets preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/batches/googlesheets/create")
async def create_google_sheets_batch(
    request: GoogleSheetsRequest,
    allow_duplicates: bool = Query(False, description="Allow duplicate RUTs in processing")
):
    """
    Crea batch completo desde Google Sheets
    Replica exactamente la lógica del workflow N8N de adquisición
    """
    try:
        from services.google_sheets_service import GoogleSheetsService
        
        logger.info(f"Creating Google Sheets batch for account: {request.account_id}")
        
        # Verificar cuenta y balance
        db_manager = DatabaseManager()
        account_service = AccountService(db_manager)
        account = await account_service.get_account(request.account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Inicializar servicios
        gs_service = GoogleSheetsService()
        batch_service = BatchService(db_manager)
        job_service = JobService(db_manager)
        
        # Autenticar Google Sheets
        if request.credentials_json_path:
            authenticated = gs_service.authenticate(
                request.credentials_json_path, 
                request.token_path
            )
            if not authenticated:
                raise HTTPException(
                    status_code=400, 
                    detail="Failed to authenticate with Google Sheets API"
                )
        
        # Leer y procesar datos
        try:
            rows = gs_service.read_sheet_data(request.spreadsheet_id, request.sheet_name)
            if not rows:
                raise HTTPException(
                    status_code=400,
                    detail="No data found in the specified sheet"
                )
            
            debtors = gs_service.process_debt_collection_data(rows)
            if not debtors:
                raise HTTPException(
                    status_code=400,
                    detail="No valid debtors found after processing"
                )
            
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error processing sheet data: {str(e)}"
            )
        
        # Filtrar deudores sin teléfono válido
        valid_debtors = [d for d in debtors if d.get('to_number')]
        if not valid_debtors:
            raise HTTPException(
                status_code=400,
                detail="No debtors with valid phone numbers found"
            )
        
        # Detectar duplicados por RUT si no se permiten
        if not allow_duplicates:
            seen_ruts = set()
            unique_debtors = []
            duplicates = []
            
            for debtor in valid_debtors:
                rut = debtor['rut']
                if rut in seen_ruts:
                    duplicates.append(rut)
                else:
                    seen_ruts.add(rut)
                    unique_debtors.append(debtor)
            
            if duplicates:
                logger.warning(f"Found {len(duplicates)} duplicate RUTs")
                # No rechazar todo, solo procesar únicos
                valid_debtors = unique_debtors
        
        # Crear batch
        batch_name = request.batch_name or f"GoogleSheets-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        batch_data = BatchModel(
            batch_id=f"gs-{request.account_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            account_id=request.account_id,
            name=batch_name,
            description=request.batch_description or f"Google Sheets import from {request.spreadsheet_id}",
            total_jobs=len(valid_debtors),
            priority=1,
            status="active",
            source_type="google_sheets",
            source_config={
                "spreadsheet_id": request.spreadsheet_id,
                "sheet_name": request.sheet_name,
                "original_rows": len(rows),
                "processed_debtors": len(debtors),
                "valid_debtors": len(valid_debtors)
            },
            created_at=datetime.now()
        )
        
        created_batch = await batch_service.create_batch(batch_data)
        
        # Insertar deudores en colección Debtors (como hace el workflow N8N)
        try:
            collection = db_manager.db["Debtors"]
            for debtor in valid_debtors:
                debtor['batch_id'] = created_batch.batch_id
                await collection.replace_one(
                    {"rut": debtor['rut']},
                    debtor,
                    upsert=True
                )
        except Exception as e:
            logger.error(f"Error inserting debtors: {e}")
            # No fallar por esto, continuar con jobs
        
        # Crear jobs de llamadas
        try:
            call_jobs = gs_service.create_call_jobs(valid_debtors)
            
            # Insertar jobs en call_jobs collection
            jobs_collection = db_manager.db["call_jobs"]
            created_jobs = []
            
            for job_data in call_jobs:
                job_data['batch_id'] = created_batch.batch_id
                
                # Crear modelo de job
                job = JobModel(
                    job_id=job_data['job_id'],
                    batch_id=created_batch.batch_id,
                    account_id=request.account_id,
                    call_mode="voice",
                    contact_info=ContactInfo(
                        phone_number=job_data['to_number'],
                        name=job_data['nombre'],
                        additional_data={
                            'rut': job_data['rut'],
                            'rut_fmt': job_data['rut_fmt'],
                            'origen_empresa': job_data['origen_empresa'],
                            'cantidad_cupones': job_data['cantidad_cupones'],
                            'monto_total': job_data['monto_total'],
                            'fecha_limite': job_data['fecha_limite'],
                            'fecha_maxima': job_data['fecha_maxima']
                        }
                    ),
                    priority=1,
                    max_attempts=3,
                    status=JobStatus.PENDING,
                    created_at=datetime.now()
                )
                
                created_job = await job_service.create_job(job)
                created_jobs.append(created_job)
                
                # También insertar en call_jobs collection (para compatibilidad N8N)
                await jobs_collection.replace_one(
                    {"job_id": job_data['job_id']},
                    job_data,
                    upsert=True
                )
                
        except Exception as e:
            logger.error(f"Error creating jobs: {e}")
            # Rollback batch si falló la creación de jobs
            await batch_service.delete_batch(created_batch.batch_id)
            raise HTTPException(
                status_code=500,
                detail=f"Error creating call jobs: {str(e)}"
            )
        
        # Actualizar conteo de jobs en batch
        await batch_service.update_batch_stats(created_batch.batch_id)
        
        # Estadísticas finales
        total_amount = sum(d.get('monto_total', 0) for d in valid_debtors)
        with_phone_count = len(valid_debtors)
        
        return {
            "success": True,
            "batch": serialize_objectid(created_batch.__dict__),
            "statistics": {
                "original_rows": len(rows),
                "processed_debtors": len(debtors),
                "valid_debtors": len(valid_debtors),
                "created_jobs": len(created_jobs),
                "total_amount_pesos": total_amount,
                "duplicates_found": len(debtors) - len(valid_debtors) if not allow_duplicates else 0
            },
            "message": f"Successfully created batch '{batch_name}' with {len(created_jobs)} call jobs"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Google Sheets batch: {e}")
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