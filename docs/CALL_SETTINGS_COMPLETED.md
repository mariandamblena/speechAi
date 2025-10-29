# ✅ Implementación Completada: call_settings en API

## 🎯 Problema Resuelto

El frontend no podía visualizar ni editar la configuración de llamadas de las campañas porque `call_settings` no estaba expuesta en la API.

## 🔧 Solución Implementada

### Cambios Realizados

1. **UpdateBatchRequest** (app/api.py línea ~82)
   ```python
   class UpdateBatchRequest(BaseModel):
       is_active: Optional[bool] = None
       name: Optional[str] = None
       description: Optional[str] = None
       priority: Optional[int] = None
       call_settings: Optional[Dict[str, Any]] = None  # ✅ NUEVO
   ```

2. **Endpoint PATCH** (app/api.py línea ~620)
   ```python
   if request.call_settings is not None:
       update_data["call_settings"] = request.call_settings
   ```

3. **ExcelBatchRequest** (app/api.py línea ~73)
   ```python
   class ExcelBatchRequest(BaseModel):
       account_id: str
       batch_name: Optional[str] = None
       batch_description: Optional[str] = None
       allow_duplicates: bool = False
       call_settings: Optional[Dict[str, Any]] = None  # ✅ NUEVO
   ```

4. **POST Excel** (app/api.py línea ~780)
   - Ya soportaba `call_settings_json` como Form parameter
   - Se pasa correctamente a los servicios de creación de batches

## ✅ Funcionalidades Ahora Disponibles

### 1. GET - Leer Configuración
```bash
GET /api/v1/batches/{batch_id}

Response:
{
  "batch_id": "batch-2025-10-27-133349-845994",
  "name": "Mi Campaña",
  "call_settings": {
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

### 2. PATCH - Editar Configuración
```bash
PATCH /api/v1/batches/{batch_id}
Content-Type: application/json

{
  "call_settings": {
    "max_attempts": 5,
    "retry_delay_hours": 48,
    "allowed_hours": {
      "start": "08:00",
      "end": "21:00"
    },
    "days_of_week": [1, 2, 3, 4, 5, 6],
    "timezone": "America/Santiago"
  }
}

Response:
{
  "success": true,
  "message": "Batch updated successfully",
  "batch_id": "batch-2025-10-27-133349-845994",
  "updated_fields": ["call_settings", "updated_at"]
}
```

### 3. POST - Crear con Configuración
```bash
POST /api/v1/batches/excel/create
Content-Type: multipart/form-data

file: archivo.xlsx
account_id: acc-123
batch_name: "Mi Campaña"
call_settings_json: '{"max_attempts": 5, "allowed_hours": {"start": "09:00", "end": "20:00"}}'
```

## 📊 Estructura de call_settings

```typescript
interface CallSettings {
  // Configuración de intentos
  max_attempts?: number;              // Intentos máximos (default: 3)
  retry_delay_hours?: number;         // Horas entre reintentos (default: 24)
  
  // Configuración de horarios
  allowed_hours?: {
    start: string;                     // "HH:MM" (ej: "09:00")
    end: string;                       // "HH:MM" (ej: "20:00")
  };
  
  days_of_week?: number[];            // 0=Dom, 1=Lun...6=Sab
                                       // Ej: [1,2,3,4,5] = Lun-Vie
  
  timezone?: string;                  // Zona horaria (ej: "America/Santiago")
  
  // Configuración de duración (NO usado por worker aún)
  max_call_duration?: number;         // Duración máxima en segundos
  ring_timeout?: number;              // Timeout de timbrado en segundos
}
```

## 🧪 Tests Ejecutados

### Script: test_call_settings.py

**Resultados: 4/4 tests PASADOS ✅**

1. ✅ GET /api/v1/batches devuelve call_settings
2. ✅ GET /api/v1/batches/{batch_id} incluye call_settings
3. ✅ PATCH actualiza call_settings correctamente
4. ✅ PATCH resetea call_settings a null

### Evidencia:
```
✅ Campo 'call_settings' presente en la respuesta
✅ Call settings configurados:
  - max_attempts: 3
  - retry_delay_hours: 24
  - allowed_hours: {'start': '09:00', 'end': '18:00'}
  - days_of_week: [1, 2, 3, 4, 5]
  - timezone: America/Santiago

✅ Actualización exitosa: Batch updated successfully
✅ Call settings guardados correctamente
```

## 🔄 Integración con Worker

El `call_worker.py` YA ESTABA preparado para usar `call_settings`:

1. **Lee call_settings del batch** (línea 970)
   ```python
   batch = self._get_batch(batch_id)
   call_settings = batch.get('call_settings', {})
   ```

2. **Respeta max_attempts** (línea 1001)
   ```python
   max_attempts = call_settings.get("max_attempts", MAX_TRIES)
   ```

3. **Valida horarios permitidos** (línea 686)
   ```python
   allowed_hours = call_settings.get("allowed_hours", {})
   ```

4. **Usa timezone** (línea 661)
   ```python
   tz_str = call_settings.get("timezone", "America/Santiago")
   ```

5. **Usa retry_delay_hours** (línea 586)
   ```python
   retry_delay_hours = call_settings["retry_delay_hours"]
   ```

## 📝 Documentación Creada

1. **CALL_SETTINGS_IMPLEMENTATION_PLAN.md**
   - Análisis completo del worker
   - Estructura de call_settings
   - Guía de implementación paso a paso

2. **test_call_settings.py**
   - Tests automatizados
   - Validación de GET/PATCH
   - Verificación de persistencia

3. **CALL_SETTINGS_COMPLETED.md** (este documento)
   - Resumen de implementación
   - Ejemplos de uso
   - Resultados de testing

## ✅ Estado del Issue #2

### Issue Original
> El campo `call_settings` **nunca es devuelto por la API** ni puede ser configurado. 
> Esto impide que el frontend pueda visualizar y editar la configuración de las llamadas.

### Estado Actual: ✅ RESUELTO

- ✅ GET devuelve call_settings
- ✅ PATCH acepta y actualiza call_settings
- ✅ POST acepta call_settings al crear
- ✅ Worker respeta configuraciones
- ✅ Tests pasando 100%

## 🎉 Frontend Puede Ahora

1. ✅ **Visualizar** configuración de llamadas existente
2. ✅ **Editar** max_attempts, retry_delay_hours, horarios, días permitidos
3. ✅ **Crear** campañas con configuración personalizada
4. ✅ **Duplicar** campañas incluyendo configuración

## 📅 Commits

1. **fix: Add to_number field to JobModel.to_dict()** (ce7809b)
   - Campo to_number para routing
   - Script de testing de endpoints

2. **feat: Expose call_settings in API** (0a25ab4)
   - Agregar call_settings a UpdateBatchRequest
   - Agregar call_settings a ExcelBatchRequest
   - Handling en PATCH endpoint
   - Documentación completa

## 🚀 Próximos Pasos

1. **Frontend**: Implementar UI para editar call_settings
2. **Validación**: Agregar validators en Pydantic (opcional)
3. **Documentación**: Actualizar API reference
4. **Testing**: Agregar tests de integración worker + API

---

**Fecha**: 28 de octubre de 2025  
**Branch**: refactor/eliminate-job-duplicates  
**Status**: ✅ COMPLETADO Y TESTEADO
