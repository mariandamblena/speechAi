# 📋 Análisis: Implementación de call_settings en API

## 🔍 Estado Actual

### ✅ Lo que YA existe en el backend:

1. **BatchModel tiene `call_settings` definido** (app/domain/models.py línea 716)
   ```python
   call_settings: Optional[Dict[str, Any]] = None
   ```

2. **Worker ya usa `call_settings`** (app/call_worker.py línea 970+)
   - Lee `call_settings` del batch
   - Usa `max_attempts` del call_settings
   - Valida horarios permitidos (`allowed_hours`, `days_of_week`)
   - Usa `timezone` para validación horaria
   - Usa `retry_delay_hours` para reintentos

3. **Estructura esperada por el worker**:
   ```python
   call_settings = {
       "max_attempts": 3,                    # Usado en línea 1001
       "retry_delay_hours": 24,              # Usado en línea 586
       "allowed_hours": {                    # Usado en línea 686
           "start": "09:00",
           "end": "20:00"
       },
       "days_of_week": [1, 2, 3, 4, 5],    # Usado en línea 676 (0=Dom, 1=Lun...6=Sab)
       "timezone": "America/Santiago"        # Usado en línea 661
   }
   ```

### ❌ Lo que FALTA:

1. **API NO devuelve `call_settings`** en GET endpoints
2. **API NO acepta `call_settings`** en POST/PATCH endpoints
3. **Frontend no puede ver ni editar configuraciones**

---

## 🎯 Solución Propuesta

### Fase 1: Exponer `call_settings` en GET (✅ LISTO)
El `BatchModel.to_dict()` YA incluye `call_settings` (línea 762), por lo que GET ya lo devuelve.

**Confirmación**: El endpoint `GET /api/v1/batches/{batch_id}` ya llama a `batch.to_dict()` que incluye `call_settings`.

### Fase 2: Permitir configurar en POST/PATCH

#### 2.1. Agregar a `CreateBatchRequest` (OPCIONAL)
El request model ya tiene un campo `call_settings` (línea 55-61):
```python
class CreateBatchRequest(BaseModel):
    account_id: str
    name: str
    description: str = ""
    priority: int = 1
    call_settings: Optional[Dict[str, Any]] = None  # ✅ YA EXISTE
```

#### 2.2. Agregar a `UpdateBatchRequest` (REQUERIDO)
```python
class UpdateBatchRequest(BaseModel):
    """Request para actualizar un batch"""
    is_active: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    call_settings: Optional[Dict[str, Any]] = None  # ⬅️ AGREGAR ESTO
```

#### 2.3. Modificar endpoint PATCH (línea 595)
```python
@app.patch("/api/v1/batches/{batch_id}")
async def update_batch(
    batch_id: str,
    request: UpdateBatchRequest,
    service: BatchService = Depends(get_batch_service)
):
    update_data = {}
    
    if request.is_active is not None:
        update_data["is_active"] = request.is_active
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.priority is not None:
        update_data["priority"] = request.priority
    
    # ⬇️ AGREGAR ESTO:
    if request.call_settings is not None:
        update_data["call_settings"] = request.call_settings
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    success = await service.update_batch(batch_id, update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    message = "Batch updated successfully"
    if request.is_active is not None:
        message = "Batch resumed" if request.is_active else "Batch paused"
    
    return {
        "success": True, 
        "message": message,
        "batch_id": batch_id,
        "updated_fields": list(update_data.keys())
    }
```

#### 2.4. Agregar a `ExcelBatchRequest` (OPCIONAL pero recomendado)
```python
class ExcelBatchRequest(BaseModel):
    account_id: str
    batch_name: Optional[str] = None
    batch_description: Optional[str] = None
    allow_duplicates: bool = False
    call_settings: Optional[Dict[str, Any]] = None  # ⬅️ AGREGAR ESTO
```

