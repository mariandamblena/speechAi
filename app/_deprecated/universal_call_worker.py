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
from domain.models import JobModel

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
MONGO_COLL_JOBS = os.getenv("MONGO_COLL_JOBS", "jobs")
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

# Continuará en el siguiente archivo...