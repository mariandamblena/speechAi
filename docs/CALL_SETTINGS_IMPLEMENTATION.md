# ✅ Implementación de `call_settings` por Campaign/Batch

## 📋 Resumen

Se ha completado la implementación de **configuraciones de llamada por batch/campaña**, resolviendo el **Problema #1 de Arquitectura** identificado en el análisis.

**Antes (INCORRECTO)**: Las configuraciones de llamada (horarios, timezone, reintentos) estaban en `AccountModel`, limitando flexibilidad.

**Ahora (CORRECTO)**: Cada batch/campaña puede tener sus propias configuraciones mediante el campo `call_settings`.

---

## 🎯 Estructura de `call_settings`

El campo `call_settings` es un diccionario opcional con la siguiente estructura:

```python
call_settings = {
    "allowed_call_hours": {
        "start": "09:00",  # Hora inicio en formato HH:MM
        "end": "18:00"     # Hora fin en formato HH:MM
    },
    "timezone": "America/Santiago",  # Zona horaria (pytz format)
    "retry_settings": {
        "max_attempts": 3,           # Intentos máximos
        "retry_delay_hours": 24      # Horas entre reintentos
    },
    "max_concurrent_calls": 10  # Límite de llamadas concurrentes para este batch
}
```

---

## 📝 Cambios Implementados

### 1. **Modelo de Datos** (`app/domain/models.py`)

#### Clase `BatchModel`

**Campo agregado:**
```python
call_settings: Optional[Dict[str, Any]] = None
```

**Método `to_dict()` actualizado:**
```python
def to_dict(self) -> Dict[str, Any]:
    data = {
        # ... campos existentes ...
        "call_settings": self.call_settings,  # ✅ NUEVO
        # ... más campos ...
    }
    return data
```

**Método `from_dict()` actualizado:**
```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> "BatchModel":
    return cls(
        # ... campos existentes ...
        call_settings=data.get("call_settings"),  # ✅ NUEVO
        # ... más campos ...
    )
```

---

### 2. **Request Models** (`app/api.py`)

#### `CreateBatchRequest`

```python
class CreateBatchRequest(BaseModel):
    account_id: str
    name: str
    description: str = ""
    priority: int = 1
    call_settings: Optional[Dict[str, Any]] = None  # ✅ NUEVO
```

---

### 3. **Endpoint POST /api/v1/batches** (`app/api.py`)

**Antes:**
```python
batch = await service.create_batch(
    request.account_id, 
    request.name, 
    request.description, 
    request.priority
)
```

**Ahora:**
```python
batch = await service.create_batch(
    request.account_id, 
    request.name, 
    request.description, 
    request.priority,
    request.call_settings  # ✅ NUEVO
)
```

---

### 4. **Endpoint POST /api/v1/batches/excel/create** (`app/api.py`)

**Parámetro agregado:**
```python
call_settings_json: Optional[str] = Query(
    None, 
    description="JSON string con configuración de llamadas para este batch"
)
```

**Parsing del JSON:**
```python
call_settings = None
if call_settings_json:
    import json
    try:
        call_settings = json.loads(call_settings_json)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"call_settings_json debe ser un JSON válido: {str(e)}"
        )
```

**Llamada al servicio:**
```python
# Basic processing
result = await basic_service.create_batch_from_excel(
    file_content=content,
    account_id=account_id,
    batch_name=batch_name,
    batch_description=batch_description,
    allow_duplicates=allow_duplicates,
    dias_fecha_limite=dias_fecha_limite,
    dias_fecha_maxima=dias_fecha_maxima,
    call_settings=call_settings  # ✅ NUEVO
)

# Acquisition processing
result = await chile_service.create_batch_from_excel_acquisition(
    file_content=content,
    account_id=account_id,
    batch_name=batch_name,
    batch_description=batch_description,
    allow_duplicates=allow_duplicates,
    dias_fecha_limite=dias_fecha_limite,
    dias_fecha_maxima=dias_fecha_maxima,
    call_settings=call_settings  # ✅ NUEVO
)
```

---

### 5. **Servicio BatchService** (`app/services/batch_service.py`)

**Import agregado:**
```python
from typing import Dict, Optional, List, Any  # ✅ Any agregado
```

