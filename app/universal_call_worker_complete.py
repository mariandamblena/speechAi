"""
Universal Call Worker - Versión genérica que soporta múltiples casos de uso
Reemplaza el call_worker específico de cobranza con uno extensible
"""
import os
import time
import uuid
import json
import signal
import random
import logging
import datetime as dt
from datetime import timezone
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import requests
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError
from tenacity import retry, wait_exponential_jitter, stop_after_attempt
from dotenv import load_dotenv

# Importar el nuevo sistema universal
from domain.use_case_registry import get_universal_processor
from domain.abstract.base_models import BaseJobModel

# ----------------------------
# Config & Logging
# ----------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s"
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "Debtors")
MONGO_COLL_JOBS = os.getenv("MONGO_COLL_JOBS", "call_jobs")
MONGO_COLL_LOGS = os.getenv("MONGO_COLL_LOGS", "call_logs")

RETELL_API_KEY = os.getenv("RETELL_API_KEY") or ""
RETELL_BASE_URL = os.getenv("RETELL_BASE_URL", "https://api.retellai.com")

WORKER_COUNT = int(os.getenv("WORKER_COUNT", "3"))
LEASE_SECONDS = int(os.getenv("LEASE_SECONDS", "120"))
MAX_TRIES = int(os.getenv("MAX_TRIES", "3"))

# Configuraciones específicas para seguimiento de llamadas
CALL_POLLING_INTERVAL = int(os.getenv("CALL_POLLING_INTERVAL", "15"))  # segundos entre consultas
CALL_MAX_DURATION_MINUTES = int(os.getenv("CALL_MAX_DURATION_MINUTES", "10"))  # timeout máximo
RETRY_DELAY_MINUTES = int(os.getenv("RETRY_DELAY_MINUTES", "30"))  # delay entre reintentos por persona
NO_ANSWER_RETRY_MINUTES = int(os.getenv("NO_ANSWER_RETRY_MINUTES", "60"))  # delay específico para no answer

RETELL_AGENT_ID = os.getenv("RETELL_AGENT_ID", "")
CALL_FROM_NUMBER = os.getenv("RETELL_FROM_NUMBER", "")

# Variable global para control de shutdown
RUNNING = True

def signal_handler(signum, frame):
    global RUNNING
    logging.info("Recibida señal de stop. Cerrando...")
    RUNNING = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ----------------------------
# Mongo Client & Collections
# ----------------------------
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
coll_jobs = db[MONGO_COLL_JOBS]
coll_logs = db[MONGO_COLL_LOGS]

# ----------------------------
# Helpers
# ----------------------------
def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def lease_expires_in(seconds: int) -> dt.datetime:
    return utcnow() + dt.timedelta(seconds=seconds)

def rand_jitter(a=0.9, b=1.1) -> float:
    return random.uniform(a, b)

def ensure_indexes():
    """Crea índices para performance y locking confiable."""
    coll_jobs.create_index([("status", 1), ("reserved_until", 1)], name="status_reserved_idx")
    coll_jobs.create_index([("tries", 1)], name="tries_idx")
    coll_jobs.create_index([("account_id", 1), ("status", 1)], name="account_status_idx")
    coll_jobs.create_index([("use_case", 1), ("status", 1)], name="usecase_status_idx")
    logging.info("Índices verificados/creados.")

