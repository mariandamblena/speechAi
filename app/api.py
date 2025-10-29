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
import uuid
from pydantic import BaseModel

from domain.models import JobModel, AccountModel, BatchModel, ContactInfo, CallPayload
from domain.enums import JobStatus, AccountStatus, PlanType, CallMode
from services.account_service import AccountService
from services.batch_service import BatchService
from services.batch_creation_service import BatchCreationService
from services.chile_batch_service import ChileBatchService
from services.argentina_batch_service import ArgentinaBatchService
from services.job_service import JobService
from services.transaction_service import TransactionService
from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings
from utils.helpers import serialize_objectid

# ============================================================================
# REQUEST MODELS (Pydantic)
# ============================================================================

class CreateAccountRequest(BaseModel):
    """Request para crear una nueva cuenta - alineado con frontend"""
    account_name: str
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    plan_type: str = "credit_based"  # "credit_based" o "minutes_based"
    initial_minutes: Optional[float] = None
    initial_credits: Optional[float] = None
    country: str = "CL"  # Código ISO del país: CL (Chile), AR (Argentina)
    timezone: Optional[str] = None  # Ej: "America/Santiago", "America/Argentina/Buenos_Aires"
    max_concurrent_calls: Optional[int] = 5  # Límite de llamadas concurrentes
    features: Optional[Dict[str, Any]] = None  # Otras características opcionales
    settings: Optional[Dict[str, Any]] = None  # Configuraciones adicionales

class TopupRequest(BaseModel):
    minutes: Optional[float] = None
    credits: Optional[float] = None

class CreateBatchRequest(BaseModel):
    account_id: str
    name: str
    description: str = ""
    priority: int = 1
    call_settings: Optional[Dict[str, Any]] = None  # Configuración de llamadas específica del batch
    # call_settings puede contener:
    # - allowed_call_hours: {"start": "09:00", "end": "18:00"}
    # - timezone: "America/Santiago"
    # - retry_settings: {"max_attempts": 3, "retry_delay_hours": 24}
    # - max_concurrent_calls: número de llamadas concurrentes para este batch

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
    call_settings: Optional[Dict[str, Any]] = None  # Configuración de llamadas

class UpdateBatchRequest(BaseModel):
    """Request para actualizar un batch"""
    is_active: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    call_settings: Optional[Dict[str, Any]] = None  # Configuración de llamadas

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
argentina_batch_service = None
job_service = None
transaction_service = None