#### 2.5. Modificar endpoint POST excel/create (línea 692)
Buscar donde se crea el batch y pasar `call_settings`:
```python
# En el endpoint /api/v1/batches/excel/create
batch_data = {
    "account_id": account_id,
    "name": batch_name,
    "description": batch_description or "",
    "call_settings": request.call_settings,  # ⬅️ AGREGAR ESTO
    # ... otros campos
}
```

---

## 📊 Campos de `call_settings`

### Estructura Completa
```typescript
interface CallSettings {
  // Configuración de intentos
  max_attempts?: number;              // Default: 3
  retry_delay_hours?: number;         // Default: 24
  
  // Configuración de horarios
  allowed_hours?: {
    start: string;                     // Format: "HH:MM" (e.g., "09:00")
    end: string;                       // Format: "HH:MM" (e.g., "20:00")
  };
  
  days_of_week?: number[];            // 0=Domingo, 1=Lunes, ..., 6=Sábado
                                       // Ejemplo: [1,2,3,4,5] = Lun-Vie
  
  timezone?: string;                  // Zona horaria (e.g., "America/Santiago")
  
  // Configuración de duración (NO implementado en worker aún)
  max_call_duration?: number;         // Duración máxima en segundos
  ring_timeout?: number;              // Timeout de timbrado en segundos
}
```

### Valores por Defecto (usados por el worker)
```python
DEFAULT_CALL_SETTINGS = {
    "max_attempts": 3,                    # MAX_TRIES en worker
    "retry_delay_hours": 24,              # Calculado en mark_failed()
    "allowed_hours": {
        "start": "09:00",
        "end": "20:00"
    },
    "days_of_week": [1, 2, 3, 4, 5],    # Lun-Vie
    "timezone": "America/Santiago"
}
```

---

## 🔧 Implementación Paso a Paso

### Paso 1: Modificar `UpdateBatchRequest`
**Archivo**: `app/api.py` línea ~79
```python
class UpdateBatchRequest(BaseModel):
    """Request para actualizar un batch"""
    is_active: Optional[bool] = None
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    call_settings: Optional[Dict[str, Any]] = None  # ⬅️ NUEVO
```

### Paso 2: Modificar endpoint PATCH
**Archivo**: `app/api.py` línea ~595
```python
@app.patch("/api/v1/batches/{batch_id}")
async def update_batch(...):
    update_data = {}
    
    # ... código existente ...
    
    if request.call_settings is not None:  # ⬅️ NUEVO
        update_data["call_settings"] = request.call_settings
    
    # ... resto del código ...
```

### Paso 3: Modificar `ExcelBatchRequest` (OPCIONAL)
**Archivo**: `app/api.py` línea ~73
```python
class ExcelBatchRequest(BaseModel):
    account_id: str
    batch_name: Optional[str] = None
    batch_description: Optional[str] = None
    allow_duplicates: bool = False
    call_settings: Optional[Dict[str, Any]] = None  # ⬅️ NUEVO
```

### Paso 4: Pasar call_settings al crear batch desde Excel
**Archivo**: `app/api.py` línea ~700+ (en el endpoint POST excel/create)

Buscar donde se llama a `batch_service.create_batch()` o similar y agregar `call_settings`.

---

## 🧪 Testing

### Test 1: GET devuelve call_settings
```bash
curl http://localhost:8000/api/v1/batches/{batch_id}

# Esperado:
{
  "batch_id": "...",
  "name": "...",
  "call_settings": {
    "max_attempts": 3,
    "retry_delay_hours": 24,
    "allowed_hours": {"start": "09:00", "end": "20:00"},
    "days_of_week": [1,2,3,4,5],
    "timezone": "America/Santiago"
  }
}
```

