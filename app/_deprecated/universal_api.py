"""
API Universal para gestión de batches multi-caso de uso
Permite crear batches de cobranza, user experience, y otros casos de uso
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, Dict, List, Any
import logging
import uuid
from datetime import datetime

from utils.universal_excel_processor import UniversalExcelProcessor
from domain.use_case_registry import get_use_case_registry
from domain.enums import UseCaseType
from infrastructure.mongo_client import get_database

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SpeechAI Universal API",
    description="API para gestión de batches multi-caso de uso",
    version="2.0.0"
)

# Instancias globales
excel_processor = UniversalExcelProcessor()
registry = get_use_case_registry()

@app.get("/")
async def root():
    """Endpoint raíz con información de la API"""
    return {
        "message": "SpeechAI Universal API - Multi Use Case Support",
        "version": "2.0.0",
        "supported_use_cases": registry.get_available_use_cases(),
        "features": [
            "Multi-use case batch processing",
            "Universal Excel processing",
            "Dynamic job creation",
            "Account balance validation",
            "Extensible architecture"
        ]
    }

@app.get("/use-cases")
async def get_supported_use_cases():
    """
    Obtiene información sobre todos los casos de uso soportados
    """
    try:
        use_cases_info = excel_processor.get_supported_use_cases()
        
        return {
            "success": True,
            "use_cases": use_cases_info,
            "total": len(use_cases_info)
        }
    except Exception as e:
        logger.error(f"Error obteniendo casos de uso: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/use-cases/{use_case}/template")
async def get_excel_template(use_case: str):
    """
    Genera template Excel para un caso de uso específico
    """
    try:
        if use_case not in registry.get_available_use_cases():
            raise HTTPException(
                status_code=404, 
                detail=f"Caso de uso no soportado: {use_case}"
            )
        
        template_df = excel_processor.get_excel_template_for_use_case(use_case)
        template_data = template_df.to_dict('records')
        
        return {
            "success": True,
            "use_case": use_case,
            "template": template_data,
            "required_columns": registry.get_required_columns_for_use_case(use_case),
            "instructions": f"Llena este template para crear batches de {use_case}"
        }
        
    except Exception as e:
        logger.error(f"Error generando template para {use_case}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batches/create")
async def create_universal_batch(
    file: UploadFile = File(...),
    use_case: str = Form(...),
    account_id: str = Form(...),
    batch_name: str = Form(...),
    batch_description: Optional[str] = Form(None)
):
    """
    Crea un batch universal desde archivo Excel
    Soporta múltiples casos de uso dinámicamente
    """
    try:
        # Validar caso de uso
        if use_case not in registry.get_available_use_cases():
            raise HTTPException(
                status_code=400,
                detail=f"Caso de uso no soportado: {use_case}. Disponibles: {registry.get_available_use_cases()}"
            )
        
        # Validar archivo
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="Solo se admiten archivos Excel (.xlsx, .xls)"
            )
        
        # Leer archivo
        file_content = await file.read()
        
        # Procesar Excel
        batch, jobs, errors = excel_processor.process_excel_to_jobs(
            file_content=file_content,
            use_case=use_case,
            account_id=account_id,
            batch_name=batch_name,
            batch_description=batch_description or f"Batch de {use_case}"
        )
        
        if not batch or not jobs:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "No se pudieron crear jobs desde el Excel",
                    "errors": errors
                }
            )
        
        # Conectar a MongoDB
        db = get_database()
        
        # Guardar batch
        batch_dict = batch.to_mongo_dict() if hasattr(batch, 'to_mongo_dict') else batch.__dict__
        batch_result = db.batches.insert_one(batch_dict)
        batch_id = str(batch_result.inserted_id)
        
        # Guardar jobs
        job_dicts = []
        for job in jobs:
            job_dict = job.to_mongo_dict() if hasattr(job, 'to_mongo_dict') else job.__dict__
            job_dict['batch_id'] = batch_id  # Asegurar referencia correcta
            job_dicts.append(job_dict)
        
        if job_dicts:
            jobs_result = db.call_jobs.insert_many(job_dicts)
            created_job_count = len(jobs_result.inserted_ids)
        else:
            created_job_count = 0
        
        # Actualizar estadísticas del batch
        db.batches.update_one(
            {"_id": batch_result.inserted_id},
            {"$set": {"total_jobs": created_job_count}}
        )
        
        logger.info(f"Batch creado: {batch_id}, Jobs: {created_job_count}, Caso de uso: {use_case}")
        
        return {
            "success": True,
            "message": f"Batch de {use_case} creado exitosamente",
            "batch_id": batch_id,
            "use_case": use_case,
            "account_id": account_id,
            "stats": {
                "total_jobs": created_job_count,
                "processed_rows": len(jobs) + len(errors),
                "successful_jobs": created_job_count,
                "failed_rows": len(errors)
            },
            "errors": errors if errors else [],
            "warnings": []
        }
        
    except Exception as e:
        logger.error(f"Error creando batch universal: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get("/batches/{batch_id}")
async def get_batch_details(batch_id: str):
    """
    Obtiene detalles de un batch específico
    """
    try:
        db = get_database()
        
        # Buscar batch
        batch = db.batches.find_one({"_id": batch_id})
        if not batch:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        # Obtener estadísticas de jobs
        pipeline = [
            {"$match": {"batch_id": batch_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        job_stats = list(db.call_jobs.aggregate(pipeline))
        stats_dict = {stat["_id"]: stat["count"] for stat in job_stats}
        
        # Calcular métricas
        total_jobs = sum(stats_dict.values())
        completed_jobs = stats_dict.get("done", 0)
        failed_jobs = stats_dict.get("failed", 0)
        pending_jobs = stats_dict.get("pending", 0)
        in_progress_jobs = stats_dict.get("in_progress", 0)
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        return {
            "success": True,
            "batch": batch,
            "stats": {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "failed_jobs": failed_jobs,
                "pending_jobs": pending_jobs,
                "in_progress_jobs": in_progress_jobs,
                "success_rate": round(success_rate, 2)
            },
            "status_breakdown": stats_dict
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batches")
async def list_batches(
    account_id: Optional[str] = None,
    use_case: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Lista batches con filtros opcionales
    """
    try:
        db = get_database()
        
        # Construir filtro
        filter_dict = {}
        if account_id:
            filter_dict["account_id"] = account_id
        if use_case:
            filter_dict["use_case"] = use_case
        
        # Obtener batches
        batches_cursor = db.batches.find(filter_dict).sort("created_at", -1).skip(offset).limit(limit)
        batches = list(batches_cursor)
        
        # Obtener estadísticas para cada batch
        for batch in batches:
            batch_id = batch["_id"]
            
            # Stats rápidas
            total_jobs = db.call_jobs.count_documents({"batch_id": batch_id})
            completed_jobs = db.call_jobs.count_documents({"batch_id": batch_id, "status": "done"})
            
            batch["stats"] = {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "success_rate": (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            }
        
        total_batches = db.batches.count_documents(filter_dict)
        
        return {
            "success": True,
            "batches": batches,
            "pagination": {
                "total": total_batches,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_batches
            },
            "filters_applied": {
                "account_id": account_id,
                "use_case": use_case
            }
        }
        
    except Exception as e:
        logger.error(f"Error listando batches: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batches/{batch_id}/start")
async def start_batch_processing(batch_id: str):
    """
    Inicia el procesamiento de un batch
    (Los workers lo tomarán automáticamente)
    """
    try:
        db = get_database()
        
        # Verificar que el batch existe
        batch = db.batches.find_one({"_id": batch_id})
        if not batch:
            raise HTTPException(status_code=404, detail="Batch no encontrado")
        
        # Actualizar estado del batch
        db.batches.update_one(
            {"_id": batch_id},
            {"$set": {
                "status": "processing",
                "started_at": datetime.utcnow()
            }}
        )
        
        # Los jobs ya están en estado "pending", los workers los procesarán
        pending_count = db.call_jobs.count_documents({"batch_id": batch_id, "status": "pending"})
        
        return {
            "success": True,
            "message": f"Batch {batch_id} iniciado para procesamiento",
            "batch_id": batch_id,
            "pending_jobs": pending_count,
            "note": "Los workers universales procesarán los jobs automáticamente"
        }
        
    except Exception as e:
        logger.error(f"Error iniciando batch {batch_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check de la API
    """
    try:
        db = get_database()
        
        # Test de conexión a DB
        db.test.find_one()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "services": {
                "database": "connected",
                "use_case_registry": "loaded",
                "excel_processor": "ready"
            },
            "available_use_cases": len(registry.get_available_use_cases())
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)