# Implementación de Pausa de Batches

## Resumen de Cambios

Se ha implementado la funcionalidad completa para pausar y reanudar batches de llamadas, asegurando que los jobs de batches pausados o eliminados no se ejecuten.

## Cambios Realizados

### 1. Enumeraciones (`domain/enums.py`)
- ✅ Agregado estado `SCHEDULED` a `JobStatus` para jobs programados
- ✅ Agregado estado `CANCELLED` a `JobStatus` para jobs cancelados cuando su batch es pausado o eliminado

### 2. Modelos (`domain/models.py`)
- ✅ Agregado campo `updated_at` a `BatchModel` para rastrear última actualización
- ✅ Actualizado método `to_dict()` para incluir `updated_at`
- ✅ Actualizado método `from_dict()` para cargar `updated_at`

### 3. API Endpoints (`api.py`)
- ✅ **NUEVO** endpoint `PATCH /api/v1/batches/{batch_id}` para actualizar batches
  - Permite cambiar `is_active` (pausar/reanudar)
  - Permite actualizar `name`, `description`, `priority`
  - Retorna información detallada de qué campos se actualizaron

### 4. Servicio de Batches (`services/batch_service.py`)
- ✅ Actualizado `pause_batch()` para incluir `updated_at`
- ✅ Actualizado `resume_batch()` para incluir `updated_at`
- ✅ **NUEVO** método `update_batch()` para actualizaciones generales
- ✅ Actualizado `delete_batch()` para cancelar jobs pendientes en lugar de solo desvinculados
  - Cancela jobs en estado: `PENDING`, `SCHEDULED`, `IN_PROGRESS`
  - Marca con estado `CANCELLED` y razón "Batch deleted"

### 5. Worker de Llamadas (`call_worker.py`)
- ✅ Agregada referencia a colección `batches` en `JobStore.__init__()`
- ✅ **MODIFICADO** `claim_one()` para verificar batches activos
  - Obtiene lista de batches con `is_active: True`
  - Solo toma jobs de batches activos o jobs sin batch
  - Mejora en logs de debug para rastrear el proceso

### 6. Scripts de Mantenimiento

#### `scripts/update_batches_is_active.py`
Script para migración inicial que agrega el campo `is_active` a batches existentes:
```bash
cd app
python scripts/update_batches_is_active.py
```

#### `scripts/cancel_inactive_batch_jobs.py`
Script para cancelar jobs pendientes de batches pausados o eliminados:
```bash
cd app
python scripts/cancel_inactive_batch_jobs.py
```

## Uso de la API

### Pausar un Batch
```bash
# Usando el endpoint específico
curl -X PUT http://localhost:8000/api/v1/batches/{batch_id}/pause

# Usando el endpoint PATCH (recomendado)
curl -X PATCH http://localhost:8000/api/v1/batches/{batch_id} \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Reanudar un Batch
```bash
# Usando el endpoint específico
curl -X PUT http://localhost:8000/api/v1/batches/{batch_id}/resume

# Usando el endpoint PATCH (recomendado)
curl -X PATCH http://localhost:8000/api/v1/batches/{batch_id} \
  -H "Content-Type: application/json" \
  -d '{"is_active": true}'
```

### Actualizar múltiples campos
```bash
curl -X PATCH http://localhost:8000/api/v1/batches/{batch_id} \
  -H "Content-Type: application/json" \
  -d '{
    "is_active": false,
    "name": "Campaña Actualizada",
    "priority": 2
  }'
```

### Eliminar un Batch (cancelando jobs)
```bash
# Sin eliminar jobs (los cancela)
curl -X DELETE http://localhost:8000/api/v1/batches/{batch_id}

