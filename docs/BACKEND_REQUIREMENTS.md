# Requisitos de Backend - Frontend SpeechAI

## 📋 Resumen
Este documento detalla los endpoints y funcionalidades que el backend debe implementar para soportar las nuevas características del frontend.

## ✅ ESTADO: COMPLETADO (25 de Octubre, 2025)

**Todos los requisitos han sido implementados y probados exitosamente.**

---

## ✅ Implementación Completada

### ✅ Método `cancel_job` en JobService - IMPLEMENTADO

**Ubicación:** `app/services/job_service.py`

**Estado:** ✅ **COMPLETADO Y PROBADO**

**Implementación realizada:**
**Implementación realizada:**

```python
async def cancel_job(self, job_id: str) -> bool:
    """
    Cancela un job pendiente (API method)
    
    Args:
        job_id: ID del job a cancelar (puede ser ObjectId o job_id)
    
    Returns:
        True si se canceló, False si no se encontró o no se pudo cancelar
    """
    if not self.db_manager:
        raise ValueError("db_manager is required for API methods")
    
    # Intentar cancelar por _id primero
    try:
        result = await self.jobs_collection.update_one(
            {
                "_id": ObjectId(job_id),
                "status": {"$in": [
                    JobStatus.PENDING.value,
                    JobStatus.SCHEDULED.value,
                    JobStatus.FAILED.value
                ]}
            },
            {
                "$set": {
                    "status": JobStatus.CANCELLED.value,
                    "updated_at": datetime.utcnow(),
                    "cancellation_reason": "Cancelled by user"
                }
            }
        )
        
        if result.matched_count > 0:
            logger.info(f"Job {job_id} cancelled")
            return True
    except Exception as e:
        logger.warning(f"Could not cancel by _id: {e}")
    
    # Intentar por job_id si falla con _id
    result = await self.jobs_collection.update_one(
        {
            "job_id": job_id,
            "status": {"$in": [
                JobStatus.PENDING.value,
                JobStatus.SCHEDULED.value,
                JobStatus.FAILED.value
            ]}
        },
        {
            "$set": {
                "status": JobStatus.CANCELLED.value,
                "updated_at": datetime.utcnow(),
                "cancellation_reason": "Cancelled by user"
            }
        }
    )
    
    if result.matched_count > 0:
        logger.info(f"Job {job_id} cancelled")
        return True
    
    return False
```

**Características implementadas:**
- ✅ Acepta ambos formatos de ID (ObjectId y job_id personalizado)
- ✅ Solo cancela jobs en estados válidos (pending, scheduled, failed)
- ✅ Marca el job como `cancelled` (soft delete) - mantiene histórico
- ✅ Registra razón de cancelación: "Cancelled by user"
- ✅ Actualiza timestamp `updated_at`
- ✅ Logs apropiados

**Decisión de diseño:** Se implementó **soft delete** en lugar de eliminación física porque:
1. Permite mantener histórico de llamadas
2. Preserva estadísticas y reportes
3. Facilita auditoría y debugging
4. El estado `cancelled` ya está en el enum de JobStatus

---

## ✅ Endpoint DELETE /api/v1/jobs/{job_id} - FUNCIONANDO

**Ubicación:** `app/api.py`

**Estado:** ✅ **COMPLETADO Y PROBADO**

**Código implementado:**
```python
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
```

**Prueba exitosa:**
```bash
# Request
curl -X DELETE http://localhost:8000/api/v1/jobs/68fd0bc942cc4632daeb15f6

# Response
{"success":true,"message":"Job cancelled"}

# Verificación
curl http://localhost:8000/api/v1/jobs/68fd0bc942cc4632daeb15f6
# {"status":"cancelled", "cancellation_reason":"Cancelled by user", ...}
```

---

## ✅ Método `retry_job` - BONUS IMPLEMENTADO

**Ubicación:** `app/services/job_service.py`

**Estado:** ✅ **IMPLEMENTADO** (bonus adicional)

**Endpoint:** `PUT /api/v1/jobs/{job_id}/retry`

**Funcionalidad:**
- Marca jobs fallidos para reintento
- Los mueve de `failed` a `pending`
- Limpia errores previos
- Resetea worker_id y reserved_until

---

## ✅ Endpoints Adicionales Mejorados

### 1. GET /api/v1/jobs/{job_id}
- ✅ Acepta ObjectId y job_id personalizado
- ✅ Manejo de errores mejorado

### 2. GET /api/v1/batches/{batch_id}/jobs
- ✅ Acepta ObjectId y batch_id personalizado
- ✅ Resuelve correctamente el batch_id interno

### 3. PATCH /api/v1/batches/{batch_id}
- ✅ Acepta ObjectId y batch_id personalizado
- ✅ Pausar/reanudar funcionando
- ✅ Actualizar múltiples campos

---

## 🎯 Checklist de Implementación

### Paso 1: Implementar `cancel_job` en JobService ✅
- [x] Implementar el método `cancel_job` en `JobService`
- [x] Usar soft delete (marcar como `cancelled`)
- [x] Agregar logs apropiados
- [x] Agregar validaciones (job existe, estados válidos)
- [x] Soportar ambos formatos de ID (ObjectId y job_id personalizado)

### Paso 2: Verificar endpoint DELETE ✅
- [x] Confirmar que el endpoint en `app/api.py` funciona correctamente
- [x] Verificar que retorna el formato correcto
- [x] Documentado en OpenAPI/Swagger
- [x] Probado con curl

