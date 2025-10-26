"""
Script para validar el pipeline completo de creación de batch y ejecución de jobs
Simula el flujo desde el frontend hasta el worker
"""

import asyncio
import logging
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Agregar el directorio padre al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.database_manager import DatabaseManager
from services.batch_creation_service import BatchCreationService
from services.batch_service import BatchService
from services.job_service import JobService
from services.account_service import AccountService
from config.settings import get_settings
from bson import ObjectId

# Configurar logging detallado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Colores para la consola
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_section(title: str):
    """Imprime una sección con formato"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{title.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 80}{Colors.ENDC}\n")


def print_step(step: str):
    """Imprime un paso con formato"""
    print(f"\n{Colors.OKCYAN}{'▶' * 3} {step}{Colors.ENDC}")


def print_success(message: str):
    """Imprime mensaje de éxito"""
    print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")


def print_info(label: str, value: Any):
    """Imprime información"""
    print(f"{Colors.OKBLUE}   {label}: {Colors.ENDC}{value}")


def print_warning(message: str):
    """Imprime advertencia"""
    print(f"{Colors.WARNING}⚠️  {message}{Colors.ENDC}")


def print_error(message: str):
    """Imprime error"""
    print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")


async def create_test_batch(
    batch_service: BatchCreationService,
    account_service: AccountService,
    account_id: str = "retail_express"
) -> Dict[str, Any]:
    """Crea un batch de prueba con datos simulados"""
    
    print_step("PASO 1: Crear batch de prueba")
    
    # Datos de prueba (simulando lo que vendría del frontend)
    test_data = {
        "account_id": account_id,
        "batch_name": "TEST Pipeline Validation",
        "batch_description": "Batch para validar el pipeline completo",
        "debtors": [
            {
                "nombre": "Juan Pérez Test",
                "rut": "12345678-9",
                "phones": {
                    "movil": "+56912345678",
                    "fijo": "+56221234567"
                },
                "monto_total": 15000.0,
                "cantidad_cupones": 1,
                "fecha_limite": "2025-11-30",
                "fecha_maxima": "2025-12-15",
                "origen_empresa": "Test Company"
            },
            {
                "nombre": "María González Test",
                "rut": "98765432-1",
                "phones": {
                    "movil": "+56987654321"
                },
                "monto_total": 25000.0,
                "cantidad_cupones": 2,
                "fecha_limite": "2025-11-30",
                "fecha_maxima": "2025-12-15",
                "origen_empresa": "Test Company"
            }
        ]
    }
    
    print_info("Cuenta", test_data["account_id"])
    print_info("Nombre del batch", test_data["batch_name"])
    print_info("Número de deudores", len(test_data["debtors"]))
    
    # Verificar que la cuenta existe
    account = await account_service.get_account(account_id)
    if not account:
        print_error(f"La cuenta {account_id} no existe")
        return None
    
    print_success(f"Cuenta encontrada: {account.account_name}")
    print_info("Plan", account.plan_type.value)
    print_info("Créditos disponibles", f"${account.credit_available:.2f}")
    
    # Crear el batch
    logger.info("Iniciando creación de batch...")
    result = await batch_service.create_batch_from_debtors(
        account_id=test_data["account_id"],
        debtors=test_data["debtors"],
        batch_name=test_data["batch_name"],
        batch_description=test_data["batch_description"],
        allow_duplicates=False
    )
    
    if result["success"]:
        print_success("Batch creado exitosamente")
        print_info("Batch ID", result["batch_id"])
        print_info("Total jobs", result["total_jobs"])
        print_info("Costo estimado", f"${result['estimated_cost']:.2f}")
        print_info("Duplicados encontrados", result.get("duplicates_found", 0))
    else:
        print_error(f"Error al crear batch: {result.get('error')}")
    
    return result


async def inspect_batch(
    batch_service: BatchService,
    batch_id: str
):
    """Inspecciona el batch creado"""
    
    print_step("PASO 2: Inspeccionar batch creado")
    
    batch = await batch_service.get_batch(batch_id)
    if not batch:
        print_error("Batch no encontrado")
        return None
    
    print_success("Batch encontrado en base de datos")
    print_info("Batch ID", batch.batch_id)
    print_info("Estado activo", batch.is_active)
    print_info("Total jobs", batch.total_jobs)
    print_info("Jobs pendientes", batch.pending_jobs)
    print_info("Jobs completados", batch.completed_jobs)
    print_info("Prioridad", batch.priority)
    
    if batch.call_settings:
        print(f"\n{Colors.OKBLUE}   Configuración de llamadas:{Colors.ENDC}")
        for key, value in batch.call_settings.items():
            print(f"      • {key}: {value}")
    
    return batch


async def inspect_jobs(
    job_service: JobService,
    batch_id: str
):
    """Inspecciona los jobs creados"""
    
    print_step("PASO 3: Inspeccionar jobs creados")
    
    jobs = await job_service.list_jobs(batch_id=batch_id, limit=10)
    
    if not jobs:
        print_error("No se encontraron jobs")
        return []
    
    print_success(f"Se encontraron {len(jobs)} jobs")
    
    for i, job in enumerate(jobs, 1):
        print(f"\n{Colors.OKBLUE}Job #{i}:{Colors.ENDC}")
        print_info("   Job ID", job.job_id or str(job._id))
        print_info("   Status", job.status.value)
        print_info("   Mode", job.mode.value)
        print_info("   Intentos", f"{job.attempts}/{job.max_attempts}")
        
        if job.contact:
            print(f"{Colors.OKBLUE}   Contacto:{Colors.ENDC}")
            print(f"      • Nombre: {job.contact.name}")
            print(f"      • DNI: {job.contact.dni}")
            print(f"      • Teléfonos: {', '.join(job.contact.phones)}")
            print(f"      • Teléfono actual: {job.contact.current_phone}")
        
        if job.payload:
            print(f"{Colors.OKBLUE}   Payload (datos de la deuda):{Colors.ENDC}")
            print(f"      • Monto: ${job.payload.debt_amount}")
            print(f"      • Fecha límite: {job.payload.due_date}")
            print(f"      • Empresa: {job.payload.company_name}")
            
            if job.payload.additional_info:
                print(f"      • Info adicional:")
                for key, value in job.payload.additional_info.items():
                    print(f"         - {key}: {value}")
    
    return jobs


async def simulate_worker_view(
    db_manager: DatabaseManager,
    batch_id: str
):
    """Simula lo que vería el worker al tomar un job"""
    
    print_step("PASO 4: Simular vista del worker")
    
    jobs_collection = db_manager.get_collection("jobs")
    batches_collection = db_manager.get_collection("batches")
    
    # Verificar batches activos (lo que hace el worker)
    print(f"\n{Colors.OKCYAN}Worker verificando batches activos...{Colors.ENDC}")
    active_batches = []
    async for batch in batches_collection.find({"is_active": True}):
        active_batches.append(batch["batch_id"])
        if batch["batch_id"] == batch_id:
            print_success(f"Batch {batch_id} está ACTIVO")
            print_info("   is_active", batch.get("is_active"))
            print_info("   total_jobs", batch.get("total_jobs"))
            print_info("   pending_jobs", batch.get("pending_jobs"))
    
    if batch_id not in active_batches:
        print_warning(f"Batch {batch_id} NO está en la lista de activos")
        return None
    
    # Buscar job pendiente (lo que hace el worker)
    print(f"\n{Colors.OKCYAN}Worker buscando job pendiente...{Colors.ENDC}")
    
    filter_query = {
        "batch_id": batch_id,
        "status": "pending"
    }
    
    print_info("Filtro de búsqueda", json.dumps(filter_query, indent=2))
    
    job_doc = await jobs_collection.find_one(filter_query)
    
    if not job_doc:
        print_warning("No se encontró job pendiente")
        return None
    
    print_success("Job pendiente encontrado!")
    print(f"\n{Colors.OKGREEN}{'─' * 80}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}DOCUMENTO DEL JOB (como lo ve el worker):{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{'─' * 80}{Colors.ENDC}")
    
    # Mostrar campos importantes para el worker
    important_fields = [
        "_id", "job_id", "batch_id", "status", "mode",
        "contact", "payload", "attempts", "max_attempts",
        "to_number", "rut", "nombre", "monto_total", "fecha_limite",
        "origen_empresa", "cantidad_cupones", "fecha_maxima"
    ]
    
    print(f"\n{Colors.OKBLUE}Campos del documento:{Colors.ENDC}")
    for field in important_fields:
        if field in job_doc:
            value = job_doc[field]
            if isinstance(value, dict):
                print(f"   {field}:")
                print(f"      {json.dumps(value, indent=6, default=str)}")
            else:
                print(f"   {field}: {value}")
    
    # Verificar campos críticos para Retell
    print(f"\n{Colors.OKGREEN}{'─' * 80}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}VALIDACIÓN PARA RETELL:{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{'─' * 80}{Colors.ENDC}\n")
    
    critical_fields = {
        "to_number": "Número de teléfono para llamar",
        "nombre": "Nombre del deudor",
        "rut": "RUT/DNI del deudor",
        "monto_total": "Monto de la deuda",
        "fecha_limite": "Fecha límite de pago",
        "origen_empresa": "Nombre de la empresa"
    }
    
    all_present = True
    for field, description in critical_fields.items():
        if field in job_doc and job_doc[field]:
            print_success(f"{description}: {job_doc[field]}")
        else:
            print_error(f"{description}: FALTANTE")
            all_present = False
    
    # Verificar estructura anidada
    print(f"\n{Colors.OKBLUE}Estructura anidada (contact & payload):{Colors.ENDC}")
    
    if "contact" in job_doc:
        contact = job_doc["contact"]
        print_success(f"contact.name: {contact.get('name')}")
        print_success(f"contact.dni: {contact.get('dni')}")
        print_success(f"contact.phones: {contact.get('phones')}")
    else:
        print_warning("Campo 'contact' no encontrado")
    
    if "payload" in job_doc:
        payload = job_doc["payload"]
        print_success(f"payload.debt_amount: {payload.get('debt_amount')}")
        print_success(f"payload.due_date: {payload.get('due_date')}")
        print_success(f"payload.company_name: {payload.get('company_name')}")
        
        if "additional_info" in payload:
            print_info("   payload.additional_info", payload["additional_info"])
    else:
        print_warning("Campo 'payload' no encontrado")
    
    # Contexto para Retell
    print(f"\n{Colors.OKGREEN}{'─' * 80}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}CONTEXTO QUE SE ENVIARÍA A RETELL:{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{'─' * 80}{Colors.ENDC}\n")
    
    retell_context = {
        "nombre": job_doc.get("nombre", ""),
        "rut": job_doc.get("rut", ""),
        "monto_total": str(job_doc.get("monto_total", 0)),
        "fecha_limite": job_doc.get("fecha_limite", ""),
        "empresa": job_doc.get("origen_empresa", ""),
    }
    
    if "payload" in job_doc and "additional_info" in job_doc["payload"]:
        retell_context.update(job_doc["payload"]["additional_info"])
    
    print(f"{Colors.OKBLUE}{json.dumps(retell_context, indent=2, ensure_ascii=False)}{Colors.ENDC}")
    
    if all_present:
        print(f"\n{Colors.OKGREEN}{'✅' * 40}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}TODOS LOS CAMPOS CRÍTICOS ESTÁN PRESENTES{Colors.ENDC}")
        print(f"{Colors.OKGREEN}{'✅' * 40}{Colors.ENDC}\n")
    else:
        print(f"\n{Colors.FAIL}{'❌' * 40}{Colors.ENDC}")
        print(f"{Colors.FAIL}FALTAN CAMPOS CRÍTICOS{Colors.ENDC}")
        print(f"{Colors.FAIL}{'❌' * 40}{Colors.ENDC}\n")
    
    return job_doc


async def main():
    """Función principal"""
    
    print_section("VALIDACIÓN DEL PIPELINE COMPLETO")
    print(f"{Colors.OKBLUE}Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}Flujo: Frontend → API → Database → Worker{Colors.ENDC}\n")
    
    settings = get_settings()
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    
    try:
        await db_manager.connect()
        print_success("Conectado a MongoDB")
        print_info("Database", settings.database.database)
        
        # Inicializar servicios
        account_service = AccountService(db_manager)
        batch_service = BatchService(db_manager)
        batch_creation_service = BatchCreationService(db_manager)
        job_service = JobService(db_manager)
        
        # 1. Crear batch
        result = await create_test_batch(batch_creation_service, account_service)
        if not result or not result["success"]:
            print_error("No se pudo continuar sin batch")
            return
        
        batch_id = result["batch_id"]
        
        # 2. Inspeccionar batch
        await inspect_batch(batch_service, batch_id)
        
        # 3. Inspeccionar jobs
        await inspect_jobs(job_service, batch_id)
        
        # 4. Simular worker
        await simulate_worker_view(db_manager, batch_id)
        
        # Resumen final
        print_section("RESUMEN FINAL")
        print_success(f"Batch creado: {batch_id}")
        print_success(f"Jobs creados: {result['total_jobs']}")
        print_success("Pipeline validado exitosamente")
        
        print(f"\n{Colors.WARNING}NOTA: Este batch es de PRUEBA. Puedes eliminarlo con:{Colors.ENDC}")
        print(f"{Colors.OKCYAN}curl -X DELETE http://localhost:8000/api/v1/batches/{batch_id}{Colors.ENDC}\n")
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        logger.exception("Error en validación del pipeline")
    finally:
        await db_manager.close()
        print_success("Conexión a MongoDB cerrada")


if __name__ == "__main__":
    asyncio.run(main())
