import os
import time
import uuid
import json
import signal
import random
import logging
import datetime as dt
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

import requests
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError
from tenacity import retry, wait_exponential_jitter, stop_after_attempt
from dotenv import load_dotenv

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

RETELL_AGENT_ID = os.getenv("RETELL_AGENT_ID", "")
CALL_FROM_NUMBER = os.getenv("RETELL_FROM_NUMBER", "")


# Campos esperados en cada job insertado por tu workflow de adquisición
# Ejemplo de documento:
# {
#   _id,
#   "status": "pending" | "in_progress" | "done" | "failed",
#   "reserved_until": ISODate or null,
#   "tries": 0,
#   "contact": {
#       "name": "Juan Perez",
#       "dni": "12345678",
#       "phones": ["+54911....", "+549351...."],
#       "next_phone_index": 0
#   },
#   "payload": {
#       "debt_amount": 12345.67,
#       "due_date": "2025-09-01",
#       ... (cualquier campo que quieras pasar a Retell como contexto)
#   },
#   "mode": "continuous" | "single"
# }

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
    """
    Crea índices para performance y locking confiable.
    """
    # Búsqueda de pendientes liberados
    coll_jobs.create_index(
        [("status", 1), ("reserved_until", 1)],
        name="status_reserved_idx"
    )
    # Control por tries
    coll_jobs.create_index(
        [("tries", 1)],
        name="tries_idx"
    )
    # Por contacto y estado (reportes) - adaptado para estructura real
    coll_jobs.create_index(
        [("rut", 1), ("status", 1)],
        name="rut_status_idx"
    )
    logging.info("Índices verificados/creados.")

# ----------------------------
# Retell Client (mínimo)
# ----------------------------
@dataclass
@dataclass
class RetellResult:
    success: bool
    call_id: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class RetellClient:
    """
    Cliente Retell v2 minimalista.
    - Crea llamadas con /v2/create-phone-call
    - Lee estado con /v2/get-call/{call_id}
    Espera:
      headers: Authorization: Bearer <RETELL_API_KEY>
      body: { from_number, to_number, agent_id, retell_llm_dynamic_variables }
    """
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
        """
        Crea una llamada usando Retell v2.
        Args:
          to_number: número destino E.164
          agent_id: ID del agente Retell (el que usás en n8n)
          from_number: número origen (si tu cuenta lo requiere)
          context: variables dinámicas para el agente (mapeadas en retell_llm_dynamic_variables)
        """
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

            # Retell v2 suele devolver { call_id, ... } o { data: { call_id, ... } }
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
        """
        Lee estado de la llamada (v2).
        """
        url = f"{self.base_url}/v2/get-call/{call_id}"
        resp = requests.get(url, headers=self._headers(), timeout=20)
        try:
            return resp.json()
        except Exception:
            return {"error": resp.text, "status_code": resp.status_code}