**Método `create_batch()` actualizado:**
```python
async def create_batch(
    self,
    account_id: str,
    name: str,
    description: str = "",
    priority: int = 1,
    call_settings: Optional[Dict[str, Any]] = None  # ✅ NUEVO
) -> BatchModel:
    """Crea un nuevo batch con configuración de llamadas opcional"""
    
    batch_id = f"batch-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
    
    batch = BatchModel(
        account_id=account_id,
        batch_id=batch_id,
        name=name,
        description=description,
        priority=priority,
        call_settings=call_settings,  # ✅ NUEVO
        created_at=datetime.utcnow()
    )
    
    result = await self.batches_collection.insert_one(batch.to_dict())
    batch._id = result.inserted_id
    
    self.logger.info(f"Created batch {batch_id} for account {account_id}")
    if call_settings:
        self.logger.info(f"Batch {batch_id} has custom call_settings: {call_settings}")
    
    return batch
```

---

### 6. **Servicio BatchCreationService** (`app/services/batch_creation_service.py`)

**Método `create_batch_from_excel()` actualizado:**
```python
async def create_batch_from_excel(
    self, 
    file_content: bytes, 
    account_id: str, 
    batch_name: str = None,
    batch_description: str = None,
    allow_duplicates: bool = False,
    dias_fecha_limite: Optional[int] = None,
    dias_fecha_maxima: Optional[int] = None,
    call_settings: Optional[Dict[str, Any]] = None  # ✅ NUEVO
) -> Dict[str, Any]:
```

**Creación del BatchModel:**
```python
batch = BatchModel(
    account_id=account_id,
    batch_id=batch_id,
    name=batch_name or f"Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
    description=batch_description or f"Importado desde Excel con {len(valid_debtors)} deudores",
    total_jobs=len(valid_debtors),
    pending_jobs=len(valid_debtors),
    call_settings=call_settings,  # ✅ NUEVO
    created_at=datetime.utcnow()
)
```

---

### 7. **Servicio ChileBatchService** (`app/services/chile_batch_service.py`)

**Método `create_batch_from_excel_acquisition()` actualizado:**
```python
async def create_batch_from_excel_acquisition(
    self,
    file_content: bytes,
    account_id: str,
    batch_name: str = None,
    batch_description: str = None,
    allow_duplicates: bool = False,
    dias_fecha_limite: Optional[int] = None,
    dias_fecha_maxima: Optional[int] = None,
    call_settings: Optional[Dict[str, Any]] = None  # ✅ NUEVO
) -> Dict[str, Any]:
```

**Creación del BatchModel:**
```python
batch = BatchModel(
    account_id=account_id,
    batch_id=batch_id_unique,
    name=batch_name,
    description=batch_description or f"Acquisition batch with {len(valid_debtors)} debtors",
    total_jobs=len(valid_debtors),
    pending_jobs=len(valid_debtors),
    completed_jobs=0,
    failed_jobs=0,
    is_active=True,
    call_settings=call_settings,  # ✅ NUEVO
    created_at=datetime.utcnow(),
    priority=1
)
```

---

## 🔧 Ejemplos de Uso

### 1. **Crear Batch con POST /api/v1/batches**

```json
POST /api/v1/batches
Content-Type: application/json

{
  "account_id": "acc-123",
  "name": "Campaña Cobranza Urgente",
  "description": "Llamadas de cobranza con horario extendido",
  "priority": 1,
  "call_settings": {
    "allowed_call_hours": {
      "start": "09:00",
      "end": "20:00"
    },
    "timezone": "America/Santiago",
    "retry_settings": {
      "max_attempts": 5,
      "retry_delay_hours": 12
    },
    "max_concurrent_calls": 15
  }
}
```

---

### 2. **Crear Batch desde Excel con call_settings**

```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@chile_10_usuarios.xlsx" \
  -F "account_id=acc-123" \
  -F "batch_name=Campaña Marketing" \
  -F "batch_description=Marketing con horario limitado" \
  -F "processing_type=acquisition" \
  -F "dias_fecha_limite=30" \
  -F "call_settings_json={\"allowed_call_hours\":{\"start\":\"10:00\",\"end\":\"18:00\"},\"timezone\":\"America/Santiago\",\"retry_settings\":{\"max_attempts\":3,\"retry_delay_hours\":24},\"max_concurrent_calls\":5}"
```

---

### 3. **Campaña sin call_settings (usa defaults de Account)**

