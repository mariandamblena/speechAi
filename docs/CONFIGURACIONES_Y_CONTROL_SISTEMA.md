# 🔧 Configuraciones y Control del Sistema SpeechAI

## 📋 Índice
1. [Configuraciones del Sistema](#configuraciones-del-sistema)
2. [Flujo de Reintentos y Estados](#flujo-de-reintentos-y-estados)
3. [Control de Workers y Batches](#control-de-workers-y-batches)
4. [Comandos de Administración](#comandos-de-administración)

---

## 🔧 Configuraciones del Sistema

### Variables de Entorno

El sistema utiliza un patrón de configuración centralizada definido en `app/config/settings.py`:

```bash
# 🗄️ Base de Datos MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=speechai_db
MONGO_COLL_JOBS=jobs
MONGO_COLL_RESULTS=call_results
MONGO_COLL_LOGS=call_logs
MONGO_COLL_ACCOUNTS=accounts
MONGO_COLL_BATCHES=batches
MONGO_MAX_POOL_SIZE=50

# 🤖 Retell AI
RETELL_API_KEY=your_api_key_here
RETELL_BASE_URL=https://api.retellai.com
RETELL_AGENT_ID=your_agent_id
RETELL_FROM_NUMBER=your_phone_number
RETELL_TIMEOUT_SECONDS=30

# 👷 Workers
WORKER_COUNT=6                    # Número de workers paralelos
LEASE_SECONDS=120                 # Tiempo de reserva de job (2 min)
MAX_ATTEMPTS=3                    # Máximo intentos por job
RETRY_DELAY_MINUTES=30            # Delay entre reintentos (30 min)

# 📞 Llamadas
CALL_POLLING_INTERVAL=10          # Intervalo de consulta (10 seg)
POLL_TIMEOUT_SECONDS=300          # Timeout máximo de llamada (5 min)
CALL_MAX_DURATION_MINUTES=10      # Duración máxima de llamada
NO_ANSWER_RETRY_MINUTES=60        # Delay para "no answer" (1 hora)

# 📊 Logging
LOG_LEVEL=INFO
```

### Configuración Estructurada

```python
from config.settings import get_settings

# Obtener configuración validada
config = get_settings()

# Acceder a configuraciones específicas
print(f"Workers: {config.worker.count}")
print(f"Max attempts: {config.worker.max_attempts}")
print(f"Retry delay: {config.worker.retry_delay_minutes} min")
```

---

## 🔄 Flujo de Reintentos y Estados

### Estados de Jobs

Los jobs pasan por los siguientes estados:

```
🆕 pending → 🔄 in_progress → ✅ done/completed
    ↓              ↓              ↑
    ❌ failed  ←  ❌ error      ❌ failed
    ↓ (si attempts < 3)
    ⏱️ pending (retry programado)
```

### Estados Detallados

| Estado | Descripción | Siguiente Acción |
|--------|-------------|------------------|
| `pending` | Job listo para procesamiento | Worker lo toma |
| `in_progress` | Worker procesando | Esperar resultado |
| `done/completed` | Llamada exitosa | Fin del proceso |
| `failed` | Falló definitivamente | No más reintentos |
| `suspended` | Sin créditos/pausado | Esperar reactivación |

### Lógica de Reintentos

```python
# Condiciones para reintento automático:
if job.attempts < MAX_ATTEMPTS:  # (3)
    if call_status in ["no_answer", "busy", "failed"]:
        # Programar reintento con delay
        next_retry = now + timedelta(minutes=RETRY_DELAY_MINUTES)
        job.status = "pending"
        job.reserved_until = next_retry
        job.attempts += 1
```

### Rotación de Teléfonos

Cuando falla una llamada, el sistema automáticamente intenta con el siguiente número:

```python
# Si hay múltiples teléfonos
contact = {
    "phones": ["+549111234567", "+549351234567"],
    "next_phone_index": 0
}

# Al fallar, avanza al siguiente
if job.contact.next_phone_index < len(job.contact.phones) - 1:
    job.contact.next_phone_index += 1
    job.status = "pending"  # Reintenta inmediatamente
```

### Delays Configurables

| Escenario | Delay | Variable |
|-----------|-------|----------|
| **Reintento general** | 30 min | `RETRY_DELAY_MINUTES` |
| **No answer específico** | 60 min | `NO_ANSWER_RETRY_MINUTES` |
| **Cambio de teléfono** | Inmediato | No aplica |
| **Error temporal** | 1-2 min | Jitter aleatorio |

---

## 🎛️ Control de Workers y Batches

### ✅ **SÍ se puede pausar/controlar:**

#### 1. **Pausar/Reanudar Batches**

```python
# Via API
POST /api/batches/{batch_id}/pause
POST /api/batches/{batch_id}/resume

# Via servicio
from services.batch_service import BatchService
batch_service = BatchService(db_manager)

# Pausar batch
await batch_service.pause_batch("batch-20251003-abc123")
# Jobs del batch no serán procesados

# Reanudar batch  
await batch_service.resume_batch("batch-20251003-abc123")
# Jobs vuelven a ser elegibles
```

#### 2. **Detener Workers Gracefully**

```bash
# Enviar señal SIGTERM o SIGINT (Ctrl+C)
pkill -TERM -f call_worker.py

# O usando el PID
kill -TERM <worker_pid>
```

El worker detecta la señal y:
```python
def _graceful_stop(signum, frame):
    global RUNNING
    RUNNING = False
    logging.info("Recibida señal de stop. Cerrando...")

# Los workers terminan su job actual y no toman nuevos
while RUNNING:  # Se vuelve False
    job = store.claim_one(worker_id=name)
    # ...
```

#### 3. **Suspender Jobs Individuales**

```python
# Cambiar estado a suspended
job_service.suspend_job(job_id, reason="Sin créditos")

# Jobs suspended no son elegibles para workers
query = {
    "status": "pending",  # No incluye "suspended"
    "$or": [
        {"reserved_until": {"$exists": False}},
        {"reserved_until": {"$lt": datetime.utcnow()}}
    ]
}
```

### ❌ **NO se puede pausar directamente:**

- **Workers individuales**: No hay API para pausar un worker específico sin detenerlo
- **Jobs en progreso**: Una vez que un worker toma un job, debe completarlo
- **Llamadas activas**: No se pueden cancelar llamadas en curso en Retell

---

## 🛠️ Comandos de Administración

### Verificar Estado del Sistema

```bash
# Ver estadísticas de jobs
python app/scripts/generate_reports.py --format terminal

# Verificar workers activos
ps aux | grep call_worker.py

# Ver logs en tiempo real
tail -f logs/speechai.log
```

### Gestión de Workers

```bash
# Iniciar workers
python app/call_worker.py

# Iniciar con configuración específica
WORKER_COUNT=10 MAX_ATTEMPTS=5 python app/call_worker.py

# Detener workers gracefully
pkill -TERM -f call_worker.py

# Forzar detención (último recurso)
pkill -KILL -f call_worker.py
```

### Gestión de Batches

```bash
# Crear batch via API
curl -X POST "http://localhost:8000/api/batches" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "acc_123",
    "name": "Cobranza Octubre",
    "description": "Batch mensual de cobranza"
  }'

# Pausar batch
curl -X POST "http://localhost:8000/api/batches/batch-20251003-abc123/pause"

# Reanudar batch
curl -X POST "http://localhost:8000/api/batches/batch-20251003-abc123/resume"
```

### Operaciones de Emergencia

```bash
# Pausar TODOS los batches activos
python -c "
from services.batch_service import BatchService
from infrastructure.database_manager import DatabaseManager
import asyncio

async def pause_all():
    db = DatabaseManager()
    batch_service = BatchService(db)
    
    # Pausar todos los batches activos
    batches = await batch_service.batches_collection.find({'is_active': True}).to_list(None)
    for batch in batches:
        await batch_service.pause_batch(batch['batch_id'])
        print(f'Pausado: {batch['batch_id']}')

asyncio.run(pause_all())
"

# Reiniciar jobs fallidos
python app/scripts/reset_jobs.py --status failed --max-age-hours 24

# Liberar jobs colgados (reservados pero sin procesar)
python -c "
from pymongo import MongoClient
from datetime import datetime, timedelta
import os

client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017'))
db = client[os.getenv('MONGO_DB', 'speechai_db')]
jobs = db[os.getenv('MONGO_COLL_JOBS', 'jobs')]

# Liberar jobs reservados hace más de 5 minutos
cutoff = datetime.utcnow() - timedelta(minutes=5)
result = jobs.update_many(
    {'status': 'in_progress', 'reserved_until': {'$lt': cutoff}},
    {'$set': {'status': 'pending'}, '$unset': {'reserved_until': 1}}
)
print(f'Liberados {result.modified_count} jobs colgados')
"
```

---

## 📊 Monitoreo y Diagnóstico

### Métricas Clave

```python
# Estadísticas en tiempo real
from app.utils.jobs_report_generator import JobsReportGenerator
generator = JobsReportGenerator()

# Estado actual del sistema
stats = generator.get_general_stats()
print(f"Jobs pending: {stats['pending']}")
print(f"Jobs in progress: {stats['in_progress']}")
print(f"Workers efectivos: {stats['pending'] > 0 and stats['in_progress'] < WORKER_COUNT}")
```

### Alertas Automáticas

El sistema debería generar alertas cuando:
- Jobs pendientes > 100 y workers disponibles
- Jobs colgados en `in_progress` > 5 minutos
- Tasa de éxito < 20%
- Batches pausados inesperadamente

---

## 🚀 Mejores Prácticas

### Configuración de Producción

```bash
# Para alta carga
WORKER_COUNT=20
LEASE_SECONDS=300
RETRY_DELAY_MINUTES=60
CALL_POLLING_INTERVAL=5

# Para desarrollo
WORKER_COUNT=3
LEASE_SECONDS=120
RETRY_DELAY_MINUTES=5
CALL_POLLING_INTERVAL=10
```

### Estrategias de Escalado

1. **Horizontal**: Aumentar `WORKER_COUNT`
2. **Temporal**: Ajustar `RETRY_DELAY_MINUTES` según carga
3. **Batch-wise**: Pausar batches de baja prioridad en horas pico
4. **Phone rotation**: Configurar múltiples números por contacto

### Resolución de Problemas Comunes

| Problema | Diagnóstico | Solución |
|----------|-------------|----------|
| Jobs no se procesan | Workers parados | Reiniciar `call_worker.py` |
| Muchos reintentos | Config mal ajustada | Revisar `MAX_ATTEMPTS` |
| Llamadas colgadas | Timeout muy alto | Ajustar `POLL_TIMEOUT_SECONDS` |
| Alta latencia | Pocos workers | Aumentar `WORKER_COUNT` |

---

**✅ Resumen:** El sistema SpeechAI permite control granular de batches (pausar/reanudar), gestión de workers (start/stop graceful), y configuración flexible de reintentos y delays. Está diseñado para ser resiliente y escalable en producción.