# Eliminando jobs también
curl -X DELETE "http://localhost:8000/api/v1/batches/{batch_id}?delete_jobs=true"
```

## Comportamiento del Sistema

### Cuando se pausa un batch (`is_active: false`):
1. ✅ El batch se marca como inactivo en la base de datos
2. ✅ El worker NO tomará nuevos jobs de este batch
3. ✅ Los jobs en progreso continuarán hasta completarse
4. ✅ Los jobs pendientes permanecen sin cambios (listos para cuando se reanude)

### Cuando se elimina un batch:
1. ✅ El batch se elimina de la base de datos
2. ✅ Todos los jobs pendientes/en progreso se marcan como `CANCELLED`
3. ✅ Los jobs completados/fallidos permanecen en la base de datos (histórico)
4. ✅ Opcionalmente se pueden eliminar todos los jobs con `delete_jobs=true`

### Worker (`call_worker.py`):
1. ✅ Antes de tomar un job, verifica que su batch esté activo
2. ✅ Solo procesa jobs de batches con `is_active: True`
3. ✅ También procesa jobs que no tienen batch asignado
4. ✅ Logs detallados del proceso de selección

## Estados de Jobs

Los jobs ahora pueden tener los siguientes estados:
- `pending`: Job listo para ejecutarse
- `scheduled`: Job programado para fecha futura
- `in_progress`: Job siendo procesado actualmente
- `completed`: Job completado exitosamente
- `done`: Alias de completed (compatibilidad)
- `failed`: Job falló después de reintentos
- `suspended`: Job suspendido por falta de créditos
- `cancelled`: **NUEVO** - Job cancelado porque su batch fue pausado o eliminado

## Pasos de Implementación

### 1. Ejecutar Script de Migración (Primera vez)
```bash
cd app
python scripts/update_batches_is_active.py
```

### 2. (Opcional) Cancelar Jobs de Batches Inactivos
```bash
cd app
python scripts/cancel_inactive_batch_jobs.py
```

### 3. Reiniciar Servicios
```bash
# Detener API y Worker si están corriendo

# Iniciar API
python app/run_api.py

# Iniciar Worker
python app/call_worker.py
```

## Verificación

### Verificar que el endpoint PATCH funciona:
```bash
# Probar pausar
curl -X PATCH http://localhost:8000/api/v1/batches/batch-2025-10-25-144129-862530 \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# Verificar en base de datos
db.batches.findOne({batch_id: "batch-2025-10-25-144129-862530"})
```

### Verificar que el worker respeta batches pausados:
1. Pausar un batch con jobs pendientes
2. Observar los logs del worker
3. Confirmar que no toma jobs de ese batch
4. Reanudar el batch
5. Confirmar que vuelve a tomar jobs

## Notas Técnicas

### Compatibilidad con Frontend
El endpoint PATCH es el **más flexible** y recomendado para el frontend:
- Permite actualizar múltiples campos en una sola llamada
- Retorna información clara de qué se actualizó
- Compatible con el patrón REST estándar

### Performance
- La verificación de batches activos agrega una query adicional pero es eficiente:
  - Se cachea la lista de batch_ids activos
  - Solo se ejecuta en cada iteración de `claim_one()`
  - Filtrado se hace a nivel de MongoDB (índices)

### Índices Recomendados
```javascript
// En MongoDB
db.batches.createIndex({ "is_active": 1, "batch_id": 1 })
db.jobs.createIndex({ "batch_id": 1, "status": 1 })
```

## Próximos Pasos Sugeridos

1. ✅ Actualizar frontend para usar `PATCH /api/v1/batches/{batch_id}`
2. ⚠️ Agregar endpoint para obtener estadísticas de jobs cancelados
3. ⚠️ Implementar notificaciones cuando un batch es pausado/reanudado
4. ⚠️ Agregar histórico de cambios de estado del batch (audit log)
5. ⚠️ Implementar pausas automáticas por condiciones (ej: sin créditos)

## Resumen de Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| PUT | `/api/v1/batches/{batch_id}/pause` | Pausar batch (legacy) |
| PUT | `/api/v1/batches/{batch_id}/resume` | Reanudar batch (legacy) |
| **PATCH** | **`/api/v1/batches/{batch_id}`** | **Actualizar batch (recomendado)** |
| POST | `/api/v1/batches/{batch_id}/cancel` | Cancelar batch permanentemente |
| DELETE | `/api/v1/batches/{batch_id}` | Eliminar batch |

---

**Fecha de Implementación:** 25 de Octubre, 2025
**Versión:** 1.0.0
**Estado:** ✅ Implementado y Probado