### Paso 3: Testing ✅
- [x] Prueba de endpoint DELETE individual
- [x] Prueba de múltiples DELETEs concurrentes (bulk delete)
- [x] Verificar que el estado cambia a `cancelled`
- [x] Verificar razón de cancelación guardada

### Paso 4: Consideraciones de Negocio ✅
- [x] ✅ Se puede eliminar un job `pending`, `scheduled`, `failed`
- [x] ❌ NO se puede cancelar job `in_progress` o `completed`
- [x] ✅ Soft delete preserva métricas/reportes
- [x] ✅ Estado `cancelled` agregado al enum JobStatus
- [x] ✅ Timestamps actualizados correctamente

---

## 🧪 Testing desde el Frontend

### 1. Prueba Individual ✅
```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/68fd0bc942cc4632daeb15f6
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Job cancelled"
}
```

### 2. Prueba desde el Frontend
1. ✅ Ir a http://localhost:3002/llamadas
2. ✅ Hacer clic en un checkbox de cualquier job
3. ✅ Hacer clic en el botón "Eliminar (1)"
4. ✅ Confirmar en el diálogo
5. ✅ Verificar mensaje de éxito

### 3. Prueba Bulk Delete
1. ✅ Seleccionar varios jobs con checkboxes
2. ✅ Hacer clic en "Eliminar (X)"
3. ✅ Confirmar
4. ✅ Debe mostrar: "Se eliminaron X tarea(s) exitosamente"

**Comportamiento del Frontend:**
```typescript
const deletePromises = Array.from(selectedJobIds).map(jobId =>
  axios.delete(`/api/v1/jobs/${jobId}`)  // ✅ AHORA FUNCIONA
);

const results = await Promise.allSettled(deletePromises);
// ✅ Todos los requests se completarán exitosamente
```

---

## 📊 Modelo de Datos Implementado

### Job Model - Estados
```python
class JobStatus(Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DONE = "done"
    FAILED = "failed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"  # ✅ NUEVO - Para jobs cancelados
```

### Job cancelado - Estructura
```json
{
  "_id": "68fd0bc942cc4632daeb15f6",
  "job_id": "job_retail_e_20251025_174129_b96907c5",
  "status": "cancelled",
  "cancellation_reason": "Cancelled by user",
  "updated_at": "2025-10-25T18:34:10.585000",
  ...
}
```

---

## 📝 Notas Importantes para el Frontend

### 1. Soft Delete vs Hard Delete
**Implementación actual:** Soft Delete (marcar como `cancelled`)

**Ventajas:**
- ✅ Preserva histórico de llamadas
- ✅ Mantiene estadísticas consistentes
- ✅ Permite auditoría
- ✅ Recuperable si es necesario

**Para el frontend:**
- Los jobs cancelados NO aparecen en listados normales
- Pueden verse con filtro `status=cancelled` si es necesario
- El contador del batch se mantiene correcto

### 2. Estados que NO se pueden cancelar
- `in_progress` - Llamada en curso
- `completed` / `done` - Ya terminado
- `cancelled` - Ya está cancelado

**Frontend debe deshabilitar botón de eliminar** para estos estados.

### 3. IDs Flexibles
Todos los endpoints aceptan ambos formatos:
- ObjectId MongoDB: `68fd0bc98ac7d47a518bc016`
- ID personalizado: `job_retail_e_20251025_174129_b96907c5`

### 4. Bulk Delete - Performance
El backend soporta requests concurrentes sin problemas:
```typescript
// ✅ Esto es seguro y eficiente
const deletePromises = selectedJobIds.map(id =>
  axios.delete(`/api/v1/jobs/${id}`)
);
await Promise.allSettled(deletePromises);
```

---

## 🔗 Documentación Relacionada

1. **API_FRONTEND_REFERENCE.md** - Referencia completa de todos los endpoints
2. **BATCH_PAUSE_IMPLEMENTATION.md** - Detalles de pausar/reanudar batches
3. **Swagger UI:** http://localhost:8000/docs

---

## ✅ Resumen de Cambios Implementados

| Componente | Archivo | Estado | Cambios |
|-----------|---------|--------|---------|
| JobService | `app/services/job_service.py` | ✅ | `cancel_job()`, `retry_job()`, `get_job_by_id()` mejorado |
| API Endpoint | `app/api.py` | ✅ | DELETE /jobs/{id} funcionando |
| JobStatus Enum | `app/domain/enums.py` | ✅ | Agregado `CANCELLED` |
| Batch Endpoints | `app/api.py` | ✅ | PATCH funcionando, soporte dual ID |
| BatchService | `app/services/batch_service.py` | ✅ | `_get_batch_filter()`, `update_batch()` |

---

## 🚀 Estado Final

### Backend: ✅ LISTO PARA PRODUCCIÓN

**Todos los requisitos del frontend han sido implementados:**
- ✅ DELETE /api/v1/jobs/{job_id}
- ✅ cancel_job() en JobService  
- ✅ retry_job() en JobService
- ✅ Soporte para ObjectId y IDs personalizados
- ✅ Soft delete con estado `cancelled`
- ✅ Bulk delete soportado
- ✅ Logs y validaciones
- ✅ Probado exitosamente

**El frontend puede comenzar a usar estos endpoints inmediatamente.**

---

**Fecha de actualización:** 25 de Octubre, 2025  
**Versión:** 2.0 (Completado)  
**Estado:** ✅ TODOS LOS REQUISITOS IMPLEMENTADOS Y PROBADOS
