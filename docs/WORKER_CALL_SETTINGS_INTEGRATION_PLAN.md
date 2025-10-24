# 🔧 Plan de Integración: call_settings en Workers

## 📋 Análisis del Estado Actual

### Frontend Expectations (según FRONTEND_COMPLETE_GUIDE.md)

El frontend espera que `call_settings` controle:

```json
{
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
    "timezone": "America/Santiago"
  }
}
```

### Worker Actual (call_worker.py)

**Variables de entorno actuales**:
```python
LEASE_SECONDS = 120
MAX_TRIES = 3
RETRY_DELAY_MINUTES = 30
NO_ANSWER_RETRY_MINUTES = 60
CALL_MAX_DURATION_MINUTES = 10
CALL_POLLING_INTERVAL = 15
```

**Problema**: Estas configuraciones son **globales** para todos los batches. Necesitamos que sean **por batch**.

---

## 🎯 Cambios Necesarios

### 1. Obtener call_settings del Batch al procesar Job

**Ubicación**: `CallOrchestrator.process()`

**Cambio**:
```python
def process(self, job: Dict[str, Any]):
    # 1. Obtener batch asociado
    batch_id = job.get("batch_id")
    batch = self._get_batch(batch_id) if batch_id else None
    
    # 2. Extraer call_settings del batch
    call_settings = batch.get("call_settings", {}) if batch else {}
    
    # 3. Validar horarios permitidos
    if not self._is_allowed_time(call_settings):
        self.job_store.reschedule_job(job["_id"], reason="Fuera de horario permitido")
        return
    
    # 4. Continuar con lógica normal...
```

---

### 2. Validar Horarios Permitidos

**Nueva función**: `_is_allowed_time(call_settings)`

```python
def _is_allowed_time(self, call_settings: Dict[str, Any]) -> bool:
    """
    Verifica si el momento actual está dentro de los horarios permitidos
    
    Args:
        call_settings: Configuración del batch con allowed_hours, days_of_week, timezone
    
    Returns:
        True si está permitido llamar ahora, False si no
    """
    if not call_settings:
        return True  # Sin restricciones
    
    # Obtener timezone del batch
    tz_str = call_settings.get("timezone", "America/Santiago")
    
    try:
        import pytz
        tz = pytz.timezone(tz_str)
    except:
        tz = pytz.timezone("America/Santiago")  # Fallback
    
    # Obtener hora actual en la timezone del batch
    from datetime import datetime
    now = datetime.now(tz)
    
    # 1. Validar día de la semana
    days_of_week = call_settings.get("days_of_week", [1, 2, 3, 4, 5, 6, 7])
    current_day = now.isoweekday()  # 1=Lunes, 7=Domingo
    
    if current_day not in days_of_week:
        logging.info(f"Fuera de horario: Día {current_day} no está en días permitidos {days_of_week}")
        return False
    
    # 2. Validar hora del día
    allowed_hours = call_settings.get("allowed_hours", {})
    if not allowed_hours:
        return True  # Sin restricciones de hora
    
    start_time = allowed_hours.get("start", "00:00")
    end_time = allowed_hours.get("end", "23:59")
    
    # Parsear horas (formato HH:MM)
    start_hour, start_min = map(int, start_time.split(":"))
    end_hour, end_min = map(int, end_time.split(":"))
    
    current_minutes = now.hour * 60 + now.minute
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    
    if not (start_minutes <= current_minutes <= end_minutes):
        logging.info(
            f"Fuera de horario: {now.strftime('%H:%M')} no está entre "
            f"{start_time} y {end_time}"
        )
        return False
    
    return True
```

---

### 3. Usar max_attempts del Batch

**Ubicación**: `JobStore.claim_one()` y lógica de reintentos

**Cambio actual**:
```python
MAX_TRIES = int(os.getenv("MAX_TRIES", "3"))  # Global
```

**Cambio necesario**:
```python
# En CallOrchestrator.process()
max_attempts = call_settings.get("max_attempts", 3)

if job.get("tries", 0) >= max_attempts:
    self.job_store.mark_failed(job["_id"], "Max attempts reached", terminal=True)
    return
```

---

### 4. Usar retry_delay_hours del Batch

**Ubicación**: `JobStore.mark_failed()`

**Cambio actual**:
```python
RETRY_DELAY_MINUTES = int(os.getenv("RETRY_DELAY_MINUTES", "30"))  # Global
```

**Cambio necesario**:
```python
def mark_failed(self, job_id, error_msg: str, terminal: bool = False, 
                call_settings: Optional[Dict] = None):
    """
    Marca job como failed y programa reintento si no es terminal
    """
    if terminal:
        # Fallo permanente, no reintentar
        self.coll.update_one(
            {"_id": job_id},
            {"$set": {
                "status": "failed",
                "last_error": error_msg,
                "updated_at": utcnow()
            }}
        )
    else:
        # Fallo temporal, programar reintento
        retry_delay_hours = 24  # Default
        
        if call_settings:
            retry_delay_hours = call_settings.get("retry_delay_hours", 24)
        
        retry_at = utcnow() + dt.timedelta(hours=retry_delay_hours)
        
        self.coll.update_one(
            {"_id": job_id},
            {"$set": {
                "status": "pending",
                "reserved_until": retry_at,
                "last_error": error_msg,
                "updated_at": utcnow()
            },
            "$inc": {"tries": 1}}
        )
```