```json
POST /api/v1/batches
Content-Type: application/json

{
  "account_id": "acc-123",
  "name": "Campaña Estándar",
  "description": "Usa configuración de cuenta",
  "priority": 1
}
```

**Resultado**: `call_settings` será `None`, el worker usará la configuración del `AccountModel`.

---

## ✅ Beneficios de la Implementación

### 1. **Flexibilidad por Campaña**
- Cobranza urgente: 09:00-20:00, 5 reintentos cada 12 horas
- Marketing: 10:00-18:00, 3 reintentos cada 24 horas
- Encuestas: 11:00-17:00, 2 reintentos cada 48 horas

### 2. **Retrocompatibilidad Total**
- Batches sin `call_settings` funcionan igual que antes
- No requiere migración de datos existentes
- MongoDB acepta `call_settings: null` sin problemas

### 3. **Separación de Concerns**
- Account: configuración general de la cuenta
- Batch: configuración específica de campaña
- Job: datos individuales de cada contacto

### 4. **Escalabilidad**
- Fácil agregar más opciones a `call_settings` en el futuro
- Ejemplo: `voice_settings`, `transfer_rules`, `recording_options`

---

## 🧪 Testing

### Validar Serialización

```python
# Crear batch con call_settings
batch = BatchModel(
    account_id="acc-test",
    batch_id="batch-test-001",
    name="Test Batch",
    call_settings={
        "allowed_call_hours": {"start": "09:00", "end": "18:00"},
        "timezone": "America/Santiago"
    },
    created_at=datetime.utcnow()
)

# Convertir a dict (para MongoDB)
batch_dict = batch.to_dict()
assert "call_settings" in batch_dict
assert batch_dict["call_settings"]["timezone"] == "America/Santiago"

# Reconstruir desde dict
restored_batch = BatchModel.from_dict(batch_dict)
assert restored_batch.call_settings is not None
assert restored_batch.call_settings["timezone"] == "America/Santiago"
```

---

## 📊 Estado Actual

| Componente | Estado | Notas |
|------------|--------|-------|
| **BatchModel** | ✅ Completo | Campo `call_settings` agregado y serialización funcionando |
| **API Endpoints** | ✅ Completo | POST `/batches` y POST `/batches/excel/create` actualizados |
| **BatchService** | ✅ Completo | Método `create_batch()` acepta y persiste `call_settings` |
| **BatchCreationService** | ✅ Completo | Excel básico soporta `call_settings` |
| **ChileBatchService** | ✅ Completo | Excel acquisition soporta `call_settings` |
| **Worker Integration** | ⚠️ Pendiente | Workers deben leer `call_settings` del batch al ejecutar jobs |
| **Documentación Frontend** | ⚠️ Pendiente | Actualizar docs con ejemplos de integración |

---

## 🚀 Próximos Pasos

### 1. **Integración en Workers** (Prioridad Alta)
Modificar `call_worker.py` y `universal_call_worker.py` para:
- Leer `call_settings` del batch al procesar un job
- Aplicar `allowed_call_hours` y `timezone` antes de llamar
- Usar `retry_settings` para lógica de reintentos
- Respetar `max_concurrent_calls` del batch

### 2. **Implementación de Endpoints Faltantes** (Problem #3)
- GET `/api/v1/batches/{batch_id}/summary` - Resumen completo del batch
- GET `/api/v1/batches/{batch_id}/status` - Estado para polling frontend
- POST `/api/v1/batches/{batch_id}/cancel` - Cancelar batch completamente
- GET `/api/v1/dashboard/overview` - Métricas del dashboard

### 3. **Documentación para Frontend**
- Ejemplos de requests con `call_settings`
- Guía de valores válidos para `timezone` (pytz)
- Formato de `allowed_call_hours`
- Validaciones y restricciones

---

## 📚 Referencias

- **ISSUES_ARQUITECTURA.md**: Análisis original del problema
- **ANALISIS_ENDPOINTS.md**: Endpoints faltantes identificados
- **CALCULO_FECHAS_DINAMICO.md**: Feature de fechas dinámicas (relacionado)

---

**Fecha de implementación**: 2025-01-15  
**Versión del sistema**: 1.0.0  
**Autor**: GitHub Copilot + Usuario  
**Estado**: ✅ **PROBLEMA #1 RESUELTO**
