# 🔄 Flujo Completo: Call Settings desde Creación hasta Ejecución

## Fecha de creación: 26 de Octubre, 2025

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Fase 1: Creación del Batch](#fase-1-creación-del-batch)
4. [Fase 2: Almacenamiento en MongoDB](#fase-2-almacenamiento-en-mongodb)
5. [Fase 3: Worker Obtiene Call Settings](#fase-3-worker-obtiene-call-settings)
6. [Fase 4: Validaciones del Worker](#fase-4-validaciones-del-worker)
7. [Fase 5: Ejecución de la Llamada](#fase-5-ejecución-de-la-llamada)
8. [Estructura de Datos](#estructura-de-datos)
9. [Logs de Ejemplo](#logs-de-ejemplo)
10. [Diagrama de Flujo](#diagrama-de-flujo)

---

## 🎯 Resumen Ejecutivo

### ¿Qué son los Call Settings?

Los **call_settings** son la configuración específica que controla cómo y cuándo se ejecutan las llamadas de un batch. Incluyen:

- ⏱️ **Duración máxima** de cada llamada
- 📞 **Timeout de timbre** (ring_timeout)
- 🔄 **Número de reintentos** permitidos
- ⏰ **Horarios permitidos** (días y horas)
- 🌍 **Timezone** del batch
- 🎯 **Prioridad** del batch
- ⏳ **Delay entre reintentos**

### Flujo Simplificado

```
Frontend → API → BatchCreationService → MongoDB (Batch + Call Settings)
                                              ↓
                                        Worker (claim_one)
                                              ↓
                                    _get_batch(batch_id)
                                              ↓
                                    call_settings extraídos
                                              ↓
                                    Validaciones aplicadas
                                              ↓
                                    Retell AI (llamada)
```

---

## 🏗️ Arquitectura del Sistema

### Componentes Principales

```
┌─────────────────┐
│    Frontend     │ Envía call_settings_json
│   (React)       │
└────────┬────────┘
         │
         ↓ POST /api/v1/batches/excel/create
┌─────────────────┐
│   FastAPI       │ Recibe y parsea JSON
│   (api.py)      │
└────────┬────────┘
         │
         ↓ create_batch_from_excel()
┌─────────────────┐
│ BatchCreation   │ Crea Batch + Jobs
│    Service      │ Guarda call_settings en Batch
└────────┬────────┘
         │
         ↓ insert_one()
┌─────────────────┐
│    MongoDB      │ Colección "batches"
│   (batches)     │ { batch_id, call_settings, ... }
└────────┬────────┘
         │
         ↓ find_one()
┌─────────────────┐
│  Call Worker    │ Lee call_settings del batch
│ (CallOrchestrator)│ Aplica validaciones
└────────┬────────┘
         │
         ↓ start_call()
┌─────────────────┐
│   Retell AI     │ Ejecuta llamada
│                 │
└─────────────────┘
```

---

## 📥 Fase 1: Creación del Batch

### 1.1 Frontend Envía Request

```javascript
// Frontend: Construcción de FormData
const formData = new FormData();
formData.append('account_id', 'retail_express');
formData.append('batch_name', 'Cobranza Octubre');
formData.append('processing_type', 'basic');
formData.append('file', excelFile);

// ✅ CALL SETTINGS - Enviado como JSON string
const callSettings = {
  max_call_duration: 300,        // 5 minutos
  ring_timeout: 30,              // 30 segundos timbre
  max_attempts: 3,               // 3 reintentos
  retry_delay_hours: 24,         // 24 horas entre reintentos
  allowed_hours: {
    start: "09:00",              // Desde las 9 AM
    end: "18:00"                 // Hasta las 6 PM
  },
  days_of_week: [1, 2, 3, 4, 5], // Lunes a Viernes
  timezone: "America/Santiago",  // Timezone Chile
  priority: 1                    // Prioridad normal
};

formData.append('call_settings_json', JSON.stringify(callSettings));

// Opcional: Fechas dinámicas
formData.append('dias_fecha_limite', '30');  // HOY + 30 días
formData.append('dias_fecha_maxima', '45');  // HOY + 45 días

// Enviar a backend
await fetch('/api/v1/batches/excel/create', {
  method: 'POST',
  body: formData
});
```

### 1.2 Backend Recibe y Parsea

**Archivo**: `app/api.py`

```python
@app.post("/api/v1/batches/excel/create")
async def create_batch_from_excel(
    account_id: str = Form(...),
    batch_name: str = Form(...),
    processing_type: str = Form("basic"),
    file: UploadFile = File(...),
    allow_duplicates: bool = Form(False),
    dias_fecha_limite: Optional[int] = Form(None),
    dias_fecha_maxima: Optional[int] = Form(None),
    call_settings_json: Optional[str] = Form(None),  # ← JSON string
    chile_service: ChileBatchService = Depends(get_chile_batch_service)
):
    # 1. Parsear call_settings de JSON string a dict
    call_settings = None
    if call_settings_json:
        try:
            call_settings = json.loads(call_settings_json)
            logger.info(f"Call settings parseados: {call_settings}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando call_settings_json: {e}")
    
    # 2. Leer archivo Excel
    file_content = await file.read()
    
    # 3. Llamar al servicio de creación
    result = await chile_service.create_batch_from_excel(
        file_content=file_content,
        account_id=account_id,
        batch_name=batch_name,
        allow_duplicates=allow_duplicates,
        dias_fecha_limite=dias_fecha_limite,
        dias_fecha_maxima=dias_fecha_maxima,
        call_settings=call_settings  # ← Pasa dict a servicio
    )
    
    return result
```

### 1.3 Servicio Crea Batch

**Archivo**: `app/services/batch_creation_service.py`

```python
async def create_batch_from_excel(
    self, 
    file_content: bytes, 
    account_id: str, 
    batch_name: str = None,
    dias_fecha_limite: Optional[int] = None,
    dias_fecha_maxima: Optional[int] = None,
    call_settings: Optional[Dict[str, Any]] = None  # ← Recibe dict
) -> Dict[str, Any]:
    
    # ... procesamiento de Excel y validaciones ...
    
    # Crear modelo de Batch
    batch = BatchModel(
        account_id=account_id,
        batch_id=batch_id,
        name=batch_name,
        total_jobs=len(valid_debtors),
        pending_jobs=len(valid_debtors),
        call_settings=call_settings,  # ← Guarda en modelo
        created_at=datetime.utcnow()
    )
    
    # Guardar batch en MongoDB
    batch_doc = await self.db.batches.insert_one(batch.to_dict())
    
    # Crear jobs (NO llevan call_settings individuales)
    jobs_created = await self._create_jobs_from_debtors(
        valid_debtors, 
        account_id, 
        batch_id
    )
    
    return {
        'success': True,
        'batch_id': batch_id,
        'total_jobs': len(jobs_created)
    }
```

---

## 💾 Fase 2: Almacenamiento en MongoDB

### 2.1 Estructura del Batch en MongoDB

**Colección**: `batches`

```json
{
  "_id": ObjectId("68fe5a10cb0445175e2fe28b"),
  "account_id": "retail_express",
  "batch_id": "batch-2025-10-26-142744-439872",
  "name": "Cobranza Octubre",
  "total_jobs": 12,
  "pending_jobs": 12,
  "completed_jobs": 0,
  "is_active": true,
  "estimated_cost": 5.64,
  "created_at": ISODate("2025-10-26T17:27:44.582Z"),
  
  // ✅ CALL SETTINGS - Guardados en el batch
  "call_settings": {
    "max_call_duration": 300,
    "ring_timeout": 30,
    "max_attempts": 3,
    "retry_delay_hours": 24,
    "allowed_hours": {
      "start": "09:00",
      "end": "18:00"
    },
    "days_of_week": [1, 2, 3, 4, 5],
    "timezone": "America/Santiago",
    "priority": 1
  }
}
```

### 2.2 Estructura de los Jobs en MongoDB

**Colección**: `jobs`

```json
{
  "_id": ObjectId("..."),
  "account_id": "retail_express",
  "batch_id": "batch-2025-10-26-142744-439872",  // ← Referencia al batch
  "deduplication_key": "retail_express::135098329::batch-2025-10-26-142744-439872",
  "status": "pending",
  "attempts": 0,
  "reserved_until": null,
  
  // Información del contacto
  "contact": {
    "name": "Juan Pérez",
    "dni": "135098329",
    "phones": ["+56938773910"],
    "next_phone_index": 0
  },
  
  // Payload para Retell AI
  "payload": {
    "debt_amount": 150000,
    "due_date": "2025-11-25",
    "company_name": "Retail Express",
    "additional_info": {
      "cantidad_cupones": 3,
      "fecha_maxima": "2025-12-10"
    }
  },
  
  "created_at": ISODate("2025-10-26T17:27:44.854Z"),
  "updated_at": ISODate("2025-10-26T17:27:44.854Z")
  
  // ⚠️ NOTA: Jobs NO tienen call_settings propios
  // Se obtienen desde el batch via batch_id
}
```

### 2.3 Relación Batch ↔ Jobs

```
┌────────────────────────────────┐
│         BATCH                  │
│  batch_id: "batch-2025..."     │
│  call_settings: {...}          │ ← Configuración centralizada
└────────────────────────────────┘
                │
                │ Referenciado por
                │
    ┌───────────┴───────────┬───────────────┐
    ↓                       ↓               ↓
┌─────────┐           ┌─────────┐     ┌─────────┐
│  JOB 1  │           │  JOB 2  │     │  JOB 3  │
│ batch_id│           │ batch_id│     │ batch_id│
└─────────┘           └─────────┘     └─────────┘
```

**Ventaja**: Un solo lugar para actualizar call_settings → afecta todos los jobs del batch

---

## 🤖 Fase 3: Worker Obtiene Call Settings

### 3.1 Worker Busca Jobs Pendientes

**Archivo**: `app/call_worker.py` → Clase `JobStore`

```python
def claim_one(self, worker_id: str) -> Optional[Dict[str, Any]]:
    """
    Reserva un job 'pending' para procesarlo
    Solo toma jobs de batches activos (is_active=True)
    """
    now = utcnow()
    
    # 1. Obtener IDs de batches activos
    active_batch_ids = []
    if self.batches_coll is not None:
        active_batches = self.batches_coll.find(
            {"is_active": True},  # ← Solo batches activos
            {"batch_id": 1}
        )
        active_batch_ids = [b["batch_id"] for b in active_batches]
    
    # 2. Buscar job pendiente de batch activo
    base_filter = {
        "$or": [
            {"status": "pending"},
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
    
    if active_batch_ids:
        base_filter["$and"] = [
            {
                "$or": [
                    {"batch_id": {"$in": active_batch_ids}},  # De batches activos
                    {"batch_id": {"$exists": False}},         # O sin batch
                ]
            }
        ]
    
    # 3. Reservar job para este worker
    job = self.coll.find_one_and_update(
        filter=base_filter,
        update={
            "$set": {
                "status": "in_progress",
                "reserved_until": lease_expires_in(LEASE_SECONDS),
                "worker_id": worker_id,
                "started_at": now
            },
            "$inc": {"attempts": 1}
        },
        return_document=ReturnDocument.AFTER
    )
    
    return job  # Retorna job con batch_id
```

### 3.2 Worker Obtiene Batch Completo

**Archivo**: `app/call_worker.py` → Clase `CallOrchestrator`

```python
def _get_batch(self, batch_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene un batch de MongoDB con cache (TTL: 5 minutos)
    """
    if not batch_id:
        return None
    
    # Verificar cache
    if batch_id in self.batch_cache:
        cached_batch, cached_at = self.batch_cache[batch_id]
        age = (utcnow() - cached_at).total_seconds()
        if age < self.cache_ttl:  # 300 segundos
            return cached_batch
    
    # Cache miss - obtener de MongoDB
    try:
        batch = self.batches_collection.find_one({"batch_id": batch_id})
        if batch:
            self.batch_cache[batch_id] = (batch, utcnow())
            logging.debug(f"Batch {batch_id} cargado y cacheado")
        return batch
    except Exception as e:
        logging.error(f"Error obteniendo batch {batch_id}: {e}")
        return None
```

### 3.3 Worker Extrae Call Settings

**Archivo**: `app/call_worker.py` → Método `process()`

```python
def process(self, job: Dict[str, Any]):
    job_id = job["_id"]
    
    # 1. Obtener batch_id del job
    batch_id = job.get('batch_id')
    batch = None
    call_settings = {}
    
    if batch_id:
        print(f"[DEBUG] Obteniendo configuración del batch {batch_id}...")
        
        # 2. Obtener batch completo
        batch = self._get_batch(batch_id)
        
        if batch:
            # 3. Extraer call_settings
            call_settings = batch.get('call_settings', {})
            
            if call_settings:
                print(f"[DEBUG] ✅ Call settings encontrados: {call_settings}")
            else:
                print(f"[DEBUG] ⚠️ Batch sin call_settings, usando defaults")
        else:
            print(f"[WARNING] Batch {batch_id} no encontrado")
    else:
        print(f"[DEBUG] Job sin batch_id, usando configuración global")
    
    # 4. Continuar con validaciones y ejecución
    # ... (ver siguiente fase)
```

---

## ✅ Fase 4: Validaciones del Worker

### 4.1 Validación de Horarios Permitidos

```python
def process(self, job: Dict[str, Any]):
    # ... extracción de call_settings ...
    
    # 🕐 VALIDAR HORARIOS PERMITIDOS
    if call_settings:
        is_allowed, reason = self._is_allowed_time(call_settings)
        
        if not is_allowed:
            print(f"[INFO] 🚫 FUERA DE HORARIO PERMITIDO - {reason}")
            
            # Reprogramar para próximo horario permitido
            next_allowed_time = self._calculate_next_allowed_time(call_settings)
            
            self.job_store.coll.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": "pending",
                        "reserved_until": next_allowed_time,
                        "last_error": f"Fuera de horario: {reason}"
                    }
                }
            )
            
            print(f"[DEBUG] Job reprogramado para {next_allowed_time.isoformat()}")
            return  # No ejecutar ahora
```

#### Función `_is_allowed_time()`

```python
def _is_allowed_time(self, call_settings: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Verifica si el momento actual está dentro de los horarios permitidos
    
    Returns:
        (is_allowed, reason)
    """
    if not call_settings:
        return True, None
    
    # Obtener timezone del batch
    tz_str = call_settings.get("timezone", "America/Santiago")
    tz = pytz.timezone(tz_str)
    now = datetime.now(tz)
    
    # 1. Validar día de la semana
    days_of_week = call_settings.get("days_of_week")
    if days_of_week:
        current_day = now.isoweekday()  # 1=Lunes, 7=Domingo
        
        if current_day not in days_of_week:
            reason = f"Día {current_day} ({now.strftime('%A')}) no permitido"
            return False, reason
    
    # 2. Validar hora del día
    allowed_hours = call_settings.get("allowed_hours", {})
    if allowed_hours:
        start_time = allowed_hours.get("start", "00:00")
        end_time = allowed_hours.get("end", "23:59")
        
        start_hour, start_min = map(int, start_time.split(":"))
        end_hour, end_min = map(int, end_time.split(":"))
        
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        if not (start_minutes <= current_minutes <= end_minutes):
            reason = f"Hora {now.strftime('%H:%M')} fuera de rango {start_time}-{end_time}"
            return False, reason
    
    return True, None
```

### 4.2 Validación de Intentos Máximos

```python
def process(self, job: Dict[str, Any]):
    # ... validación de horarios ...
    
    # 🔄 VALIDAR MAX_ATTEMPTS DEL BATCH
    max_attempts = call_settings.get("max_attempts", MAX_TRIES)  # Default: 3
    current_tries = job.get("tries", 0)
    
    print(f"[DEBUG] Intentos: {current_tries}/{max_attempts}")
    
    if current_tries >= max_attempts:
        print(f"[ERROR] 🚫 MÁXIMO DE INTENTOS ALCANZADO")
        self.job_store.mark_failed(
            job_id, 
            f"Máximo de intentos alcanzado ({max_attempts})", 
            terminal=True
        )
        return  # No ejecutar
```

### 4.3 Validación de Balance (Créditos/Minutos)

```python
def process(self, job: Dict[str, Any]):
    # ... validaciones anteriores ...
    
    # 🔥 VALIDACIÓN DE BALANCE
    account_id = job.get('account_id')
    if account_id:
        account_doc = self.job_store.db.accounts.find_one({"account_id": account_id})
        
        if account_doc:
            plan_type = account_doc.get('plan_type')
            
            # Validar según tipo de plan
            if plan_type == "unlimited":
                has_balance = True
            elif plan_type == "minutes_based":
                minutes_remaining = account_doc.get('minutes_remaining', 0)
                has_balance = minutes_remaining > 0
            elif plan_type == "credit_based":
                credit_available = account_doc.get('credit_available', 0)
                cost_per_call = account_doc.get('cost_per_call_setup', 0.02)
                has_balance = credit_available >= cost_per_call
            
            if not has_balance:
                print(f"[ERROR] 🚫 SALDO INSUFICIENTE")
                self.job_store.mark_failed(job_id, "Saldo insuficiente", terminal=True)
                return
```

---

## 📞 Fase 5: Ejecución de la Llamada

### 5.1 Preparar Contexto para Retell AI

```python
def process(self, job: Dict[str, Any]):
    # ... todas las validaciones pasadas ...
    
    # Obtener teléfono
    phone = self._pick_next_phone(job)
    if not phone:
        self.job_store.mark_failed(job_id, "Sin teléfono válido", terminal=True)
        return
    
    # Construir contexto
    context = self._context_from_job(job)
    print(f"[DEBUG] Context enviado a Retell: {context}")
```

### 5.2 Iniciar Llamada con Call Settings

```python
def process(self, job: Dict[str, Any]):
    # ... preparación de contexto ...
    
    # Usar ring_timeout del batch si está disponible
    ring_timeout = call_settings.get("ring_timeout") if call_settings else None
    
    if ring_timeout:
        print(f"[DEBUG] Usando ring_timeout del batch: {ring_timeout}s")
    
    # ✅ LLAMAR A RETELL AI
    res = self.retell.start_call(
        to_number=phone,
        agent_id=RETELL_AGENT_ID,
        from_number=CALL_FROM_NUMBER,
        context=context,
        ring_timeout=ring_timeout  # ← Usa configuración del batch
    )
    
    print(f"[DEBUG] Resultado: success={res.success}, call_id={res.call_id}")
```

### 5.3 Cliente Retell AI

**Archivo**: `app/call_worker.py` → Clase `RetellClient`

```python
def start_call(
    self, 
    *, 
    to_number: str, 
    agent_id: str, 
    from_number: Optional[str], 
    context: Dict[str, Any], 
    ring_timeout: Optional[int] = None
) -> RetellResult:
    """
    Crea una llamada usando Retell v2
    
    Args:
        to_number: Número destino E.164 (ej: +56938773910)
        agent_id: ID del agente Retell
        from_number: Número origen
        context: Variables dinámicas para el agente
        ring_timeout: Tiempo máximo de timbre en segundos (del call_settings)
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
        body["ring_timeout"] = ring_timeout  # ← Configurado desde batch
    
    resp = requests.post(url, headers=self._headers(), data=json.dumps(body), timeout=30)
    
    if 200 <= resp.status_code < 300:
        data = resp.json()
        call_id = data.get("call_id")
        return RetellResult(success=True, call_id=call_id, raw=data)
    
    # Error
    return RetellResult(success=False, error=str(resp.json()))
```

### 5.4 Manejo de Reintentos

```python
def mark_failed(self, job_id, reason: str, terminal=False, call_settings: dict = None):
    """
    Marca un job como fallido y programa reintento
    
    Args:
        call_settings: Configuración del batch (para retry_delay_hours)
    """
    now = utcnow()
    
    # Obtener delay de reintento desde call_settings
    retry_delay_hours = 30  # Default
    
    if call_settings and "retry_delay_hours" in call_settings:
        retry_delay_hours = call_settings["retry_delay_hours"]
    
    next_try_at = now + dt.timedelta(hours=retry_delay_hours)
    
    update = {
        "$set": {
            "status": "failed" if not terminal else "done",
            "last_error": reason,
            "next_try_at": next_try_at,
            "updated_at": now
        }
    }
    
    self.coll.update_one({"_id": job_id}, update)
```

---

## 📊 Estructura de Datos

### Call Settings Schema

```typescript
interface CallSettings {
  // Duración y timing
  max_call_duration: number;      // Segundos (ej: 300 = 5 minutos)
  ring_timeout: number;           // Segundos de timbre (ej: 30)
  
  // Reintentos
  max_attempts: number;           // Número de intentos (ej: 3)
  retry_delay_hours: number;      // Horas entre reintentos (ej: 24)
  
  // Horarios permitidos
  allowed_hours: {
    start: string;                // Formato "HH:MM" (ej: "09:00")
    end: string;                  // Formato "HH:MM" (ej: "18:00")
  };
  
  days_of_week: number[];         // Array de días [1-7] (1=Lunes, 7=Domingo)
  timezone: string;               // Timezone IANA (ej: "America/Santiago")
  
  // Prioridad
  priority: number;               // Nivel de prioridad (1=normal, 2=alta, 0=baja)
}
```

### Ejemplo Completo

```json
{
  "max_call_duration": 300,
  "ring_timeout": 30,
  "max_attempts": 3,
  "retry_delay_hours": 24,
  "allowed_hours": {
    "start": "09:00",
    "end": "18:00"
  },
  "days_of_week": [1, 2, 3, 4, 5],
  "timezone": "America/Santiago",
  "priority": 1
}
```

### Valores por Defecto (si no se especifican)

```python
DEFAULT_CALL_SETTINGS = {
    "max_call_duration": 600,         # 10 minutos
    "ring_timeout": 60,               # 60 segundos
    "max_attempts": 3,                # 3 intentos
    "retry_delay_hours": 30,          # 30 horas
    "allowed_hours": None,            # Sin restricciones
    "days_of_week": None,             # Todos los días
    "timezone": "America/Santiago",   # Timezone Chile
    "priority": 1                     # Prioridad normal
}
```

---

## 📝 Logs de Ejemplo

### Creación del Batch

```
2025-10-26 14:27:43,645 | INFO | api | 📥 Recibiendo request para crear batch desde Excel
2025-10-26 14:27:43,647 | INFO | api |    - account_id: 'retail_express'
2025-10-26 14:27:43,647 | INFO | api |    - batch_name: 'Cobranza Octubre'
2025-10-26 14:27:43,647 | INFO | api |    - processing_type: 'basic'
2025-10-26 14:27:43,654 | INFO | api |    - call_settings_json: {"max_call_duration":300,"ring_timeout":30,...}
2025-10-26 14:27:44,586 | INFO | services.batch_creation_service | Batch batch-2025-10-26-142744-439872 creado
2025-10-26 14:27:44,853 | INFO | services.batch_creation_service | Creando 12 deudores para batch
2025-10-26 14:27:44,865 | INFO | services.batch_creation_service | Jobs creados: 12
```

### Worker Procesa Job

```
[DEBUG] [worker-1] Buscando jobs pendientes...
[DEBUG] [worker-1] Batches activos encontrados: 3
[DEBUG] [worker-1] ✅ Job encontrado: ObjectId('...')

[DEBUG] [ObjectId('...')] ========== PROCESANDO JOB ==========
[DEBUG] [ObjectId('...')] Obteniendo configuración del batch batch-2025-10-26-142744-439872...
[DEBUG] [ObjectId('...')] ✅ Call settings encontrados: {
  'max_call_duration': 300,
  'ring_timeout': 30,
  'max_attempts': 3,
  'retry_delay_hours': 24,
  'allowed_hours': {'start': '09:00', 'end': '18:00'},
  'days_of_week': [1, 2, 3, 4, 5],
  'timezone': 'America/Santiago',
  'priority': 1
}

[DEBUG] [ObjectId('...')] Validando horario permitido...
[DEBUG] [ObjectId('...')] Hora actual en America/Santiago: 14:30
[DEBUG] [ObjectId('...')] ✅ Dentro de horario permitido (09:00-18:00)
[DEBUG] [ObjectId('...')] ✅ Día permitido: 6 (Sábado) ❌ - No está en [1,2,3,4,5]
[INFO]  [ObjectId('...')] 🚫 FUERA DE HORARIO PERMITIDO - Día 6 no permitido
[DEBUG] [ObjectId('...')] Job reprogramado para 2025-10-27T09:00:00Z
```

### Worker Ejecuta Llamada

```
[DEBUG] [ObjectId('...')] ========== PROCESANDO JOB ==========
[DEBUG] [ObjectId('...')] ✅ Call settings encontrados
[DEBUG] [ObjectId('...')] ✅ Dentro de horario permitido
[DEBUG] [ObjectId('...')] Intentos: 1/3
[DEBUG] [ObjectId('...')] ✅ Balance suficiente - Plan: credit_based
[DEBUG] [ObjectId('...')] Context enviado a Retell: {
  'nombre': 'Juan Pérez',
  'empresa': 'Retail Express',
  'RUT': '135098329',
  'monto_total': '150000',
  'fecha_limite': '2025-11-25',
  'cuotas_adeudadas': '3'
}
[DEBUG] [ObjectId('...')] Usando ring_timeout del batch: 30s
[DEBUG] [ObjectId('...')] Iniciando llamada a Retell...
[DEBUG] [ObjectId('...')] Resultado Retell: success=True, call_id=abc123...
```

---

## 🔄 Diagrama de Flujo

### Flujo Completo con Decisiones

```
┌──────────────┐
│   Frontend   │
│   Crea Form  │
└──────┬───────┘
       │
       ↓ POST /api/v1/batches/excel/create
┌──────────────────┐
│      API         │
│ Parsea JSON      │
└──────┬───────────┘
       │
       ↓ create_batch_from_excel()
┌──────────────────┐
│  BatchCreation   │
│     Service      │
└──────┬───────────┘
       │
       ↓ insert_one()
┌──────────────────┐
│    MongoDB       │
│  batches: {      │
│    call_settings │
│  }               │
│  jobs: [...]     │
└──────┬───────────┘
       │
       ↓ Worker loop
┌──────────────────┐
│   JobStore       │
│  claim_one()     │ ← Solo jobs de batches activos
└──────┬───────────┘
       │
       ↓ Job reservado
┌──────────────────┐
│ CallOrchestrator │
│  process(job)    │
└──────┬───────────┘
       │
       ↓ _get_batch(batch_id)
┌──────────────────┐
│  Obtiene Batch   │ ← Con cache (5 min TTL)
│  + call_settings │
└──────┬───────────┘
       │
       ↓
   ┌───┴────┐
   │ ¿Tiene │
   │  call_ │  NO ─────→ Usar defaults
   │settings?│
   └───┬────┘
       │ SÍ
       ↓
┌──────────────────┐
│  Validaciones    │
│  1. ¿Horario OK? │────NO───→ Reprogramar
│  2. ¿Día OK?     │
└──────┬───────────┘
       │ SÍ
       ↓
┌──────────────────┐
│  3. ¿Intentos?   │────NO───→ Mark failed (terminal)
└──────┬───────────┘
       │ SÍ (<max_attempts)
       ↓
┌──────────────────┐
│  4. ¿Balance?    │────NO───→ Mark failed (terminal)
└──────┬───────────┘
       │ SÍ
       ↓
┌──────────────────┐
│  Retell AI       │
│  start_call()    │ ← ring_timeout del batch
│  + context       │
└──────┬───────────┘
       │
   ┌───┴────┐
   │Success?│
   └───┬────┘
       │
  ┌────┴────┐
  │         │
 SÍ        NO
  │         │
  ↓         ↓
Mark      Mark Failed
Done      + Reintento
          (retry_delay_hours)
```

---

## 🔑 Puntos Clave

### 1. Call Settings NO están en Jobs

❌ **Incorrecto**: Guardar call_settings en cada job
```json
{
  "_id": "...",
  "call_settings": {...}  // ❌ NO
}
```

✅ **Correcto**: Guardar call_settings en batch
```json
// Batch
{
  "batch_id": "batch-123",
  "call_settings": {...}  // ✅ SÍ
}

// Job
{
  "_id": "...",
  "batch_id": "batch-123"  // ✅ Referencia al batch
}
```

**Ventaja**: Cambiar call_settings una vez afecta todos los jobs del batch

### 2. Cache de Batches

El worker usa **cache con TTL de 5 minutos** para evitar consultas repetidas a MongoDB:

```python
self.batch_cache = {}        # {batch_id: (batch_data, timestamp)}
self.cache_ttl = 300         # 5 minutos
```

**Implicación**: Cambios en call_settings tardan hasta 5 minutos en aplicarse

### 3. Validación de Batches Activos

Solo se procesan jobs de batches con `is_active: true`:

```python
active_batches = self.batches_coll.find({"is_active": True})
```

**Para pausar un batch**: 
```bash
PATCH /api/v1/batches/{batch_id}
{
  "is_active": false
}
```

### 4. Defaults si No Hay Call Settings

Si un batch no tiene `call_settings`, el worker usa valores globales:

| Parámetro | Default |
|-----------|---------|
| `max_attempts` | `MAX_TRIES` (env var, default: 3) |
| `retry_delay_hours` | 30 horas |
| `ring_timeout` | No especificado (Retell default) |
| `allowed_hours` | Sin restricciones |
| `days_of_week` | Todos los días |

### 5. Timezone Awareness

Todas las validaciones de horario usan el `timezone` del batch:

```python
tz = pytz.timezone(call_settings.get("timezone", "America/Santiago"))
now = datetime.now(tz)  # Hora local del batch
```

---

## 🐛 Troubleshooting

### Problema: Jobs no se ejecutan

**Posibles causas**:

1. **Batch pausado** (`is_active: false`)
   ```bash
   # Verificar
   db.batches.find({batch_id: "batch-xxx"}, {is_active: 1})
   
   # Activar
   PATCH /api/v1/batches/batch-xxx {"is_active": true}
   ```

2. **Fuera de horario permitido**
   ```bash
   # Ver logs del worker
   [INFO] 🚫 FUERA DE HORARIO PERMITIDO - Día 6 no permitido
   
   # Job reprogramado con reserved_until
   db.jobs.find({_id: ObjectId("...")}, {reserved_until: 1, last_error: 1})
   ```

3. **Máximo de intentos alcanzado**
   ```bash
   # Verificar intentos
   db.jobs.find({_id: ObjectId("...")}, {attempts: 1, status: 1})
   ```

4. **Sin balance**
   ```bash
   [ERROR] 🚫 SALDO INSUFICIENTE
   
   # Verificar cuenta
   db.accounts.find({account_id: "retail_express"}, {credit_available: 1})
   ```

### Problema: Call settings no se aplican

**Verificar**:

1. **Call settings en batch**
   ```bash
   db.batches.find({batch_id: "batch-xxx"}, {call_settings: 1})
   ```

2. **Cache del worker** (esperar 5 minutos o reiniciar worker)
   ```bash
   # Reiniciar worker
   Ctrl+C
   python app/call_worker.py
   ```

3. **Logs del worker**
   ```bash
   [DEBUG] ✅ Call settings encontrados: {...}
   # vs
   [DEBUG] ⚠️ Batch sin call_settings, usando defaults
   ```

---

## 📚 Archivos Relacionados

| Archivo | Propósito |
|---------|-----------|
| `app/api.py` | Endpoint de creación, parseo de call_settings_json |
| `app/services/batch_creation_service.py` | Creación de batch con call_settings |
| `app/call_worker.py` | Worker que obtiene y aplica call_settings |
| `app/domain/models.py` | Modelo BatchModel con campo call_settings |
| `docs/CALL_SETTINGS_IMPLEMENTATION.md` | Documentación de implementación |
| `docs/FRONTEND_SUMMARY.md` | Guía para frontend |

---

## 📞 Resumen Ejecutivo para Desarrolladores

### Frontend
- Envía `call_settings_json` como **string JSON** en FormData
- No necesita validar exhaustivamente (backend valida)
- Puede mostrar preview de configuración

### Backend (API)
- Parsea `call_settings_json` de string a dict
- Guarda en batch (NO en jobs individuales)
- Valida estructura básica

### Backend (Worker)
- Lee `batch_id` del job
- Obtiene batch completo (con cache)
- Extrae `call_settings` del batch
- Aplica validaciones (horarios, intentos, balance)
- Ejecuta llamada con configuración del batch

### MongoDB
- **Batches**: Contienen `call_settings`
- **Jobs**: Solo referencian batch via `batch_id`
- Relación 1:N (un batch, muchos jobs)

---

**Documento creado**: 26 de Octubre, 2025  
**Última actualización**: 26 de Octubre, 2025  
**Versión**: 1.0.0