### Test 2: PATCH actualiza call_settings
```bash
curl -X PATCH http://localhost:8000/api/v1/batches/{batch_id} \
  -H "Content-Type: application/json" \
  -d '{
    "call_settings": {
      "max_attempts": 5,
      "retry_delay_hours": 48,
      "allowed_hours": {"start": "08:00", "end": "21:00"},
      "days_of_week": [1,2,3,4,5,6],
      "timezone": "America/Santiago"
    }
  }'

# Esperado:
{
  "success": true,
  "message": "Batch updated successfully",
  "batch_id": "...",
  "updated_fields": ["call_settings"]
}
```

### Test 3: Worker respeta configuración
```python
# Crear un batch con call_settings personalizados
# Crear jobs en ese batch
# Verificar que el worker:
# - Respeta max_attempts personalizado
# - Respeta horarios personalizados
# - Usa retry_delay_hours correcto
```

---

## ⚠️ Consideraciones

### 1. Validación
Agregar validación en el request model:
```python
from pydantic import validator

class UpdateBatchRequest(BaseModel):
    call_settings: Optional[Dict[str, Any]] = None
    
    @validator('call_settings')
    def validate_call_settings(cls, v):
        if v is None:
            return v
        
        # Validar max_attempts
        if 'max_attempts' in v:
            if not isinstance(v['max_attempts'], int) or v['max_attempts'] < 1:
                raise ValueError('max_attempts debe ser un entero >= 1')
        
        # Validar allowed_hours
        if 'allowed_hours' in v:
            if not isinstance(v['allowed_hours'], dict):
                raise ValueError('allowed_hours debe ser un objeto')
            if 'start' not in v['allowed_hours'] or 'end' not in v['allowed_hours']:
                raise ValueError('allowed_hours debe tener start y end')
        
        # Validar days_of_week
        if 'days_of_week' in v:
            if not isinstance(v['days_of_week'], list):
                raise ValueError('days_of_week debe ser una lista')
            if not all(isinstance(d, int) and 0 <= d <= 6 for d in v['days_of_week']):
                raise ValueError('days_of_week debe contener números entre 0 y 6')
        
        return v
```

### 2. Defaults
Si `call_settings` es None, el worker usa sus propios defaults (variables de entorno).

### 3. Migración
Batches existentes sin `call_settings` seguirán funcionando con defaults del worker.

### 4. Cache del Worker
El worker cachea los batches. Si se actualiza `call_settings`:
- Cache expira después de `cache_ttl` (default: 300 segundos)
- O reiniciar worker para forzar recarga

---

## 📝 Resumen de Cambios Necesarios

| Archivo | Línea | Cambio | Prioridad |
|---------|-------|--------|-----------|
| `app/api.py` | ~79 | Agregar `call_settings` a `UpdateBatchRequest` | ⭐⭐⭐ ALTA |
| `app/api.py` | ~620 | Agregar handling de `call_settings` en PATCH | ⭐⭐⭐ ALTA |
| `app/api.py` | ~73 | Agregar `call_settings` a `ExcelBatchRequest` | ⭐⭐ MEDIA |
| `app/api.py` | ~700+ | Pasar `call_settings` al crear batch | ⭐⭐ MEDIA |
| `app/api.py` | ~79+ | Agregar validador de `call_settings` | ⭐ BAJA |

**Estimación de tiempo**: 30-60 minutos para implementación completa + testing

---

## ✅ Checklist de Implementación

- [ ] Modificar `UpdateBatchRequest` agregando `call_settings`
- [ ] Modificar endpoint PATCH para aceptar `call_settings`
- [ ] Probar GET devuelve `call_settings` (debería ya funcionar)
- [ ] Probar PATCH actualiza `call_settings`
- [ ] Modificar `ExcelBatchRequest` (opcional)
- [ ] Modificar endpoint POST excel/create (opcional)
- [ ] Agregar validación de campos (opcional)
- [ ] Crear tests de integración
- [ ] Verificar que worker respeta configuraciones
- [ ] Actualizar documentación del issue

---

**Última actualización**: 28 de octubre de 2025  
**Status**: ⏳ ANÁLISIS COMPLETO - LISTO PARA IMPLEMENTAR