# ----------------------------
# Retell Client
# ----------------------------
@dataclass
class RetellResult:
    success: bool
    call_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class RetellClient:
    """Cliente Retell v2 universal para todos los casos de uso"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.retellai.com"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @retry(wait=wait_exponential_jitter(initial=1, max=20), stop=stop_after_attempt(3))
    def start_call(self, *, to_number: str, agent_id: str, from_number: Optional[str], context: Dict[str, Any]) -> RetellResult:
        """Crea una llamada usando Retell v2"""
        url = f"{self.base_url}/v2/create-phone-call"

        body = {
            "to_number": str(to_number),
            "agent_id": str(agent_id),
            "retell_llm_dynamic_variables": context or {},
        }
        if from_number:
            body["from_number"] = str(from_number)

        resp = requests.post(url, headers=self._headers(), data=json.dumps(body), timeout=30)

        if 200 <= resp.status_code < 300:
            try:
                data = resp.json()
            except Exception:
                return RetellResult(success=False, error=f"Respuesta no-JSON: {resp.text}")

            call_id = data.get("call_id") or (data.get("data") or {}).get("call_id") or data.get("id")
            if not call_id:
                return RetellResult(success=False, error=f"Sin call_id en respuesta: {data}", raw=data)
            return RetellResult(success=True, call_id=call_id, raw=data)

        # error HTTP
        try:
            err = resp.json()
        except Exception:
            err = {"text": resp.text}
        return RetellResult(success=False, error=str(err))

    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Lee estado de la llamada (v2)"""
        url = f"{self.base_url}/v2/get-call/{call_id}"
        resp = requests.get(url, headers=self._headers(), timeout=20)
        try:
            return resp.json()
        except Exception:
            return {"error": resp.text, "status_code": resp.status_code}