@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al arrancar la API"""
    global db_manager, account_service, batch_service, batch_creation_service, chile_batch_service, argentina_batch_service, job_service, transaction_service
    
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    await db_manager.connect()
    
    account_service = AccountService(db_manager)
    batch_service = BatchService(db_manager)
    batch_creation_service = BatchCreationService(db_manager)
    chile_batch_service = ChileBatchService(db_manager)
    argentina_batch_service = ArgentinaBatchService(db_manager)
    job_service = JobService(db_manager)
    transaction_service = TransactionService(db_manager)
    
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

async def get_argentina_batch_service() -> ArgentinaBatchService:
    return argentina_batch_service

async def get_job_service() -> JobService:
    return job_service

async def get_transaction_service() -> TransactionService:
    return transaction_service


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
        # Generar account_id automáticamente
        import uuid
        account_id = f"acc-{uuid.uuid4().hex[:12]}"
        
        # Convertir plan_type a enum
        plan_enum = PlanType(request.plan_type)
        
        # Determinar créditos/minutos iniciales según el plan
        initial_minutes = request.initial_minutes or 0.0
        initial_credits = request.initial_credits or 0.0
        
        if plan_enum == PlanType.MINUTES_BASED and request.initial_minutes:
            initial_minutes = request.initial_minutes
        elif plan_enum == PlanType.CREDIT_BASED and request.initial_credits:
            initial_credits = request.initial_credits
        
        # Crear cuenta con el nuevo modelo
        account = await service.create_account(
            account_id=account_id,
            account_name=request.account_name,
            plan_type=plan_enum,
            initial_minutes=initial_minutes,
            initial_credits=initial_credits,
            contact_name=request.contact_name,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            country=request.country,
            timezone=request.timezone,
            max_concurrent_calls=request.max_concurrent_calls,
            features=request.features,
            settings=request.settings
        )
        
        return {"success": True, "account": serialize_objectid(account.to_dict())}
    except ValueError as e:
        logger.error(f"Validation error creating account: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating account: {e}")
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

@app.get("/api/v1/accounts/{account_id}/last-call-settings")
async def get_last_call_settings(
    account_id: str
):
    """
    Obtener la última configuración de call_settings utilizada por esta cuenta.
    Útil para pre-llenar el formulario de configuración en el frontend.
    
    Returns:
        - call_settings: Última configuración utilizada
        - from_batch: ID del batch del que se obtuvo la configuración
        - created_at: Fecha de creación de ese batch
    """
    try:
        # Buscar el último batch de esta cuenta que tenga call_settings
        batches_coll = db_manager.batches
        
        last_batch = await batches_coll.find_one(
            {
                "account_id": account_id,
                "call_settings": {"$exists": True, "$ne": None}
            },
            sort=[("created_at", -1)]  # Más reciente primero
        )
        
        if not last_batch:
            return {
                "success": False,
                "message": "No previous call_settings found for this account",
                "call_settings": None
            }
        
        return {
            "success": True,
            "call_settings": last_batch.get("call_settings"),
            "from_batch": last_batch.get("batch_id"),
            "created_at": last_batch.get("created_at").isoformat() if last_batch.get("created_at") else None
        }
        
    except Exception as e:
        logger.error(f"Error getting last call_settings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obtaining call settings: {str(e)}")


# ============================================================================
# ENDPOINTS - BATCH MANAGEMENT
# ============================================================================

@app.post("/api/v1/batches")
async def create_batch(
    request: CreateBatchRequest,
    service: BatchService = Depends(get_batch_service)
):
    """Crear un nuevo batch con configuración de llamadas opcional"""
    try:
        batch = await service.create_batch(
            request.account_id, 
            request.name, 
            request.description, 
            request.priority,
            request.call_settings  # Pasar call_settings al servicio
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

@app.get("/api/v1/batches/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    service: BatchService = Depends(get_batch_service)
):
    """
    Obtener estado en tiempo real del batch (optimizado para polling frecuente)
    
    Este endpoint está optimizado para ser llamado frecuentemente (cada 5 segundos)
    por el frontend. Solo retorna los campos esenciales para actualización de UI.
    """
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Retornar solo campos esenciales para minimizar payload
    return {
        "batch_id": batch.batch_id,
        "is_active": batch.is_active,
        "total_jobs": batch.total_jobs,
        "pending_jobs": batch.pending_jobs,
        "completed_jobs": batch.completed_jobs,
        "failed_jobs": batch.failed_jobs,
        "suspended_jobs": batch.suspended_jobs,
        "total_cost": batch.total_cost,
        "total_minutes": batch.total_minutes,
        "progress_percentage": round((batch.completed_jobs / batch.total_jobs * 100) if batch.total_jobs > 0 else 0, 2),
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "completed_at": batch.completed_at.isoformat() if batch.completed_at else None
    }

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

@app.post("/api/v1/batches/{batch_id}/cancel")
async def cancel_batch(
    batch_id: str,
    reason: Optional[str] = Query(None, description="Razón de cancelación"),
    service: BatchService = Depends(get_batch_service)
):
    """
    Cancelar un batch completamente (diferente de pause)
    
    Diferencias entre pause y cancel:
    - pause: Detiene temporalmente, se puede reanudar
    - cancel: Detiene permanentemente, marca jobs como cancelados
    
    Args:
        batch_id: ID del batch a cancelar
        reason: Razón opcional de la cancelación
    """
    success = await service.cancel_batch(batch_id, reason)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    return {
        "success": True, 
        "message": "Batch cancelled successfully",
        "reason": reason
    }

@app.patch("/api/v1/batches/{batch_id}")
async def update_batch(
    batch_id: str,
    request: UpdateBatchRequest,
    service: BatchService = Depends(get_batch_service)
):
    """
    Actualizar propiedades de un batch (incluyendo pausar/reanudar)
    
    Args:
        batch_id: ID del batch a actualizar (puede ser batch_id o _id de MongoDB)
        request: Datos a actualizar (is_active, name, description, priority)
    """
    update_data = {}
    
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.priority is not None:
        update_data["priority"] = request.priority
    if request.call_settings is not None:
        update_data["call_settings"] = request.call_settings
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Intentar actualizar por batch_id o por _id
    success = await service.update_batch(batch_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Determinar mensaje según la acción
    message = "Batch updated successfully"
    if request.is_active is not None:
        message = "Batch resumed" if request.is_active else "Batch paused"
    
    return {
        "success": True, 
        "message": message,
        "batch_id": batch_id,
        "updated_fields": list(update_data.keys())
    }

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
    account_id: str = Form(..., description="ID de la cuenta"),
    batch_name: Optional[str] = Form(None, description="Nombre del batch"),
    batch_description: Optional[str] = Form(None, description="Descripción del batch"),
    allow_duplicates: bool = Form(False, description="Permitir duplicados"),
    processing_type: str = Form("basic", description="Tipo de procesamiento: 'basic' o 'acquisition'"),
    dias_fecha_limite: Optional[int] = Form(None, description="Días a agregar a fecha actual para calcular fecha_limite (ej: 30)"),
    dias_fecha_maxima: Optional[int] = Form(None, description="Días a agregar a fecha actual para calcular fecha_maxima (ej: 45)"),
    call_settings_json: Optional[str] = Form(None, description="JSON string con configuración de llamadas para este batch"),
    basic_service: BatchCreationService = Depends(get_batch_creation_service),
    chile_service: ChileBatchService = Depends(get_chile_batch_service)
):
    """
    Crear batch completo desde archivo Excel con opción de procesamiento
    
    Tipos de procesamiento:
    - 'basic': Procesamiento simple y directo (por defecto)
    - 'acquisition': Lógica avanzada con agrupación por RUT, normalización chilena,
                     cálculo de fechas límite según workflow N8N de adquisición
    
    Cálculo dinámico de fechas (opcional):
    - dias_fecha_limite: Calcula fecha_limite = HOY + N días (ej: 30 días)
    - dias_fecha_maxima: Calcula fecha_maxima = HOY + N días (ej: 45 días)
    - Si no se especifican, se usan las fechas del Excel
    
    Configuración de llamadas (opcional):
    - call_settings_json: JSON string con configuración específica del batch, ej:
      '{"allowed_call_hours": {"start": "09:00", "end": "20:00"}, "timezone": "America/Santiago", "retry_settings": {"max_attempts": 5, "retry_delay_hours": 12}, "max_concurrent_calls": 10}'
    """
    try:
        # Log para debugging
        logger.info(f"📥 Recibiendo request para crear batch desde Excel")
        logger.info(f"   - account_id: '{account_id}'")
        logger.info(f"   - batch_name: '{batch_name}'")
        logger.info(f"   - processing_type: '{processing_type}'")
        logger.info(f"   - allow_duplicates: {allow_duplicates}")
        logger.info(f"   - file: {file.filename}")
        logger.info(f"   - dias_fecha_limite: {dias_fecha_limite}")
        logger.info(f"   - dias_fecha_maxima: {dias_fecha_maxima}")
        logger.info(f"   - call_settings_json: {call_settings_json[:100] if call_settings_json else 'None'}...")
        
        # Validar account_id
        if not account_id or account_id.lower() == "string" or account_id == "undefined":
            raise HTTPException(
                status_code=400, 
                detail=f"❌ account_id inválido: '{account_id}'. Debe ser un ID válido como 'acc-a1b2c3d4e5f6'. El frontend debe enviar el ID real de la cuenta seleccionada."
            )
        
        # Verificar tipo de archivo
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos Excel (.xlsx, .xls)")
        
        # Verificar tipo de procesamiento
        if processing_type not in ["basic", "acquisition"]:
            raise HTTPException(
                status_code=400, 
                detail="processing_type debe ser 'basic' o 'acquisition'"
            )
        
        # Parsear call_settings si se proporciona
        call_settings = None
        if call_settings_json:
            import json
            try:
                call_settings = json.loads(call_settings_json)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"call_settings_json debe ser un JSON válido: {str(e)}"
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
                allow_duplicates=allow_duplicates,
                dias_fecha_limite=dias_fecha_limite,
                dias_fecha_maxima=dias_fecha_maxima,
                call_settings=call_settings
            )
        else:
            # Usar lógica básica (por defecto)
            result = await basic_service.create_batch_from_excel(
                file_content=content,
                account_id=account_id,
                batch_name=batch_name or f"Basic Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                batch_description=batch_description,
                allow_duplicates=allow_duplicates,
                dias_fecha_limite=dias_fecha_limite,
                dias_fecha_maxima=dias_fecha_maxima,
                call_settings=call_settings
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
    job = await service.get_job_by_id(job_id)
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

@app.get("/api/v1/dashboard/overview")
async def get_dashboard_overview(
    account_id: Optional[str] = Query(None, description="Filtrar por cuenta específica"),
    batch_service: BatchService = Depends(get_batch_service),
    job_service: JobService = Depends(get_job_service),
    account_service: AccountService = Depends(get_account_service)
):
    """
    Obtener overview del dashboard con métricas principales
    
    Diseñado específicamente para el frontend dashboard que muestra:
    - Jobs Hoy
    - Tasa de Éxito %
    - Lotes Activos
    - Jobs Pendientes
    """
    try:
        # Fecha de hoy (inicio del día)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Filtros opcionales por cuenta
        batch_filter = {"account_id": account_id} if account_id else {}
        job_filter = {"account_id": account_id} if account_id else {}
        
        # 1. Obtener lotes activos
        active_batches = await batch_service.list_batches(
            account_id=account_id,
            is_active=True,
            limit=1000
        )
        
        # 2. Estadísticas de jobs (agregación en MongoDB para performance)
        jobs_pipeline = [
            {"$match": job_filter},
            {"$facet": {
                "today_jobs": [
                    {"$match": {"created_at": {"$gte": today_start}}},
                    {"$count": "count"}
                ],
                "pending_jobs": [
                    {"$match": {"status": JobStatus.PENDING.value}},
                    {"$count": "count"}
                ],
                "completed_jobs": [
                    {"$match": {"status": JobStatus.COMPLETED.value}},
                    {"$count": "count"}
                ],
                "failed_jobs": [
                    {"$match": {"status": JobStatus.FAILED.value}},
                    {"$count": "count"}
                ]
            }}
        ]
        
        jobs_stats_cursor = job_service.jobs_collection.aggregate(jobs_pipeline)
        jobs_stats_result = await jobs_stats_cursor.to_list(length=1)
        
        # Parsear resultados
        jobs_stats = jobs_stats_result[0] if jobs_stats_result else {}
        
        jobs_today = jobs_stats.get("today_jobs", [{}])[0].get("count", 0)
        pending_jobs = jobs_stats.get("pending_jobs", [{}])[0].get("count", 0)
        completed_jobs = jobs_stats.get("completed_jobs", [{}])[0].get("count", 0)
        failed_jobs = jobs_stats.get("failed_jobs", [{}])[0].get("count", 0)
        
        # 3. Calcular tasa de éxito
        total_finished = completed_jobs + failed_jobs
        success_rate = round((completed_jobs / total_finished * 100) if total_finished > 0 else 0, 2)
        
        # 4. Calcular totales de batches
        total_jobs_in_batches = sum(batch.total_jobs for batch in active_batches)
        total_cost_in_batches = sum(batch.total_cost for batch in active_batches)
        total_minutes_in_batches = sum(batch.total_minutes for batch in active_batches)
        
        # 5. Información de cuenta (si se filtró)
        account_info = None
        if account_id:
            account = await account_service.get_account(account_id)
            if account:
                account_info = {
                    "account_id": account.account_id,
                    "name": account.name,
                    "status": account.status.value,
                    "balance": account.balance,
                    "billing_type": account.billing_type.value
                }
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "account": account_info,
            "metrics": {
                "jobs_today": jobs_today,
                "success_rate_percentage": success_rate,
                "active_batches": len(active_batches),
                "pending_jobs": pending_jobs
            },
            "detailed_stats": {
                "jobs": {
                    "today": jobs_today,
                    "pending": pending_jobs,
                    "completed": completed_jobs,
                    "failed": failed_jobs,
                    "total_finished": total_finished
                },
                "batches": {
                    "active_count": len(active_batches),
                    "total_jobs": total_jobs_in_batches,
                    "total_cost": round(total_cost_in_batches, 2),
                    "total_minutes": round(total_minutes_in_batches, 2)
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching dashboard overview: {str(e)}"
        )

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

@app.post("/api/v1/batches/argentina/{use_case}")
async def create_argentina_batch_for_use_case(
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
    argentina_service: ArgentinaBatchService = Depends(get_argentina_batch_service)
):
    """
    NUEVO: Crea batch argentino para cualquier caso de uso
    
    Casos de uso soportados:
    - debt_collection: Cobranza de deudas
    - marketing: Campañas de marketing
    
    Normalización argentina automática:
    - DNI: 12.345.678 → 12345678
    - Teléfonos: 11-2345-6789 → +5491123456789
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
        
        # Procesar con ArgentinaBatchService
        result = await argentina_service.create_batch_for_use_case(
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
                "message": f"Batch argentino de {use_case} creado exitosamente",
                "batch_id": result["batch_id"],
                "use_case": use_case,
                "country": "AR",
                "stats": result["stats"]
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "Error desconocido"))
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating Argentina batch for {use_case}: {str(e)}")
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
                "debt_collection": "Cobranza de deudas con normalización por país",
                "marketing": "Campañas de marketing personalizadas"
            },
            "countries": {
                "chile": "/api/v1/batches/chile/{use_case}",
                "argentina": "/api/v1/batches/argentina/{use_case}"
            }
        }
    except Exception as e:
        logging.error(f"Error getting use cases: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS FALTANTES - IMPLEMENTADOS
# ============================================================================

@app.get("/api/v1/accounts")
async def list_accounts(
    status: Optional[str] = Query(None),
    plan_type: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0, ge=0),
    service: AccountService = Depends(get_account_service)
):
    """Listar todas las cuentas con filtros opcionales"""
    try:
        from domain.enums import AccountStatus, PlanType
        
        status_enum = None
        if status:
            try:
                status_enum = AccountStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        plan_type_enum = None
        if plan_type:
            try:
                plan_type_enum = PlanType(plan_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid plan_type: {plan_type}")
        
        accounts = await service.list_accounts(
            status=status_enum,
            plan_type=plan_type_enum,
            limit=limit,
            skip=skip
        )
        
        return [serialize_objectid(account.to_dict()) for account in accounts]
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error listing accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/batches/{batch_id}/jobs")
async def get_batch_jobs(
    batch_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0, ge=0),
    batch_service: BatchService = Depends(get_batch_service),
    job_service: JobService = Depends(get_job_service)
):
    """Obtener jobs de un batch específico"""
    try:
        from domain.enums import JobStatus
        
        # Primero obtener el batch para conseguir el batch_id real
        batch = await batch_service.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        # Usar el batch_id personalizado para buscar jobs
        actual_batch_id = batch.batch_id
        
        status_enum = None
        if status:
            try:
                status_enum = JobStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
        
        jobs = await job_service.list_jobs(
            batch_id=actual_batch_id,
            status=status_enum,
            limit=limit,
            skip=skip
        )
        
        return [serialize_objectid(job.to_dict()) for job in jobs]
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting batch jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/accounts/{account_id}/batches")
async def get_account_batches(
    account_id: str,
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    skip: int = Query(0, ge=0),
    service: BatchService = Depends(get_batch_service),
    account_service: AccountService = Depends(get_account_service)
):
    """Obtener batches/campañas de una cuenta específica"""
    try:
        # Verificar que la cuenta existe
        account = await account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        batches = await service.list_batches(
            account_id=account_id,
            is_active=is_active,
            limit=limit,
            skip=skip
        )
        
        return [serialize_objectid(batch.to_dict()) for batch in batches]
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting account batches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/accounts/{account_id}/transactions")
async def get_account_transactions(
    account_id: str,
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0, ge=0),
    service: TransactionService = Depends(get_transaction_service),
    account_service: AccountService = Depends(get_account_service)
):
    """Obtener transacciones financieras de una cuenta"""
    try:
        # Verificar que la cuenta existe
        account = await account_service.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        from domain.enums import TransactionType
        transaction_type_enum = None
        if transaction_type:
            try:
                transaction_type_enum = TransactionType(transaction_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid transaction_type: {transaction_type}")
        
        transactions = await service.get_account_transactions(
            account_id=account_id,
            transaction_type=transaction_type_enum,
            limit=limit,
            skip=skip
        )
        
        return [serialize_objectid(transaction.to_dict()) for transaction in transactions]
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting account transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENDPOINTS ADICIONALES - MEJORAS PARA EL FRONTEND
# ============================================================================

@app.get("/api/v1/dashboard/overview")
async def get_dashboard_overview(
    account_id: Optional[str] = Query(None),
    service: JobService = Depends(get_job_service),
    account_svc: AccountService = Depends(get_account_service),
    batch_svc: BatchService = Depends(get_batch_service)
):
    """Obtener resumen ejecutivo para el dashboard principal"""
    try:
        if account_id:
            # Dashboard específico de cuenta
            account = await account_svc.get_account(account_id)
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            
            # Stats de jobs de hoy
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Agregación para jobs de hoy
            pipeline = [
                {
                    "$match": {
                        "account_id": account_id,
                        "created_at": {"$gte": today}
                    }
                },
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            cursor = service.jobs_collection.aggregate(pipeline)
            today_stats = {}
            async for stat in cursor:
                today_stats[stat["_id"]] = stat["count"]
            
            # Batches activos
            active_batches = await batch_svc.list_batches(account_id=account_id, is_active=True, limit=10)
            
            # Últimos batches (recientes)
            recent_batches = await batch_svc.list_batches(account_id=account_id, limit=5)
            
            return {
                "jobs_today": today_stats.get("completed", 0) + today_stats.get("in_progress", 0),
                "success_rate": "69.4%",  # Se calculará dinámicamente después
                "active_batches": len(active_batches),
                "pending_jobs": today_stats.get("pending", 0),
                "recent_batches": [
                    {
                        "name": batch.name,
                        "status": "RUNNING" if batch.is_active else "PAUSED",
                        "jobs_count": f"{batch.completed_jobs} jobs",
                        "description": "RUNNING" if batch.is_active else "PAUSED"
                    }
                    for batch in recent_batches[:3]
                ],
                "call_activity": {
                    "chart_placeholder": "Gráfico de actividad",
                    "note": "Disponible cuando se implemente /api/v1/reports/analytics"
                },
                "daily_summary": {
                    "completed": today_stats.get("completed", 0),
                    "in_progress": today_stats.get("in_progress", 0),
                    "failed": today_stats.get("failed", 0),
                    "revenue": "$0"  # Se calculará con transacciones
                }
            }
        else:
            # Dashboard global del sistema
            all_accounts = await account_svc.list_accounts(limit=1000)
            active_accounts = len([a for a in all_accounts if a.status.value == "active"])
            
            return {
                "system_overview": {
                    "total_accounts": len(all_accounts),
                    "active_accounts": active_accounts,
                    "suspended_accounts": len(all_accounts) - active_accounts
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting dashboard overview: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/accounts/{account_id}/summary")
async def get_account_summary(
    account_id: str,
    account_svc: AccountService = Depends(get_account_service),
    batch_svc: BatchService = Depends(get_batch_service),
    transaction_svc: TransactionService = Depends(get_transaction_service)
):
    """Obtener resumen completo de una cuenta (para modal de detalle)"""
    try:
        # Verificar que la cuenta existe
        account = await account_svc.get_account(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        # Stats de batches
        batches = await batch_svc.list_batches(account_id=account_id, limit=1000)
        active_batches = len([b for b in batches if b.is_active])
        
        # Resumen de transacciones
        transaction_summary = await transaction_svc.get_account_transaction_summary(account_id)
        
        # Balance actual
        balance = await account_svc.check_balance(account_id)
        
        return {
            "account": serialize_objectid(account.to_dict()),
            "balance": balance,
            "stats": {
                "total_batches": len(batches),
                "active_batches": active_batches,
                "completed_batches": len(batches) - active_batches
            },
            "financial_summary": {
                "total_spent": transaction_summary.get("total_cost", 0) / 100,  # Convertir centavos
                "total_recharges": transaction_summary.get("total_recharges", 0),
                "total_usage": transaction_summary.get("total_usage", 0),
                "transaction_count": transaction_summary.get("transaction_count", 0)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting account summary: {str(e)}")
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