---

### 5. Usar max_call_duration del Batch

**Ubicación**: `CallOrchestrator._wait_call_result()`

**Cambio actual**:
```python
CALL_MAX_DURATION_MINUTES = int(os.getenv("CALL_MAX_DURATION_MINUTES", "10"))
```

**Cambio necesario**:
```python
def _wait_call_result(self, call_id: str, job: Dict, call_settings: Dict):
    """Espera el resultado de la llamada con timeout del batch"""
    
    # Obtener max_duration del call_settings o usar default
    max_duration_seconds = call_settings.get("max_call_duration", 600)  # Default 10 min
    max_iterations = max_duration_seconds // CALL_POLLING_INTERVAL
    
    for attempt in range(max_iterations):
        time.sleep(CALL_POLLING_INTERVAL)
        
        call_data = self.retell.get_call_data(call_id)
        
        if call_data and call_data.get("call_status") in ["ended", "error"]:
            return call_data
    
    # Timeout alcanzado
    logging.warning(f"Call {call_id} timeout después de {max_duration_seconds}s")
    return None
```

---

### 6. Usar ring_timeout del Batch

**Ubicación**: `CallOrchestrator._create_call()`

**Cambio**:
```python
def _create_call(self, to_number: str, job: Dict, call_settings: Dict) -> Optional[str]:
    """Crea llamada en Retell con timeout del batch"""
    
    ring_timeout = call_settings.get("ring_timeout", 30)  # Default 30s
    
    payload = {
        "agent_id": RETELL_AGENT_ID,
        "to_number": to_number,
        "from_number": CALL_FROM_NUMBER,
        "override_agent_id": RETELL_AGENT_ID,
        "retell_llm_dynamic_variables": self._context_from_job(job),
        "ring_timeout": ring_timeout  # ← Usar del batch
    }
    
    # ... resto del código
```

---

## 🔄 Flujo Completo con call_settings

```
1. Worker obtiene job de la cola
   ↓
2. Worker obtiene batch asociado al job
   ↓
3. Worker extrae call_settings del batch
   ↓
4. Worker valida horarios permitidos
   ├─ Si fuera de horario → Reprogramar job para más tarde
   └─ Si dentro de horario → Continuar
   ↓
5. Worker valida max_attempts
   ├─ Si alcanzó máximo → Marcar como failed terminal
   └─ Si puede reintentar → Continuar
   ↓
6. Worker crea llamada con ring_timeout del batch
   ↓
7. Worker espera resultado con max_call_duration del batch
   ↓
8. Si falla:
   ├─ Calcular próximo reintento con retry_delay_hours
   └─ Reprogramar job
```

---

## 📊 Cambios por Archivo

### 1. `app/call_worker.py`

**Nuevas funciones**:
- `CallOrchestrator._get_batch(batch_id)` - Obtener batch de MongoDB
- `CallOrchestrator._is_allowed_time(call_settings)` - Validar horarios
- `CallOrchestrator._get_retry_delay(call_settings, reason)` - Calcular delay

**Funciones modificadas**:
- `CallOrchestrator.process(job)` - Obtener y usar call_settings
- `CallOrchestrator._create_call()` - Pasar ring_timeout
- `CallOrchestrator._wait_call_result()` - Usar max_call_duration
- `JobStore.mark_failed()` - Usar retry_delay_hours
- `JobStore.claim_one()` - Considerar reserved_until por horarios

---

## 🧪 Tests Necesarios

### Unit Tests

```python
# test_call_settings_integration.py

def test_is_allowed_time_within_hours():
    """Test que valida correctamente horarios permitidos"""
    call_settings = {
        "allowed_hours": {"start": "09:00", "end": "18:00"},
        "days_of_week": [1, 2, 3, 4, 5],
        "timezone": "America/Santiago"
    }
    # Mock datetime.now() para simular diferentes horas
    # Verificar True si está dentro, False si está fuera

def test_is_allowed_time_weekend():
    """Test que rechaza llamadas en fin de semana"""
    call_settings = {
        "days_of_week": [1, 2, 3, 4, 5]  # Solo lunes a viernes
    }
    # Mock datetime.now() para simular sábado
    # Verificar que retorna False

def test_max_attempts_respected():
    """Test que respeta max_attempts del batch"""
    call_settings = {"max_attempts": 2}
    job = {"tries": 2}
    # Verificar que se marca como failed terminal

def test_retry_delay_calculation():
    """Test que calcula correctamente el delay de reintento"""
    call_settings = {"retry_delay_hours": 48}
    # Verificar que reserved_until = now + 48 horas
```

