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

# ----------------------------
# Config & Logging
# ----------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(threadName)s | %(message)s"
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "speechai_db")
MONGO_COLL_JOBS = os.getenv("MONGO_COLL_JOBS", "jobs")  # Cambiar default a "jobs"
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
    def start_call(self, *, to_number: str, agent_id: str, from_number: Optional[str], context: Dict[str, Any], ring_timeout: Optional[int] = None) -> RetellResult:
        """
        Crea una llamada usando Retell v2.
        Args:
          to_number: número destino E.164
          agent_id: ID del agente Retell (el que usás en n8n)
          from_number: número origen (si tu cuenta lo requiere)
          context: variables dinámicas para el agente (mapeadas en retell_llm_dynamic_variables)
          ring_timeout: tiempo máximo de timbre en segundos (opcional)
        """
        url = f"{self.base_url}/v2/create-phone-call"

        body = {
            "to_number": str(to_number),
            "agent_id": str(agent_id),
            "retell_llm_dynamic_variables": context or {},
        }
        if from_number:
            body["from_number"] = str(from_number)
        if ring_timeout is not None:
            body["ring_timeout"] = ring_timeout

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
    def __init__(self, coll, db=None):
        self.coll = coll
        self.db = db
        
        # Acceso a colección de batches para verificar estado
        self.batches_coll = db["batches"] if db is not None else None
        
        # Check if we can update account/batch usage
        if db is not None:
            print("[DEBUG] JobStore initialized with database access for usage tracking")
        else:
            print("[WARNING] JobStore initialized without database access - usage tracking disabled")

    def claim_one(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Reserva un job 'pending' cuyo lease esté vencido o vacío.
        NUEVO: Solo toma jobs que no tengan resultado exitoso previo.
        NUEVO: No toma jobs de batches pausados (is_active=False).
        """
        now = utcnow()
        reservation = lease_expires_in(LEASE_SECONDS)
        
        print(f"[DEBUG] [{worker_id}] Buscando jobs pendientes...")
        print(f"[DEBUG] [{worker_id}] Timestamp actual: {now}")
        print(f"[DEBUG] [{worker_id}] Filtro: status=pending, sin resultado exitoso, respeta delay por persona, batch activo")

        try:
            # Primero obtener IDs de batches activos
            active_batch_ids = []
            if self.batches_coll is not None:
                active_batches_cursor = self.batches_coll.find(
                    {"is_active": True},
                    {"batch_id": 1}
                )
                active_batch_ids = [batch["batch_id"] for batch in active_batches_cursor]
                print(f"[DEBUG] [{worker_id}] Batches activos encontrados: {len(active_batch_ids)}")
            
            # Construir filtro base
            base_filter = {
                "$or": [
                    # Jobs pending normales
                    {"status": "pending"},
                    # Jobs failed listos para retry
                    {
                        "status": "failed",
                        "attempts": {"$lt": MAX_TRIES},
                        "$or": [
                            {"next_try_at": {"$exists": False}},
                            {"next_try_at": {"$lte": now}}
                        ]
                    }
                ]
            }
            
            # Agregar filtro para batches activos o jobs sin batch
            if active_batch_ids:
                base_filter["$and"] = [
                    {
                        "$or": [
                            {"batch_id": {"$in": active_batch_ids}},  # Jobs de batches activos
                            {"batch_id": {"$exists": False}},  # Jobs sin batch
                            {"batch_id": None}  # Jobs con batch_id explícitamente None
                        ]
                    }
                ]
            
            doc = self.coll.find_one_and_update(
                filter=base_filter,
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
                
                # Verificar si ya tiene resultado exitoso (doble check)
                call_result = doc.get('call_result', {})
                if call_result and call_result.get('success'):
                    print(f"[WARNING] [{worker_id}] Job ya tiene resultado exitoso, marcando como done")
                    self.mark_done(doc["_id"], call_result)
                    return None
                    
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

    def save_call_id(self, job_id, call_id: str):
        """NUEVO: Guardar call_id inmediatamente después de crear la llamada"""
        try:
            result = self.coll.update_one(
                {"_id": job_id},
                {"$set": {
                    "call_id": call_id,
                    "call_started_at": utcnow(),
                    "updated_at": utcnow(),
                    "is_calling": True
                }}
            )
            if result.modified_count > 0:
                print(f"[DEBUG] [{job_id}] ✅ Call_id guardado: {call_id}")
            else:
                print(f"[WARNING] [{job_id}] No se pudo guardar call_id")
        except PyMongoError as e:
            logging.error(f"save_call_id error: {e}")

    def save_call_result(self, job_id, call_result: Dict[str, Any], is_success: bool):
        """NUEVO: Guardar resultado completo de la llamada"""
        now = utcnow()
        
        # Calcular duración si tenemos timestamp de inicio
        call_duration = None
        job = self.coll.find_one({"_id": job_id}, {"call_started_at": 1})
        if job and job.get("call_started_at"):
            call_started = job["call_started_at"]
            # Asegurar que ambas fechas tengan el mismo timezone
            if call_started.tzinfo is None:
                call_started = call_started.replace(tzinfo=timezone.utc)
            duration_delta = now - call_started
            call_duration = int(duration_delta.total_seconds())
        
        # Extraer datos importantes del call result
        call_summary = {}
        if call_result:
            # Datos básicos de la llamada
            call_summary = {
                "call_status": call_result.get("call_status"),
                "disconnection_reason": call_result.get("disconnection_reason"),
                "duration_ms": call_result.get("duration_ms"),
                "start_timestamp": call_result.get("start_timestamp"),
                "end_timestamp": call_result.get("end_timestamp"),
            }
            
            # Call cost
            if call_result.get("call_cost"):
                call_summary["call_cost"] = call_result["call_cost"]
                
            # Call analysis
            if call_result.get("call_analysis"):
                call_summary["call_analysis"] = call_result["call_analysis"]
                
            # URLs de grabación y transcript
            call_summary["recording_url"] = call_result.get("recording_url")
            call_summary["recording_multi_channel_url"] = call_result.get("recording_multi_channel_url")
            call_summary["public_log_url"] = call_result.get("public_log_url")
            
            # Transcripción
            call_summary["transcript"] = call_result.get("transcript")
            
            # Variables dinámicas capturadas
            if call_result.get("collected_dynamic_variables"):
                call_summary["collected_dynamic_variables"] = call_result["collected_dynamic_variables"]

        update_fields = {
            "call_result": {
                "success": is_success,
                "status": call_result.get("call_status", "unknown"),
                "summary": call_summary,  # Datos estructurados importantes
                "details": call_result,    # Respuesta completa para referencia
                "timestamp": now
            },
            "call_ended_at": now,
            "updated_at": now
        }
        
        if call_duration is not None:
            update_fields["call_duration_seconds"] = call_duration
            
        # Actualizar variables dinámicas capturadas
        collected_vars = call_result.get("collected_dynamic_variables", {}) if call_result else {}
        if collected_vars:
            if collected_vars.get("fecha_pago_cliente"):
                update_fields["fecha_pago_cliente"] = collected_vars["fecha_pago_cliente"]
            if collected_vars.get("monto_pago_cliente"):
                # Convertir a número si es posible
                try:
                    update_fields["monto_pago_cliente"] = int(collected_vars["monto_pago_cliente"])
                except (ValueError, TypeError):
                    update_fields["monto_pago_cliente"] = collected_vars["monto_pago_cliente"]
            
        # Si es exitoso, marcar como done. Si no, programar reintento
        if is_success:
            update_fields["status"] = "done"
            update_fields["finished_at"] = now
        else:
            # Determinar tipo de delay según el resultado
            delay_minutes = RETRY_DELAY_MINUTES
            call_status = call_result.get("call_status") or call_result.get("status") or ""
            call_status = call_status.lower()
            
            if any(status in call_status for status in ["no_answer", "not_connected", "busy"]):
                delay_minutes = NO_ANSWER_RETRY_MINUTES
                
            next_try = now + dt.timedelta(minutes=delay_minutes)
            update_fields.update({
                "status": "failed", 
                "next_try_at": next_try,
                "last_attempt_result": call_status
            })
            
        try:
            self.coll.update_one({"_id": job_id}, {"$set": update_fields})
            print(f"[DEBUG] [{job_id}] Resultado guardado: success={is_success}, status={call_result.get('call_status')}")
            
            # 🔥 NEW: Update account and batch usage when call is successful
            if is_success and self.db is not None:
                try:
                    self._update_account_and_batch_usage_sync(job_id, call_duration, call_result)
                except Exception as e:
                    print(f"[ERROR] [{job_id}] Failed to update account/batch usage: {e}")
                    
            if not is_success:
                print(f"[DEBUG] [{job_id}] Próximo intento programado para: {update_fields.get('next_try_at')}")
        except PyMongoError as e:
            logging.error(f"save_call_result error: {e}")

    def _update_account_and_batch_usage_sync(self, job_id, call_duration: int, call_result: Dict[str, Any]):
        """Update account and batch usage after successful call using direct MongoDB operations"""
        
        # Get job details to extract account_id and batch_id
        job = self.coll.find_one({"_id": job_id}, {"account_id": 1, "batch_id": 1})
        if not job:
            print(f"[ERROR] [{job_id}] Job not found for usage update")
            return
            
        account_id = job.get("account_id")
        batch_id = job.get("batch_id")
        
        if not account_id:
            print(f"[ERROR] [{job_id}] No account_id found for usage update")
            return
            
        # Calculate call duration in minutes
        call_minutes = 0.0
        if call_duration:
            call_minutes = call_duration / 60.0
        elif call_result and call_result.get("duration_ms"):
            call_minutes = call_result["duration_ms"] / (1000 * 60.0)
            
        if call_minutes <= 0:
            call_minutes = 0.1  # Minimum billing unit
            
        print(f"[DEBUG] [{job_id}] Updating usage: {call_minutes:.2f} minutes for account {account_id}")
        
        # Extract call cost if available
        call_cost = None
        if call_result and call_result.get("call_cost"):
            cost_data = call_result["call_cost"]
            if isinstance(cost_data, dict):
                call_cost = cost_data.get("combined_cost") or cost_data.get("total_cost")
            elif isinstance(cost_data, (int, float)):
                call_cost = float(cost_data)
                
        try:
            # Update account usage directly with MongoDB
            accounts_collection = self.db.accounts
            
            # Update account: increment minutes_used and calls_today
            account_update = {
                "$inc": {
                    "minutes_used": call_minutes,
                    "calls_today": 1
                },
                "$set": {
                    "updated_at": utcnow()
                }
            }
            
            # Also update credit_used if we have call_cost
            if call_cost:
                account_update["$inc"]["credit_used"] = call_cost
            
            account_result = accounts_collection.update_one(
                {"account_id": account_id},
                account_update
            )
            
            if account_result.modified_count > 0:
                print(f"[DEBUG] [{job_id}] ✅ Account usage updated: {call_minutes:.2f} minutes for {account_id}")
            else:
                print(f"[WARNING] [{job_id}] Account {account_id} not found or not updated")
            
            # Update batch statistics if batch_id exists
            if batch_id:
                batches_collection = self.db.batches
                
                # Calculate cost in dollars (assuming call_cost is in dollars)
                cost_to_add = call_cost if call_cost else (call_minutes * 0.15)  # Default rate
                
                batch_update = {
                    "$inc": {
                        "total_cost": cost_to_add,
                        "total_minutes": call_minutes,
                        "completed_jobs": 1
                    },
                    "$set": {
                        "updated_at": utcnow()
                    }
                }
                
                batch_result = batches_collection.update_one(
                    {"batch_id": batch_id},
                    batch_update
                )
                
                if batch_result.modified_count > 0:
                    print(f"[DEBUG] [{job_id}] ✅ Batch stats updated for batch {batch_id}")
                else:
                    print(f"[WARNING] [{job_id}] Batch {batch_id} not found or not updated")
                    
        except Exception as e:
            print(f"[ERROR] [{job_id}] Failed to update account/batch usage: {e}")
            logging.error(f"Account/batch update error for job {job_id}: {e}")

    def mark_failed(self, job_id, reason: str, terminal=False, call_settings: dict = None):
        """
        Marca un job como fallido.
        
        Args:
            job_id: ID del job
            reason: Razón del fallo
            terminal: Si True, el job no se reintentará
            call_settings: Configuración del batch (para retry_delay_hours)
        """
        new_status = "failed" if terminal else "pending"
        reserved_until = None if terminal else lease_expires_in(int(LEASE_SECONDS * 1.5))
        
        update_fields = {
            "status": new_status,
            "last_error": reason,
            "updated_at": utcnow(),
            "reserved_until": reserved_until
        }
        
        # Si no es terminal, programar reintento con delay
        if not terminal:
            # Usar retry_delay_hours del batch o el default global
            retry_delay_hours = RETRY_DELAY_MINUTES / 60  # Default en horas
            if call_settings and "retry_delay_hours" in call_settings:
                retry_delay_hours = call_settings["retry_delay_hours"]
                print(f"[DEBUG] [{job_id}] Usando retry_delay_hours del batch: {retry_delay_hours}h")
            else:
                print(f"[DEBUG] [{job_id}] Usando retry_delay_hours default: {retry_delay_hours}h")
            
            next_try = utcnow() + dt.timedelta(hours=retry_delay_hours)
            update_fields["next_try_at"] = next_try
            print(f"[DEBUG] [{job_id}] Próximo reintento programado para: {next_try.isoformat()}Z")
            
        try:
            self.coll.update_one({"_id": job_id}, {"$set": update_fields})
        except PyMongoError as e:
            logging.error(f"mark_failed error: {e}")

# ----------------------------
# Call Orchestrator
# ----------------------------
class CallOrchestrator:
    def __init__(self, job_store: JobStore, retell: RetellClient):
        self.job_store = job_store
        self.retell = retell
        self.batch_cache = {}  # Cache de batches {batch_id: (batch_data, timestamp)}
        self.cache_ttl = 300  # TTL de 5 minutos
        self.batches_collection = db["batches"]  # Colección de batches
    
    def _get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un batch de MongoDB con cache
        
        Args:
            batch_id: ID del batch
        
        Returns:
            Diccionario con datos del batch o None si no existe
        """
        if not batch_id:
            return None
        
        # Verificar cache
        if batch_id in self.batch_cache:
            cached_batch, cached_at = self.batch_cache[batch_id]
            age = (utcnow() - cached_at).total_seconds()
            if age < self.cache_ttl:
                logging.debug(f"Cache hit para batch {batch_id} (age: {age:.1f}s)")
                return cached_batch
        
        # Cache miss o expirado - obtener de MongoDB
        try:
            batch = self.batches_collection.find_one({"batch_id": batch_id})
            if batch:
                self.batch_cache[batch_id] = (batch, utcnow())
                logging.debug(f"Batch {batch_id} cargado de MongoDB y cacheado")
            else:
                logging.warning(f"Batch {batch_id} no encontrado en MongoDB")
            return batch
        except Exception as e:
            logging.error(f"Error obteniendo batch {batch_id}: {e}")
            return None
    
    def _is_allowed_time(self, call_settings: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Verifica si el momento actual está dentro de los horarios permitidos
        
        Args:
            call_settings: Configuración del batch con allowed_hours, days_of_week, timezone
        
        Returns:
            Tupla (is_allowed, reason) donde:
            - is_allowed: True si está permitido llamar ahora
            - reason: Razón de rechazo si is_allowed es False
        """
        if not call_settings:
            return True, None
        
        # Obtener timezone del batch
        tz_str = call_settings.get("timezone", "America/Santiago")
        
        try:
            import pytz
            tz = pytz.timezone(tz_str)
        except:
            logging.warning(f"Timezone inválido: {tz_str}, usando America/Santiago")
            import pytz
            tz = pytz.timezone("America/Santiago")
        
        # Obtener hora actual en la timezone del batch
        from datetime import datetime
        now = datetime.now(tz)
        
        # 1. Validar día de la semana
        days_of_week = call_settings.get("days_of_week")
        if days_of_week:
            current_day = now.isoweekday()  # 1=Lunes, 7=Domingo
            
            if current_day not in days_of_week:
                reason = f"Día {current_day} ({now.strftime('%A')}) no está en días permitidos {days_of_week}"
                logging.info(f"Fuera de horario: {reason}")
                return False, reason
        
        # 2. Validar hora del día
        allowed_hours = call_settings.get("allowed_hours", {})
        if not allowed_hours:
            return True, None  # Sin restricciones de hora
        
        start_time = allowed_hours.get("start", "00:00")
        end_time = allowed_hours.get("end", "23:59")
        
        # Parsear horas (formato HH:MM)
        try:
            start_hour, start_min = map(int, start_time.split(":"))
            end_hour, end_min = map(int, end_time.split(":"))
            
            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min
            
            if not (start_minutes <= current_minutes <= end_minutes):
                reason = (
                    f"Hora actual {now.strftime('%H:%M')} fuera del rango "
                    f"permitido {start_time}-{end_time}"
                )
                logging.info(f"Fuera de horario: {reason}")
                return False, reason
        except Exception as e:
            logging.error(f"Error parseando horarios {start_time}-{end_time}: {e}")
            return True, None  # En caso de error, permitir la llamada
        
        return True, None
    
    def _calculate_next_allowed_time(self, call_settings: Dict[str, Any]) -> dt.datetime:
        """
        Calcula la próxima hora permitida para llamar
        
        Args:
            call_settings: Configuración del batch
        
        Returns:
            Datetime de la próxima hora permitida (UTC)
        """
        if not call_settings:
            return utcnow() + dt.timedelta(hours=1)  # Default: 1 hora
        
        # Obtener timezone del batch
        tz_str = call_settings.get("timezone", "America/Santiago")
        
        try:
            import pytz
            tz = pytz.timezone(tz_str)
        except:
            import pytz
            tz = pytz.timezone("America/Santiago")
        
        from datetime import datetime
        now = datetime.now(tz)
        
        # Obtener hora de inicio permitida
        allowed_hours = call_settings.get("allowed_hours", {})
        start_time = allowed_hours.get("start", "09:00")
        
        try:
            start_hour, start_min = map(int, start_time.split(":"))
        except:
            start_hour, start_min = 9, 0  # Default 09:00
        
        # Calcular próximo horario permitido
        next_allowed = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
        
        # Si ya pasó la hora de inicio hoy, programar para mañana
        if next_allowed <= now:
            next_allowed += dt.timedelta(days=1)
        
        # Verificar días de la semana
        days_of_week = call_settings.get("days_of_week")
        if days_of_week:
            max_attempts = 7  # Buscar hasta 7 días en el futuro
            for _ in range(max_attempts):
                if next_allowed.isoweekday() in days_of_week:
                    break
                next_allowed += dt.timedelta(days=1)
        
        # Convertir a UTC para MongoDB
        next_allowed_utc = next_allowed.astimezone(pytz.UTC).replace(tzinfo=None)
        
        logging.info(f"Próximo horario permitido: {next_allowed_utc.isoformat()}Z")
        return next_allowed_utc

    def _pick_next_phone(self, job: Dict[str, Any]) -> Optional[str]:
        # Adaptado para la estructura real con contact.phones y next_phone_index
        job_id = job.get('_id')
        print(f"[DEBUG] [{job_id}] _pick_next_phone iniciado")
        
        # Obtener datos del contacto
        contact = job.get('contact', {})
        phones = contact.get('phones', [])
        next_phone_index = contact.get('next_phone_index', 0)
        
        print(f"[DEBUG] [{job_id}] phones disponibles: {phones}")
        print(f"[DEBUG] [{job_id}] next_phone_index: {next_phone_index}")
        
        # Verificar si hay teléfonos disponibles
        if not phones:
            print(f"[DEBUG] [{job_id}] ❌ No hay teléfonos en contact.phones")
            return None
        
        # Verificar si el índice está dentro del rango
        if next_phone_index >= len(phones):
            print(f"[DEBUG] [{job_id}] ❌ next_phone_index ({next_phone_index}) fuera de rango (max: {len(phones)-1})")
            return None
        
        # Obtener el teléfono actual
        phone = phones[next_phone_index]
        print(f"[DEBUG] [{job_id}] ✅ Usando teléfono: {phone} (índice {next_phone_index})")
        return phone

    def _advance_phone(self, job, call_settings: dict = None):
        """
        Avanzar al siguiente teléfono en la lista.
        
        Args:
            job: Job actual
            call_settings: Configuración del batch (para retry_delay_hours)
        """
        # Avanzar al siguiente teléfono en la lista
        contact = job.get('contact', {})
        phones = contact.get('phones', [])
        current_index = contact.get('next_phone_index', 0)
        
        job_id = job.get('_id')
        print(f"[DEBUG] [{job_id}] _advance_phone: índice actual {current_index}, total phones: {len(phones)}")
        
        # Avanzar al siguiente índice
        next_index = current_index + 1
        
        try:
            # Actualizar el índice en la base de datos
            self.job_store.coll.update_one(
                {"_id": job["_id"]},
                {"$set": {
                    "contact.next_phone_index": next_index,
                    "updated_at": utcnow()
                }}
            )
            print(f"[DEBUG] [{job_id}] next_phone_index actualizado a {next_index}")
        except Exception as e:
            logging.warning(f"Error actualizando next_phone_index: {e}")
        
        # Verificar si quedan más teléfonos
        if next_index >= len(phones):
            # No quedan teléfonos: resetear índice para próximo intento
            print(f"[DEBUG] [{job_id}] ❌ No quedan más teléfonos (índice {next_index} >= {len(phones)})")
            print(f"[DEBUG] [{job_id}] Reseteando next_phone_index a 0 para próximo intento")
            
            # Resetear índice de teléfono para el próximo intento  
            try:
                self.job_store.coll.update_one(
                    {"_id": job["_id"]},
                    {"$set": {
                        "contact.next_phone_index": 0,
                        "updated_at": utcnow()
                    }}
                )
                print(f"[DEBUG] [{job_id}] next_phone_index reseteado a 0")
            except Exception as e:
                logging.warning(f"Error reseteando next_phone_index: {e}")
            
            self.job_store.mark_failed(job["_id"], "No quedan teléfonos por intentar", terminal=False, call_settings=call_settings)

    def _context_from_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mapear datos del job a variables dinámicas que espera el agente Retell.
        Usa el payload.to_retell_context() si existe, sino fallback a lógica legacy.
        IMPORTANTE: Retell requiere que TODOS los valores sean strings.
        """
        try:
            from utils.timezone_utils import chile_time_display
        except ImportError:
            # Fallback si no se puede importar la utilidad
            import datetime
            def chile_time_display():
                return datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p CLT")
        
        now_chile = chile_time_display()  # Usa nuestra utilidad centralizada
        
        # Intentar usar el payload del job (nueva arquitectura)
        payload_data = job.get("payload", {})
        if payload_data and isinstance(payload_data, dict):
            # Si el payload tiene el contexto pre-generado, usarlo
            if hasattr(payload_data, 'to_retell_context'):
                context = payload_data.to_retell_context()
            else:
                # Construir contexto desde payload dict
                context = {}
                
                # Para marketing
                if payload_data.get('offer_description'):
                    context.update({
                        'tipo_llamada': 'marketing',
                        'empresa': str(payload_data.get('company_name', '')),
                        'descripcion_oferta': str(payload_data.get('offer_description', '')),
                        'descuento_porcentaje': str(payload_data.get('discount_percentage', 0)),
                        'categoria_producto': str(payload_data.get('product_category', '')),
                        'segmento_cliente': str(payload_data.get('customer_segment', '')),
                        'tipo_campana': str(payload_data.get('campaign_type', '')),
                        'llamada_accion': str(payload_data.get('call_to_action', '')),
                        'valor_oferta': str(payload_data.get('offer_value', 0)),
                        'oferta_expira': str(payload_data.get('offer_expires', '')),
                    })
                # Para debt collection
                elif payload_data.get('debt_amount'):
                    context.update({
                        'tipo_llamada': 'cobranza',
                        'empresa': str(payload_data.get('company_name', '')),
                        'monto_total': str(payload_data.get('debt_amount', '')),
                        'fecha_limite': str(payload_data.get('due_date', '')),
                        'dias_vencidos': str(payload_data.get('overdue_days', 0)),
                        'tipo_deuda': str(payload_data.get('debt_type', '')),
                    })
                    
                    # AGREGAR VARIABLES DE ADDITIONAL_INFO para cobranza
                    additional_info = payload_data.get('additional_info', {})
                    if additional_info:
                        context.update({
                            'cantidad_cupones': str(additional_info.get('cantidad_cupones', '')),
                            'fecha_maxima': str(additional_info.get('fecha_maxima', '')),
                            'cuotas_adeudadas': str(additional_info.get('cantidad_cupones', '')),
                        })
            
            # Agregar información del contacto
            contact_data = job.get("contact", {})
            if contact_data:
                context.update({
                    'nombre': str(contact_data.get('name', '')),
                    'RUT': str(contact_data.get('dni', '')),
                })
            
            # Agregar timestamp
            context['current_time_America_Santiago'] = now_chile
            
            return {k: v for k, v in context.items() if v and v != "None"}
        
        # Fallback: Lógica legacy para jobs antiguos
        ctx = {
            "nombre": str(job.get("nombre", "")),
            "empresa": str(job.get("origen_empresa", "")),
            "RUT": str(job.get("rut_fmt") or job.get("rut", "")),
            "cantidad_cupones": str(job.get("cantidad_cupones", "")),
            "cuotas_adeudadas": str(job.get("cantidad_cupones", "")),
            "monto_total": str(job.get("monto_total", "")),
            "fecha_limite": str(job.get("fecha_limite", "")),
            "fecha_maxima": str(job.get("fecha_maxima", "")),
            "fecha_pago_cliente": "",
            "current_time_America_Santiago": now_chile,
        }
        return {k: v for k, v in ctx.items() if v and v != "None"}

    def process(self, job: Dict[str, Any]):
        job_id = job["_id"]
        
        print(f"\n[DEBUG] [{job_id}] ========== PROCESANDO JOB ==========")
        print(f"[DEBUG] [{job_id}] Job completo: {job}")
        print(f"[DEBUG] [{job_id}] ==========================================\n")
        
        # Verificar si ya tiene resultado exitoso (doble seguridad)
        call_result = job.get('call_result', {})
        if call_result and call_result.get('success'):
            print(f"[DEBUG] [{job_id}] ✅ Job ya tiene resultado exitoso, saltando")
            self.job_store.mark_done(job_id, call_result.get('details', {}))
            return
        
        # 🔥 OBTENER CALL_SETTINGS DEL BATCH (NUEVA FUNCIONALIDAD)
        batch_id = job.get('batch_id')
        batch = None
        call_settings = {}
        
        if batch_id:
            print(f"[DEBUG] [{job_id}] Obteniendo configuración del batch {batch_id}...")
            batch = self._get_batch(batch_id)
            if batch:
                call_settings = batch.get('call_settings', {})
                if call_settings:
                    print(f"[DEBUG] [{job_id}] ✅ Call settings encontrados: {call_settings}")
                else:
                    print(f"[DEBUG] [{job_id}] ⚠️ Batch sin call_settings, usando defaults")
            else:
                print(f"[WARNING] [{job_id}] Batch {batch_id} no encontrado, usando defaults")
        else:
            print(f"[DEBUG] [{job_id}] Job sin batch_id, usando configuración global")
        
        # 🕐 VALIDAR HORARIOS PERMITIDOS
        if call_settings:
            is_allowed, reason = self._is_allowed_time(call_settings)
            if not is_allowed:
                print(f"[INFO] [{job_id}] 🚫 FUERA DE HORARIO PERMITIDO - {reason}")
                # Calcular próximo horario permitido y reprogramar
                next_allowed_time = self._calculate_next_allowed_time(call_settings)
                try:
                    self.job_store.coll.update_one(
                        {"_id": job_id},
                        {
                            "$set": {
                                "status": "pending",
                                "reserved_until": next_allowed_time,
                                "last_error": f"Fuera de horario: {reason}",
                                "updated_at": utcnow()
                            }
                        }
                    )
                    print(f"[DEBUG] [{job_id}] Job reprogramado para {next_allowed_time.isoformat()}Z")
                except Exception as e:
                    logging.error(f"Error reprogramando job {job_id}: {e}")
                return
            else:
                print(f"[DEBUG] [{job_id}] ✅ Dentro de horario permitido")
        
        # 🔄 VALIDAR MAX_ATTEMPTS DEL BATCH
        max_attempts = call_settings.get("max_attempts", MAX_TRIES)
        current_tries = job.get("tries", 0)
        
        print(f"[DEBUG] [{job_id}] Intentos: {current_tries}/{max_attempts}")
        
        if current_tries >= max_attempts:
            print(f"[ERROR] [{job_id}] 🚫 MÁXIMO DE INTENTOS ALCANZADO ({current_tries}/{max_attempts})")
            self.job_store.mark_failed(job_id, f"Máximo de intentos alcanzado ({max_attempts})", terminal=True)
            return
        
        # 🔥 VALIDACIÓN DE BALANCE - CRÍTICA PARA SAAS
        account_id = job.get('account_id')
        if account_id:
            try:
                # Acceder a la base de datos
                if self.job_store.db is not None:
                    account_doc = self.job_store.db.accounts.find_one({"account_id": account_id})
                else:
                    # Fallback usando la colección existente
                    db = self.job_store.coll.database
                    account_doc = db.accounts.find_one({"account_id": account_id})
                
                if account_doc:
                    plan_type = account_doc.get('plan_type')
                    
                    # Validación según tipo de plan
                    has_balance = True
                    error_msg = ""
                    
                    if plan_type == "unlimited":
                        has_balance = True
                    elif plan_type == "minutes_based":
                        minutes_purchased = account_doc.get('minutes_purchased', 0)
                        minutes_used = account_doc.get('minutes_used', 0) 
                        minutes_reserved = account_doc.get('minutes_reserved', 0)
                        minutes_remaining = max(0, minutes_purchased - minutes_used - minutes_reserved)
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
                        return
                    else:
                        print(f"[DEBUG] [{job_id}] ✅ Balance suficiente - Plan: {plan_type}")
                else:
                    print(f"[ERROR] [{job_id}] Cuenta {account_id} no encontrada")
                    self.job_store.mark_failed(job_id, f"Cuenta {account_id} no encontrada", terminal=True)
                    return
            except Exception as e:
                print(f"[ERROR] [{job_id}] Error validando balance: {e}")
                self.job_store.mark_failed(job_id, f"Error validando balance: {e}", terminal=True)
                return
        else:
            print(f"[ERROR] [{job_id}] Sin account_id en job")
            self.job_store.mark_failed(job_id, "Sin account_id especificado", terminal=True)
            return
        
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
        
        # Usar ring_timeout del batch si está disponible
        ring_timeout = call_settings.get("ring_timeout") if call_settings else None
        if ring_timeout:
            print(f"[DEBUG] [{job_id}] Usando ring_timeout del batch: {ring_timeout}s")
        
        res = self.retell.start_call(
            to_number=phone,
            agent_id=RETELL_AGENT_ID,
            from_number=CALL_FROM_NUMBER,
            context=context,
            ring_timeout=ring_timeout
        )

        print(f"[DEBUG] [{job_id}] Resultado Retell: success={res.success}, error={res.error}")
        print(f"[DEBUG] [{job_id}] Call_id: {res.call_id}, Raw response: {res.raw}")

        if not res.success:
            err = res.error or "Retell start_call error"
            print(f"[ERROR] [{job_id}] Error al iniciar llamada: {err}")
            logging.warning(f"[{job_id}] Error al iniciar llamada: {err}")
            self._advance_phone(job, call_settings)
            return

        call_id = res.call_id or "unknown"
        print(f"[DEBUG] [{job_id}] ✅ Llamada creada exitosamente - call_id: {call_id}")
        
        # NUEVO: Guardar call_id inmediatamente
        self.job_store.save_call_id(job_id, call_id)
        
        logging.info(f"[{job_id}] Call creada en Retell (call_id={call_id}). Iniciando seguimiento...")
        
        # NUEVO: Seguimiento completo como workflow n8n con max_call_duration del batch
        max_call_duration = call_settings.get("max_call_duration") if call_settings else None
        final_result = self._poll_call_until_completion(job_id, call_id, max_call_duration)
        
        if final_result:
            # Determinar si es exitoso según el status
            status = (final_result.get("call_status") or final_result.get("status") or "").lower()
            is_success = status in {"completed", "finished", "done", "ended"}
            
            # Guardar resultado completo
            self.job_store.save_call_result(job_id, final_result, is_success)
            
            if is_success:
                logging.info(f"[{job_id}] ✅ Llamada completada exitosamente")
            else:
                logging.info(f"[{job_id}] ❌ Llamada falló (status={status}), se reintentará según configuración")
                self._advance_phone(job, call_settings)
        else:
            # Timeout o error en el seguimiento
            logging.warning(f"[{job_id}] Timeout en seguimiento de llamada")
            self.job_store.mark_failed(job_id, "Timeout en seguimiento de llamada", terminal=False, call_settings=call_settings)

    def _poll_call_until_completion(self, job_id, call_id: str, max_call_duration: int = None) -> Optional[Dict[str, Any]]:
        """
        NUEVO: Hace pooling como el workflow de n8n hasta que la llamada termine
        
        Args:
            job_id: ID del job
            call_id: ID de la llamada en Retell
            max_call_duration: Duración máxima en segundos (del batch o default)
        """
        print(f"[DEBUG] [{job_id}] Iniciando pooling para call_id: {call_id}")
        
        # Usar max_call_duration del batch o el default global
        if max_call_duration is None:
            max_call_duration = CALL_MAX_DURATION_MINUTES * 60
            print(f"[DEBUG] [{job_id}] Usando max_call_duration default: {max_call_duration}s")
        else:
            print(f"[DEBUG] [{job_id}] Usando max_call_duration del batch: {max_call_duration}s")
        
        max_duration_seconds = max_call_duration
        start_time = time.time()
        
        # Espera inicial (como en workflow n8n)
        print(f"[DEBUG] [{job_id}] Esperando {CALL_POLLING_INTERVAL} segundos antes del primer poll...")
        time.sleep(CALL_POLLING_INTERVAL * rand_jitter(0.8, 1.2))
        
        while time.time() - start_time < max_duration_seconds:
            self.job_store.extend_lease(job_id)
            
            print(f"[DEBUG] [{job_id}] Consultando estado de llamada...")
            status_payload = self.retell.get_call_status(call_id)
            print(f"[DEBUG] [{job_id}] Status response: {status_payload}")
            
            # Manejar errores de API
            if "error" in status_payload:
                print(f"[ERROR] [{job_id}] Error en get_call_status: {status_payload}")
                time.sleep(CALL_POLLING_INTERVAL * 2)  # Esperar más en caso de error
                continue
            
            status = (status_payload.get("call_status") or status_payload.get("status") or "").lower()
            print(f"[DEBUG] [{job_id}] Status extraído: '{status}'")
            
            # Estados finales (como en workflow n8n)
            if status in {"ended", "error", "not_connected", "completed", "finished", "done", "failed"}:
                print(f"[DEBUG] [{job_id}] ✅ Estado final detectado: {status}")
                return status_payload
                
            # Estados en progreso - continuar pooling
            if status in {"in_progress", "ongoing", "active", "ringing", "connecting"}:
                print(f"[DEBUG] [{job_id}] ⏳ Llamada en progreso ({status}), continuando pooling...")
            else:
                print(f"[DEBUG] [{job_id}] ⚠️ Estado desconocido: {status}, continuando pooling...")
            
            # Esperar antes del siguiente poll
            time.sleep(CALL_POLLING_INTERVAL * rand_jitter(0.9, 1.1))
        
        print(f"[WARNING] [{job_id}] ⏰ Timeout alcanzado después de {CALL_MAX_DURATION_MINUTES} minutos")
        # Hacer una consulta final
        final_status = self.retell.get_call_status(call_id)
        return final_status if "error" not in final_status else None

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
    store = JobStore(coll_jobs, db)
    
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