# ----------------------------
# Job Store Universal
# ----------------------------
class UniversalJobStore:
    """Store que maneja jobs de cualquier caso de uso"""
    
    def __init__(self, coll, db=None):
        self.coll = coll
        self.db = db

    def claim_one(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """Reserva un job pendiente de cualquier caso de uso"""
        now = utcnow()
        reservation = lease_expires_in(LEASE_SECONDS)
        
        print(f"[DEBUG] [{worker_id}] Buscando jobs pendientes (cualquier caso de uso)...")
        
        try:
            doc = self.coll.find_one_and_update(
                filter={"status": "pending"},
                update={
                    "$set": {
                        "status": "in_progress",
                        "reserved_until": reservation,
                        "worker_id": worker_id,
                        "started_at": now,
                        "updated_at": now,
                    },
                    "$inc": {"attempts": 1}
                },
                return_document=ReturnDocument.AFTER
            )
            
            if doc:
                use_case = doc.get('use_case', 'unknown')
                contact_info = doc.get('contact', {})
                contact_name = contact_info.get('name', 'N/A')
                print(f"[DEBUG] [{worker_id}] ✅ Job encontrado: {doc.get('_id')}")
                print(f"[DEBUG] [{worker_id}] Caso de uso: {use_case}, Contacto: {contact_name}")
            else:
                print(f"[DEBUG] [{worker_id}] ❌ No se encontraron jobs pendientes")
                
            return doc
        except PyMongoError as e:
            print(f"[ERROR] [{worker_id}] Error en claim_one: {e}")
            logging.error(f"claim_one error: {e}")
            return None

    def extend_lease(self, job_id):
        """Extiende el lease de un job"""
        try:
            self.coll.update_one(
                {"_id": job_id},
                {"$set": {
                    "reserved_until": lease_expires_in(LEASE_SECONDS),
                    "updated_at": utcnow()
                }}
            )
        except PyMongoError as e:
            logging.warning(f"No se pudo extender lease de {job_id}: {e}")

    def save_call_id(self, job_id, call_id: str):
        """Guarda call_id después de crear la llamada"""
        try:
            self.coll.update_one(
                {"_id": job_id},
                {"$set": {
                    "call_id": call_id,
                    "call_started_at": utcnow(),
                    "updated_at": utcnow(),
                    "is_calling": True
                }}
            )
            print(f"[DEBUG] [{job_id}] ✅ Call_id guardado: {call_id}")
        except PyMongoError as e:
            logging.error(f"save_call_id error: {e}")

    def mark_failed(self, job_id, reason: str, terminal=False):
        """Marca un job como fallido"""
        new_status = "failed" if terminal else "pending"
        reserved_until = None if terminal else lease_expires_in(int(LEASE_SECONDS * 1.5))
        
        update_fields = {
            "status": new_status,
            "last_error": reason,
            "updated_at": utcnow(),
            "reserved_until": reserved_until
        }
        
        if not terminal:
            next_try = utcnow() + dt.timedelta(minutes=RETRY_DELAY_MINUTES)
            update_fields["next_try_at"] = next_try
            
        try:
            self.coll.update_one({"_id": job_id}, {"$set": update_fields})
        except PyMongoError as e:
            logging.error(f"mark_failed error: {e}")

    def mark_done(self, job_id, retell_payload=None):
        """Marca un job como completado"""
        try:
            self.coll.update_one(
                {"_id": job_id},
                {"$set": {
                    "status": "done",
                    "finished_at": utcnow(),
                    "updated_at": utcnow(),
                    "retell_result": retell_payload or {}
                }}
            )
        except PyMongoError as e:
            logging.error(f"mark_done error: {e}")

# Continuará en el siguiente archivo..."""
Universal Call Worker - Parte 2: Orchestrator y lógica de procesamiento
"""

# ----------------------------
# Universal Call Orchestrator
# ----------------------------
class UniversalCallOrchestrator:
    """
    Orchestrator que puede procesar jobs de cualquier caso de uso
    """
    
    def __init__(self, job_store: UniversalJobStore, retell: RetellClient):
        self.job_store = job_store
        self.retell = retell
        self.processor = get_universal_processor()
    
    def _validate_account_balance(self, job: Dict[str, Any]) -> bool:
        """
        Valida balance de la cuenta antes de procesar job
        Retorna True si hay balance suficiente, False en caso contrario
        """
        job_id = job["_id"]
        account_id = job.get('account_id')
        
        if not account_id:
            print(f"[ERROR] [{job_id}] Sin account_id en job")
            self.job_store.mark_failed(job_id, "Sin account_id especificado", terminal=True)
            return False
        
        try:
            # Acceder a la base de datos
            if self.job_store.db is not None:
                account_doc = self.job_store.db.accounts.find_one({"account_id": account_id})
            else:
                # Fallback usando la colección existente
                db = self.job_store.coll.database
                account_doc = db.accounts.find_one({"account_id": account_id})
            
            if not account_doc:
                print(f"[ERROR] [{job_id}] Cuenta {account_id} no encontrada")
                self.job_store.mark_failed(job_id, f"Cuenta {account_id} no encontrada", terminal=True)
                return False
            
            plan_type = account_doc.get('plan_type')
            has_balance = True
            error_msg = ""
            
            if plan_type == "unlimited":
                has_balance = True
            elif plan_type == "minutes_based":
                minutes_remaining = account_doc.get('minutes_remaining', 0)
                has_balance = minutes_remaining > 0
                if not has_balance:
                    error_msg = f"Sin minutos disponibles (restantes: {minutes_remaining})"
            elif plan_type == "credit_based":
                credit_balance = account_doc.get('credit_balance', 0)
                credit_reserved = account_doc.get('credit_reserved', 0)
                cost_per_call = account_doc.get('cost_per_call_setup', 0.02)
                credit_available = max(0, credit_balance - credit_reserved)
                has_balance = credit_available >= cost_per_call
                if not has_balance:
                    error_msg = f"Sin créditos suficientes (disponibles: {credit_available:.2f}, necesarios: {cost_per_call:.2f})"
            
            if not has_balance:
                print(f"[ERROR] [{job_id}] 🚫 SALDO INSUFICIENTE - Plan: {plan_type}, {error_msg}")
                self.job_store.mark_failed(job_id, f"Saldo insuficiente: {error_msg}", terminal=True)
                return False
            else:
                print(f"[DEBUG] [{job_id}] ✅ Balance suficiente - Plan: {plan_type}")
                return True
                
        except Exception as e:
            print(f"[ERROR] [{job_id}] Error validando balance: {e}")
            self.job_store.mark_failed(job_id, f"Error validando balance: {e}", terminal=True)
            return False
    
    def _get_next_phone(self, job: Dict[str, Any]) -> Optional[str]:
        """
        Obtiene el siguiente teléfono del contacto (universal para cualquier estructura)
        """
        job_id = job["_id"]
        
        # Intentar con nueva estructura (contact.phones)
        contact = job.get('contact') or job.get('contacto')
        if contact and 'phones' in contact:
            phones = contact['phones']
            next_index = contact.get('next_phone_index', 0)
            
            if 0 <= next_index < len(phones):
                return phones[next_index]
        
        # Fallback: estructura antigua
        if job.get('to_number'):
            return job['to_number']
            
        # Fallback: buscar campos de teléfono conocidos
        phone_fields = ['telefono', 'phone', 'celular', 'movil']
        for field in phone_fields:
            if job.get(field):
                return str(job[field])
        
        print(f"[ERROR] [{job_id}] No se encontró teléfono válido en job")
        return None
    
    def _advance_to_next_phone(self, job_id: str):
        """Avanza al siguiente teléfono en la lista"""
        try:
            # Actualizar el índice del siguiente teléfono
            self.job_store.coll.update_one(
                {"_id": job_id},
                {"$inc": {"contact.next_phone_index": 1}}
            )
            # Fallback para estructura antigua
            self.job_store.coll.update_one(
                {"_id": job_id},
                {"$inc": {"contacto.next_phone_index": 1}}
            )
        except Exception as e:
            print(f"[WARNING] [{job_id}] No se pudo actualizar índice de teléfono: {e}")
    
    def _convert_job_to_base_model(self, job_dict: Dict[str, Any]) -> Optional[BaseJobModel]:
        """
        Convierte un job de MongoDB a modelo base
        (Simplificado - en producción necesitarías deserialización completa)
        """
        try:
            # Por ahora, trabajamos directamente con el diccionario
            # En una implementación completa, aquí deserializarías a objetos BaseJobModel
            return job_dict
        except Exception as e:
            print(f"[WARNING] Error convirtiendo job a modelo base: {e}")
            return job_dict
    
    def process_job(self, job: Dict[str, Any]):
        """
        Procesa un job usando el procesador universal apropiado
        """
        job_id = job["_id"]
        use_case = job.get('use_case', 'unknown')
        
        print(f"\n[DEBUG] [{job_id}] ========== PROCESANDO JOB UNIVERSAL ==========")
        print(f"[DEBUG] [{job_id}] Caso de uso: {use_case}")
        print(f"[DEBUG] [{job_id}] Job completo: {job}")
        print(f"[DEBUG] [{job_id}] ===================================================\n")
        
        # Verificar si ya tiene resultado exitoso
        call_result = job.get('call_result', {})
        if call_result and call_result.get('success'):
            print(f"[DEBUG] [{job_id}] ✅ Job ya tiene resultado exitoso, saltando")
            self.job_store.mark_done(job_id, call_result.get('details', {}))
            return
        
        # 🔥 VALIDACIÓN DE BALANCE - CRÍTICA PARA SAAS
        if not self._validate_account_balance(job):
            return  # Ya se marcó como failed en la validación
        
        # Obtener teléfono
        phone = self._get_next_phone(job)
        if not phone:
            print(f"[ERROR] [{job_id}] Sin teléfono válido disponible")
            self.job_store.mark_failed(job_id, "Sin teléfono válido", terminal=True)
            return
        
        # Verificar si el procesador puede manejar este caso de uso
        if not self.processor.can_process_use_case(use_case):
            print(f"[ERROR] [{job_id}] Caso de uso no soportado: {use_case}")
            self.job_store.mark_failed(job_id, f"Caso de uso no soportado: {use_case}", terminal=True)
            return
        
        # Convertir job a modelo base y procesar
        try:
            job_model = self._convert_job_to_base_model(job)
            processing_result = self.processor.process_job(job_model)
            
            context = processing_result.get('context', {})
            processor_type = processing_result.get('processor_type', use_case)
            job_summary = processing_result.get('job_summary', f"{use_case} job")
            
            print(f"[DEBUG] [{job_id}] Procesador: {processor_type}")
            print(f"[DEBUG] [{job_id}] Resumen: {job_summary}")
            print(f"[DEBUG] [{job_id}] Context enviado a Retell: {context}")
            
        except Exception as e:
            print(f"[ERROR] [{job_id}] Error procesando job: {e}")
            self.job_store.mark_failed(job_id, f"Error procesando: {e}", terminal=True)
            return
        
        # Extender lease antes de llamar
        self.job_store.extend_lease(job_id)
        
        # Llamar usando contexto generado por el procesador
        contact_name = job.get('contact', {}).get('name') or job.get('nombre', 'N/A')
        contact_id = job.get('contact', {}).get('identifier') or job.get('rut', 'N/A')
        
        logging.info(f"[{job_id}] Llamando a {phone} ({contact_name} - {contact_id}) - Caso: {use_case}")
        print(f"[DEBUG] [{job_id}] Iniciando llamada a Retell...")
        
        # Crear llamada con Retell
        start_result = self.retell.start_call(
            to_number=phone,
            agent_id=RETELL_AGENT_ID,
            from_number=CALL_FROM_NUMBER,
            context=context
        )
        
        if not start_result.success:
            error = f"Error iniciando llamada: {start_result.error}"
            print(f"[ERROR] [{job_id}] {error}")
            self.job_store.mark_failed(job_id, error, terminal=False)
            return
        
        call_id = start_result.call_id
        print(f"[SUCCESS] [{job_id}] ✅ Llamada iniciada: {call_id}")
        
        # Guardar call_id inmediatamente
        self.job_store.save_call_id(job_id, call_id)
        
        # Seguir la llamada hasta completarse
        self._track_call_completion(job_id, call_id, phone)
    
    def _track_call_completion(self, job_id: str, call_id: str, phone: str):
        """
        Sigue el estado de la llamada hasta que termine
        """
        print(f"[DEBUG] [{job_id}] Siguiendo llamada {call_id}...")
        
        max_duration = CALL_MAX_DURATION_MINUTES * 60  # convertir a segundos
        start_time = time.time()
        
        while RUNNING:
            elapsed = time.time() - start_time
            if elapsed > max_duration:
                print(f"[WARNING] [{job_id}] Llamada excedió duración máxima ({CALL_MAX_DURATION_MINUTES} min)")
                break
            
            try:
                call_status = self.retell.get_call_status(call_id)
                
                if "error" in call_status:
                    print(f"[ERROR] [{job_id}] Error consultando estado: {call_status}")
                    break
                
                status = call_status.get("call_status", "unknown")
                print(f"[DEBUG] [{job_id}] Estado llamada: {status} (transcurridos: {elapsed:.1f}s)")
                
                # Estados finales
                if status in ["ended", "error", "registered"]:
                    print(f"[SUCCESS] [{job_id}] ✅ Llamada terminada: {status}")
                    
                    # Determinar si fue exitosa
                    is_success = status == "ended"
                    
                    # Guardar resultado
                    try:
                        # Actualizar con resultado final
                        self.job_store.coll.update_one(
                            {"_id": job_id},
                            {"$set": {
                                "call_result": {
                                    "success": is_success,
                                    "status": status,
                                    "details": call_status,
                                    "timestamp": utcnow()
                                },
                                "call_ended_at": utcnow(),
                                "updated_at": utcnow(),
                                "status": "done" if is_success else "pending"
                            }}
                        )
                        
                        if is_success:
                            print(f"[SUCCESS] [{job_id}] 🎉 Llamada completada exitosamente")
                        else:
                            print(f"[INFO] [{job_id}] Llamada terminó sin éxito, programando reintento")
                            
                    except Exception as e:
                        print(f"[ERROR] [{job_id}] Error guardando resultado: {e}")
                    
                    break
                
                # Continuar siguiendo
                time.sleep(CALL_POLLING_INTERVAL)
                
            except Exception as e:
                print(f"[ERROR] [{job_id}] Excepción siguiendo llamada: {e}")
                break
        
        print(f"[DEBUG] [{job_id}] Seguimiento de llamada completado")


# ----------------------------
# Worker Loop Universal
# ----------------------------
def universal_worker_loop(name: str, store: UniversalJobStore, orch: UniversalCallOrchestrator):
    """Loop de worker que puede procesar cualquier tipo de job"""
    delay = rand_jitter() * 3
    print(f"[DEBUG] [{name}] Worker iniciando en {delay:.2f} segundos...")
    time.sleep(delay)
    
    print(f"[DEBUG] [{name}] Worker universal activo y buscando jobs...")
    
    while RUNNING:
        try:
            print(f"[DEBUG] [{name}] Intentando obtener un job...")
            job = store.claim_one(name)
            
            if job:
                print(f"[DEBUG] [{name}] ✅ Job obtenido, iniciando procesamiento...")
                orch.process_job(job)
                print(f"[DEBUG] [{name}] Job procesado, buscando el siguiente...")
            else:
                print(f"[DEBUG] [{name}] No hay jobs disponibles, esperando...")
                time.sleep(rand_jitter() * 2)
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ERROR] [{name}] Excepción en worker_loop: {e}")
            logging.exception(f"[{name}] Excepción en worker_loop: {e}")
            time.sleep(2.0 * rand_jitter())


# ----------------------------
# Main Universal
# ----------------------------
def main():
    print("\n=== INICIANDO UNIVERSAL CALL WORKER ===")
    print(f"MONGO_URI: {MONGO_URI}")
    print(f"MONGO_DB: {MONGO_DB}")
    print(f"MONGO_COLL_JOBS: {MONGO_COLL_JOBS}")
    print(f"RETELL_API_KEY: {'***' + RETELL_API_KEY[-4:] if RETELL_API_KEY else 'NOT SET'}")
    print(f"RETELL_AGENT_ID: {RETELL_AGENT_ID}")
    print(f"RETELL_FROM_NUMBER: {CALL_FROM_NUMBER}")
    print(f"WORKER_COUNT: {WORKER_COUNT}")
    print("========================================\n")
    
    logging.info("Inicializando índices…")
    ensure_indexes()

    if not RETELL_API_KEY:
        logging.error("RETELL_API_KEY es requerida. Saliendo...")
        return

    if not RETELL_AGENT_ID:
        logging.error("RETELL_AGENT_ID es requerido. Saliendo...")
        return

    print(f"[DEBUG] Conectando a MongoDB...")
    store = UniversalJobStore(coll_jobs, db)
    
    print(f"[DEBUG] Inicializando cliente Retell...")
    retell = RetellClient(RETELL_API_KEY, RETELL_BASE_URL)
    
    print(f"[DEBUG] Creando universal orchestrator...")
    orch = UniversalCallOrchestrator(store, retell)

    import threading
    threads = []
    for i in range(WORKER_COUNT):
        worker_name = f"universal-bot-{i+1}"
        print(f"[DEBUG] Iniciando universal worker: {worker_name}")
        t = threading.Thread(
            target=universal_worker_loop, 
            args=(worker_name, store, orch), 
            daemon=True, 
            name=worker_name
        )
        t.start()
        threads.append(t)

    logging.info(f"{WORKER_COUNT} universal workers activos. Esperando jobs… (Ctrl+C para salir)")
    try:
        while RUNNING:
            time.sleep(1.5)
    finally:
        print("\n[DEBUG] Cerrando workers...")
        logging.info("Esperando cierre de threads...")
        for t in threads:
            t.join(timeout=3)
        logging.info("Universal worker cerrado. Bye.")


if __name__ == "__main__":
    main()