### Integration Tests

```python
# test_worker_integration.py

def test_worker_respects_batch_hours():
    """Test E2E que worker respeta horarios del batch"""
    # 1. Crear batch con horarios 09:00-18:00
    # 2. Crear job asociado
    # 3. Mock hora actual a 20:00
    # 4. Worker debe reprogramar el job, no ejecutarlo

def test_worker_uses_batch_retry_settings():
    """Test E2E que worker usa retry settings del batch"""
    # 1. Crear batch con retry_delay_hours=12
    # 2. Crear job que fallará
    # 3. Verificar que reserved_until = now + 12 horas
```

---

## ⚠️ Consideraciones Importantes

### 1. Retrocompatibilidad

**Problema**: Batches existentes NO tienen `call_settings`

**Solución**:
```python
call_settings = batch.get("call_settings") or {}

# Siempre usar valores default si no existe
max_attempts = call_settings.get("max_attempts", 3)
retry_delay = call_settings.get("retry_delay_hours", 24)
```

### 2. Performance

**Problema**: Obtener batch por cada job puede ser costoso

**Solución**: Cache del batch
```python
# En CallOrchestrator
self.batch_cache = {}  # {batch_id: batch_data}
self.cache_ttl = 300  # 5 minutos

def _get_batch_cached(self, batch_id):
    if batch_id in self.batch_cache:
        cached_batch, cached_at = self.batch_cache[batch_id]
        if (utcnow() - cached_at).total_seconds() < self.cache_ttl:
            return cached_batch
    
    # Cache miss o expirado, obtener de MongoDB
    batch = self.batch_coll.find_one({"batch_id": batch_id})
    self.batch_cache[batch_id] = (batch, utcnow())
    return batch
```

### 3. Timezone Handling

**Problema**: Comparar horas en diferentes timezones

**Solución**: Usar `pytz` y convertir todo a la timezone del batch
```python
import pytz
from datetime import datetime

tz = pytz.timezone(call_settings.get("timezone", "America/Santiago"))
now_in_batch_tz = datetime.now(tz)
```

### 4. Jobs Reprogramados

**Problema**: Jobs fuera de horario deben esperar hasta el próximo horario permitido

**Solución**: Calcular `reserved_until` inteligentemente
```python
def _calculate_next_allowed_time(self, call_settings):
    """Calcula la próxima hora permitida para llamar"""
    tz = pytz.timezone(call_settings.get("timezone", "America/Santiago"))
    now = datetime.now(tz)
    
    allowed_hours = call_settings.get("allowed_hours", {})
    start_time = allowed_hours.get("start", "09:00")
    
    # Si estamos fuera de horario hoy, programar para mañana a la hora de inicio
    start_hour, start_min = map(int, start_time.split(":"))
    
    next_allowed = now.replace(hour=start_hour, minute=start_min, second=0)
    
    if next_allowed <= now:
        # Ya pasó la hora de inicio hoy, programar para mañana
        next_allowed += dt.timedelta(days=1)
    
    return next_allowed
```

---

## 📝 Checklist de Implementación

### Fase 1: Preparación (30 min)
- [ ] Crear rama `feature/call-settings-worker-integration`
- [ ] Backup de `call_worker.py`
- [ ] Instalar `pytz` si no está: `pip install pytz`

### Fase 2: Implementación Core (2 horas)
- [ ] Agregar `_get_batch()` method
- [ ] Agregar `_is_allowed_time()` method
- [ ] Agregar `_calculate_next_allowed_time()` method
- [ ] Modificar `process()` para obtener call_settings
- [ ] Modificar `mark_failed()` para usar retry_delay_hours
- [ ] Modificar `_create_call()` para usar ring_timeout
- [ ] Modificar `_wait_call_result()` para usar max_call_duration

### Fase 3: Cache y Optimizaciones (1 hora)
- [ ] Implementar cache de batches
- [ ] Agregar logs informativos
- [ ] Manejar errores de timezone

### Fase 4: Testing (2 horas)
- [ ] Unit tests para `_is_allowed_time()`
- [ ] Unit tests para retry delay calculation
- [ ] Integration test con batch real
- [ ] Test de performance con cache

### Fase 5: Validación (1 hora)
- [ ] Test manual con batch con horarios 09:00-18:00
- [ ] Test manual con batch sin call_settings (retrocompatibilidad)
- [ ] Verificar logs en MongoDB
- [ ] Verificar jobs reprogramados correctamente

---

## 🚀 Entregables

1. **Código modificado**: `app/call_worker.py` con integración completa
2. **Tests**: `tests/test_call_settings_worker.py` con casos de prueba
3. **Documentación**: Este documento + README actualizado
4. **Validation Report**: Reporte de pruebas exitosas

---

**Autor**: GitHub Copilot  
**Fecha**: 2025-01-15  
**Estimación**: 6-7 horas de trabajo  
**Prioridad**: 🔴 CRÍTICA