# ----------------------------
# Job Store
# ----------------------------
class JobStore:
    def __init__(self, coll):
        self.coll = coll

    def claim_one(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Reserva un job 'pending' cuyo lease esté vencido o vacío.
        """
        now = utcnow()
        reservation = lease_expires_in(LEASE_SECONDS)
        
        print(f"[DEBUG] [{worker_id}] Buscando jobs pendientes...")
        print(f"[DEBUG] [{worker_id}] Timestamp actual: {now}")
        print(f"[DEBUG] [{worker_id}] Filtro: status=pending, attempts < max_attempts")

        try:
            doc = self.coll.find_one_and_update(
                filter={
                    "status": "pending",
                    "$or": [
                        {"reserved_until": {"$lt": now}},
                        {"reserved_until": {"$exists": False}},
                        {"reserved_until": None},
                    ],
                    # Adaptado para tu estructura: usar "attempts" en lugar de "tries"
                    "$expr": {
                        "$lt": [
                            {"$ifNull": ["$attempts", 0]}, 
                            {"$ifNull": ["$max_attempts", 3]}
                        ]
                    }
                },
                update={
                    "$set": {
                        "status": "in_progress",
                        "reserved_until": reservation,
                        "worker_id": worker_id,
                        "started_at": now,
                        "updated_at": now,
                    },
                    # Incrementar "attempts" en lugar de "tries"
                    "$inc": {"attempts": 1}
                },
                return_document=ReturnDocument.AFTER
            )
            
            if doc:
                print(f"[DEBUG] [{worker_id}] ✅ Job encontrado: {doc.get('_id')}")
                print(f"[DEBUG] [{worker_id}] Job data: RUT={doc.get('rut')}, Status={doc.get('status')}, Attempts={doc.get('attempts')}")
                print(f"[DEBUG] [{worker_id}] Phone: {doc.get('to_number')}, Try_phones: {doc.get('try_phones')}")
            else:
                print(f"[DEBUG] [{worker_id}] ❌ No se encontraron jobs pendientes")
                
            return doc
        except PyMongoError as e:
            print(f"[ERROR] [{worker_id}] Error en claim_one: {e}")
            logging.error(f"claim_one error: {e}")
            return None

    def extend_lease(self, job_id):
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

    def mark_done(self, job_id, retell_payload=None):
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

    def mark_failed(self, job_id, reason: str, terminal=False):
        new_status = "failed" if terminal else "pending"
        reserved_until = None if terminal else lease_expires_in(int(LEASE_SECONDS * 1.5))
        try:
            self.coll.update_one(
                {"_id": job_id},
                {"$set": {
                    "status": new_status,
                    "last_error": reason,
                    "updated_at": utcnow(),
                    "reserved_until": reserved_until
                }}
            )
        except PyMongoError as e:
            logging.error(f"mark_failed error: {e}")

# ----------------------------
# Call Orchestrator
# ----------------------------
class CallOrchestrator:
    def __init__(self, job_store: JobStore, retell: RetellClient):
        self.job_store = job_store
        self.retell = retell

    def _pick_next_phone(self, job: Dict[str, Any]) -> Optional[str]:
        # Adaptado para la estructura real de tus datos
        # Estructura esperada: {"to_number": "+56991975219", "try_phones": [...]}
        
        job_id = job.get('_id')
        print(f"[DEBUG] [{job_id}] _pick_next_phone iniciado")
        print(f"[DEBUG] [{job_id}] to_number: {job.get('to_number')}")
        print(f"[DEBUG] [{job_id}] try_phones: {job.get('try_phones')}")
        print(f"[DEBUG] [{job_id}] last_phone_tried: {job.get('last_phone_tried')}")
        
        # Primero intentar to_number principal
        if job.get("to_number") and not job.get("last_phone_tried"):
            phone = job["to_number"]
            print(f"[DEBUG] [{job_id}] Usando to_number principal: {phone}")
            return phone
        
        # Luego intentar try_phones array
        try_phones = job.get("try_phones") or []
        last_tried = job.get("last_phone_tried")
        
        for phone in try_phones:
            if phone != last_tried:
                print(f"[DEBUG] [{job_id}] Usando try_phone: {phone}")
                return phone
        
        print(f"[DEBUG] [{job_id}] ❌ No hay más teléfonos disponibles")
        return None

    def _advance_phone(self, job):
        # Marcar el teléfono actual como intentado y avanzar
        current_phone = self._pick_next_phone(job)
        if current_phone:
            # Actualizar last_phone_tried para seguir el progreso
            try:
                self.job_store.coll.update_one(
                    {"_id": job["_id"]},
                    {"$set": {
                        "last_phone_tried": current_phone,
                        "updated_at": utcnow()
                    }}
                )
            except Exception as e:
                logging.warning(f"Error actualizando last_phone_tried: {e}")
        
        # Verificar si quedan más teléfonos
        to_number = job.get("to_number")
        try_phones = job.get("try_phones") or []
        last_tried = job.get("last_phone_tried")
        
        remaining_phones = []
        if to_number and to_number != last_tried:
            remaining_phones.append(to_number)
        for phone in try_phones:
            if phone != last_tried:
                remaining_phones.append(phone)
        
        if not remaining_phones:
            # No quedan teléfonos: fallo terminal
            self.job_store.mark_failed(job["_id"], "No quedan teléfonos por intentar", terminal=True)

    def _context_from_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos del job a variables dinámicas que espera el agente Retell.
        Variables basadas en el prompt de Retell:
        - {{nombre}}, {{empresa}}, {{cuotas_adeudadas}}, {{monto_total}}, {{fecha_limite}}, {{fecha_maxima}}
        IMPORTANTE: Retell requiere que TODOS los valores sean strings.
        """
        ctx = {
            "nombre": str(job.get("nombre", "")),  # Para {{nombre}}
            "empresa": str(job.get("origen_empresa", "")),  # Para {{empresa}}
            "cuotas_adeudadas": str(job.get("cantidad_cupones", "")),  # Para {{cuotas_adeudadas}}
            "monto_total": str(job.get("monto_total", "")),  # Para {{monto_total}}
            "fecha_limite": str(job.get("fecha_limite", "")),  # Para {{fecha_limite}}
            "fecha_maxima": str(job.get("fecha_maxima", "")),  # Para {{fecha_maxima}}
            # Variables adicionales para logging/debugging
            "rut": str(job.get("rut", "")), 
            "dni": str(job.get("rut_fmt", "")),
            "batch_id": str(job.get("batch_id", "")),
            "phone_number": str(job.get("to_number", ""))
        }
        return {k: v for k, v in ctx.items() if v and v != "None"}  # Excluir valores vacíos o "None"

    def process(self, job: Dict[str, Any]):
        job_id = job["_id"]
        
        print(f"\n[DEBUG] [{job_id}] ========== PROCESANDO JOB ==========")
        print(f"[DEBUG] [{job_id}] Job completo: {job}")
        print(f"[DEBUG] [{job_id}] ==========================================\n")
        
        phone = self._pick_next_phone(job)
        if not phone:
            print(f"[ERROR] [{job_id}] Sin teléfono válido disponible")
            self.job_store.mark_failed(job_id, "Sin teléfono válido", terminal=True)
            return

        context = self._context_from_job(job)
        print(f"[DEBUG] [{job_id}] Context enviado a Retell: {context}")
        
        logging.info(f"[{job_id}] Llamando a {phone} (RUT: {job.get('rut')}, Nombre: {job.get('nombre')}) - agent_id={RETELL_AGENT_ID}")
        self.job_store.extend_lease(job_id)

        # Inicia la llamada con Retell
        print(f"[DEBUG] [{job_id}] Iniciando llamada a Retell...")
        print(f"[DEBUG] [{job_id}] Parámetros: phone={phone}, agent_id={RETELL_AGENT_ID}, from_number={CALL_FROM_NUMBER}")
        
        res = self.retell.start_call(
            to_number=phone,
            agent_id=RETELL_AGENT_ID,   # ✅ CORREGIDO: usar agent_id
            from_number=CALL_FROM_NUMBER,
            context=context
        )

        print(f"[DEBUG] [{job_id}] Resultado Retell: success={res.success}, error={res.error}")
        print(f"[DEBUG] [{job_id}] Call_id: {res.call_id}, Raw response: {res.raw}")

        if not res.success:
            err = res.error or "Retell start_call error"
            print(f"[ERROR] [{job_id}] Error al iniciar llamada: {err}")
            logging.warning(f"[{job_id}] Error al iniciar llamada: {err}")
            self._advance_phone(job)
            return

        call_id = res.call_id or "unknown"
        print(f"[DEBUG] [{job_id}] ✅ Llamada creada exitosamente - call_id: {call_id}")
        logging.info(f"[{job_id}] Call creada en Retell (call_id={call_id}). Pooling corto...")
        self.job_store.extend_lease(job_id)

        # Pooling de estado (si no usás webhook)
        print(f"[DEBUG] [{job_id}] Esperando 5 segundos antes del pooling...")
        time.sleep(5 * rand_jitter())
        self.job_store.extend_lease(job_id)
        
        print(f"[DEBUG] [{job_id}] Consultando estado de la llamada...")
        status_payload = self.retell.get_call_status(call_id)
        print(f"[DEBUG] [{job_id}] Status response: {status_payload}")
        
        status = (status_payload.get("status") or "").lower()
        print(f"[DEBUG] [{job_id}] Status extraído: '{status}'")

        if status in {"completed", "finished", "done"}:
            print(f"[DEBUG] [{job_id}] ✅ Llamada completada exitosamente")
            self.job_store.mark_done(job_id, retell_payload=status_payload)
            logging.info(f"[{job_id}] Llamada finalizada OK.")
        elif status in {"in_progress", "ongoing", ""}:
            print(f"[DEBUG] [{job_id}] ⏳ Llamada en progreso, programando reintento")
            self.job_store.mark_failed(job_id, "Timeout de pooling; esperar webhook o reintentar", terminal=False)
            logging.info(f"[{job_id}] Estado no conclusivo. Reintento posterior.")
        else:
            print(f"[DEBUG] [{job_id}] ❌ Llamada fallida, probando siguiente teléfono")
            self._advance_phone(job)
            logging.info(f"[{job_id}] Llamada fallida (status={status}). Probamos siguiente teléfono si existe.")

# ----------------------------
# Worker Loop
# ----------------------------
RUNNING = True

def _graceful_stop(signum, frame):
    global RUNNING
    RUNNING = False
    logging.info("Recibida señal de stop. Cerrando...")

signal.signal(signal.SIGINT, _graceful_stop)
signal.signal(signal.SIGTERM, _graceful_stop)

def worker_loop(name: str, store: JobStore, orch: CallOrchestrator):
    jitter_first = random.uniform(0, 1.5)
    print(f"[DEBUG] [{name}] Worker iniciando en {jitter_first:.2f} segundos...")
    time.sleep(jitter_first)  # arranque escalonado
    
    print(f"[DEBUG] [{name}] Worker activo y buscando jobs...")
    
    while RUNNING:
        try:
            print(f"[DEBUG] [{name}] Intentando obtener un job...")
            job = store.claim_one(worker_id=name)
            if not job:
                print(f"[DEBUG] [{name}] No hay jobs disponibles, esperando...")
                time.sleep(1.0 * rand_jitter(0.5, 1.5))
                continue
                
            print(f"[DEBUG] [{name}] ✅ Job obtenido, iniciando procesamiento...")
            orch.process(job)
            print(f"[DEBUG] [{name}] Job procesado, buscando el siguiente...")
            
        except Exception as e:
            print(f"[ERROR] [{name}] Excepción en worker_loop: {e}")
            logging.exception(f"[{name}] Excepción en worker_loop: {e}")
            time.sleep(2.0 * rand_jitter())

def main():
    print("\n=== INICIANDO CALL WORKER ===")
    print(f"MONGO_URI: {MONGO_URI}")
    print(f"MONGO_DB: {MONGO_DB}")
    print(f"MONGO_COLL_JOBS: {MONGO_COLL_JOBS}")
    print(f"RETELL_API_KEY: {'***' + RETELL_API_KEY[-4:] if RETELL_API_KEY else 'NOT SET'}")
    print(f"RETELL_AGENT_ID: {RETELL_AGENT_ID}")
    print(f"RETELL_FROM_NUMBER: {CALL_FROM_NUMBER}")
    print(f"WORKER_COUNT: {WORKER_COUNT}")
    print("==============================\n")
    
    logging.info("Inicializando índices…")
    ensure_indexes()

    if not RETELL_API_KEY:
        logging.error("RETELL_API_KEY es requerida. Saliendo...")
        return

    if not RETELL_AGENT_ID:
        logging.error("RETELL_AGENT_ID es requerido. Saliendo...")
        return

    print(f"[DEBUG] Conectando a MongoDB...")
    store = JobStore(coll_jobs)
    
    print(f"[DEBUG] Inicializando cliente Retell...")
    retell = RetellClient(RETELL_API_KEY, RETELL_BASE_URL)
    
    print(f"[DEBUG] Creando orchestrator...")
    orch = CallOrchestrator(store, retell)

    import threading
    threads = []
    for i in range(WORKER_COUNT):
        worker_name = f"bot-{i+1}"
        print(f"[DEBUG] Iniciando worker: {worker_name}")
        t = threading.Thread(target=worker_loop, args=(worker_name, store, orch), daemon=True, name=worker_name)
        t.start()
        threads.append(t)

    logging.info(f"{WORKER_COUNT} workers activos. Esperando jobs… (Ctrl+C para salir)")
    try:
        while RUNNING:
            time.sleep(1.5)
    finally:
        print("\n[DEBUG] Cerrando workers...")
        logging.info("Esperando cierre de threads...")
        for t in threads:
            t.join(timeout=3)
        logging.info("Listo. Bye.")

if __name__ == "__main__":
    main()
