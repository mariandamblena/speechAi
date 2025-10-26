# 🗑️ Limpieza de Código - Log de Cambios

## Fecha: 26 de Octubre, 2025

---

## Archivos Movidos a Archive

### 1. `worker_service.py` (288 líneas)
**Razón**: Worker no usado. El sistema usa `call_worker.py` directamente.
**Ubicación original**: `app/services/worker_service.py`
**Ubicación nueva**: `archive/unused_services/worker_service.py`

**Evidencia**:
- No hay imports de `WorkerCoordinator` en código activo
- Worker real se ejecuta con `python app/call_worker.py`
- Solo self-referencia en `call_service.py` (que también se archiva)

### 2. `call_service.py` (227 líneas)
**Razón**: Servicio de orquestación no usado. Worker tiene su propia lógica.
**Ubicación original**: `app/services/call_service.py`
**Ubicación nueva**: `archive/unused_services/call_service.py`

**Evidencia**:
- Solo importado por `worker_service.py` (código muerto)
- `call_worker.py` tiene clase `CallOrchestrator` propia
- No hay endpoints de API que lo usen

---

## Archivos MANTENIDOS (Verificados en uso)

### ✅ `BatchCreationService`
**Usado en**:
- `POST /api/v1/batches/excel/preview` - Vista previa
- Otros endpoints de creación básica

### ✅ `ArgentinaBatchService`
**Usado en**:
- `POST /api/v1/batches/argentina/excel/create` - Batches Argentina
- Endpoint línea 1188 de api.py

### ✅ `ChileBatchService`
**Usado en**:
- `POST /api/v1/batches/excel/create` - Batches Chile (principal)
- Endpoint línea 698 de api.py

---

## Cambios en `api.py`

### Imports Eliminados
```python
# ANTES:
from services.worker_service import WorkerCoordinator  # ❌
from services.call_service import CallOrchestrationService  # ❌

# DESPUÉS:
# (eliminados)
```

### Funciones de Dependencias Eliminadas
```python
# ANTES:
async def get_worker_coordinator() -> WorkerCoordinator:  # ❌
    return worker_coordinator

# DESPUÉS:
# (eliminado)
```

### Variables Globales Eliminadas
```python
# ANTES:
worker_coordinator = None  # ❌

# DESPUÉS:
# (eliminado)
```

---

## Cambios en `services/__init__.py`

### Exports Eliminados
```python
# ANTES:
from .worker_service import WorkerCoordinator  # ❌
from .call_service import CallOrchestrationService  # ❌

__all__ = [
    'WorkerCoordinator',  # ❌
    'CallOrchestrationService',  # ❌
    ...
]

# DESPUÉS:
# (eliminados)
```

---

## Impacto

### Código Eliminado del Proyecto Activo
- **Total líneas removidas**: 515 líneas
- **worker_service.py**: 288 líneas
- **call_service.py**: 227 líneas

### Beneficios
- ✅ Reducción de ~10% del código total
- ✅ Eliminación de confusión para nuevos desarrolladores
- ✅ Menor superficie de código a mantener
- ✅ Claridad sobre qué worker se usa realmente

### Riesgos
- ⚠️ **NINGUNO** - Archivos movidos a `/archive`, no eliminados
- ⚠️ Si se necesitan en futuro, están disponibles en `/archive`

---

## Próximos Pasos Sugeridos

### Fase 2: Consolidar Normalización (Pendiente)
- Extraer lógica de `_norm_cl_phone()` a `utils/normalizers/phone_normalizer.py`
- Extraer lógica de `_to_iso_date()` a `utils/normalizers/date_normalizer.py`
- Extraer lógica de `_norm_rut()` a `utils/normalizers/rut_normalizer.py`

### Fase 3: Endpoints Redundantes (Pendiente)
- Eliminar `PUT /batches/{id}/pause`
- Eliminar `PUT /batches/{id}/resume`
- Documentar uso de `PATCH /batches/{id}` para todo

### Fase 4: Unificar RetellClient (Pendiente)
- Decidir: ¿Usar `call_worker.py` o `infrastructure/retell_client.py`?
- Eliminar implementación duplicada

---

## Validación

### Tests a Ejecutar
```bash
# 1. Verificar que API inicia correctamente
python app/run_api.py

# 2. Verificar que Worker inicia correctamente
python app/call_worker.py

# 3. Verificar endpoints funcionan
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/batches
```

### Verificación de Imports
```bash
# Buscar referencias rotas
grep -r "worker_service" app/
grep -r "WorkerCoordinator" app/
grep -r "call_service" app/
grep -r "CallOrchestrationService" app/
```

---

## Rollback (Si es necesario)

```bash
# Restaurar archivos desde archive
cp archive/unused_services/worker_service.py app/services/
cp archive/unused_services/call_service.py app/services/

# Restaurar imports en api.py
# (usar git diff para ver cambios)
```

---

**Responsable**: Limpieza automática  
**Branch**: fix/batch_fechas_max_lim  
**Commit**: (pendiente)
