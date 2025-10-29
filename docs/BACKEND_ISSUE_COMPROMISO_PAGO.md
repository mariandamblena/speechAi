# 🐛 Issues del Backend - Campos Faltantes en API

## 1. ✅ RESUELTO: Campos de Compromiso de Pago

### 📋 Estado: FUNCIONA CORRECTAMENTE ✅

Los campos `fecha_pago_cliente` y `monto_pago_cliente` **ahora SÍ se devuelven correctamente** en el endpoint `GET /api/v1/jobs`.

**Verificado el 28 de octubre de 2025:**
- ✅ Fecha Prometida: "lunes, 6 de octubre de 2025"
- ✅ Monto Prometido: "$44.583"
- ✅ Los datos se muestran correctamente en el modal de detalle de Job
- ✅ La columna "Compromiso" en la tabla muestra la información
- ✅ La exportación CSV incluye los campos correctamente

**Issue CERRADO** - El backend está funcionando como se esperaba.

---

## 2. 🟡 IMPORTANTE: Configuración de Llamadas No Expuesta en API

### 📋 Descripción del Problema

El campo `call_settings` **nunca es devuelto por la API** ni puede ser configurado. Esto impide que el frontend pueda visualizar y editar la configuración de las llamadas de una campaña.

### 🔍 Evidencia

**Campo requerido por el frontend pero NO devuelto:**

```typescript
// Campo que el frontend necesita pero el backend NO devuelve:
interface BatchModel {
  // ❌ NO DEVUELTO:
  call_settings: {
    max_call_duration: number;        // Duración máxima de llamada
    ring_timeout: number;              // Tiempo de timbrado
    max_attempts: number;              // Intentos máximos
    retry_delay_hours: number;         // Horas entre reintentos
    allowed_hours: {                   // Horario permitido
      start: string;                   // Ej: "09:00"
      end: string;                     // Ej: "20:00"
    };
    days_of_week: number[];            // Días permitidos [1,2,3,4,5] = Lun-Vie
    timezone: string;                  // Zona horaria (ej: "America/Santiago")
  };
}
```

**Lo que SÍ devuelve actualmente `GET /api/v1/batches/{batch_id}`:**

```json
{
  "_id": "68fd0cdc8ac7d47a518bc017",
  "batch_id": "batch-2025-10-25-144604-615037",
  "name": "Testing GG Group",
  "description": "testing",
  "account_id": "retail_express",
  "total_jobs": 12,
  "pending_jobs": 12,
  "completed_jobs": 0,
  "failed_jobs": 0,
  "suspended_jobs": 0,
  "total_cost": 0.0,
  "total_minutes": 0.0,
  "estimated_cost": 5.64,
  "is_active": true,
  "priority": 1,
  "created_at": "2025-10-25T17:46:04.648000",
  "updated_at": "2025-10-25T18:01:29.436000"
}
```

### 📊 Endpoints Afectados

| Endpoint | Impacto |
|----------|---------|
| `GET /api/v1/batches/{batch_id}` | No devuelve `call_settings`, imposible visualizar |
| `POST /api/v1/batches/excel/create` | No acepta `call_settings`, solo usa defaults |
| `PATCH /api/v1/batches/{batch_id}` | Solo permite `is_active`, `name`, `description`, `priority` - no permite editar `call_settings` |

### 🎯 Funcionalidades Bloqueadas

1. ❌ **Ver configuración de llamadas**: Frontend no puede mostrar duración máxima, timeout, intentos, horarios permitidos
2. ❌ **Editar configuración**: Imposible modificar parámetros de llamadas de una campaña existente
3. ⚠️ **Duplicar con configuración personalizada**: Solo se puede copiar nombre, descripción y prioridad (no la configuración de llamadas)
4. ❌ **Configurar al crear**: No se pueden personalizar parámetros de llamada al crear una campaña nueva

### 💡 Soluciones Propuestas

#### Opción 1: Devolver `call_settings` en GET (⭐ RECOMENDADO)
```python
# En el backend, agregar a la respuesta de GET /batches/{batch_id}:
{
  # ... campos actuales (name, description, priority, etc.) ...
  
  # ⬇️ AGREGAR:
  "call_settings": {
    "max_call_duration": 300,
    "ring_timeout": 30,
    "max_attempts": 3,
    "retry_delay_hours": 24,
    "allowed_hours": {"start": "09:00", "end": "20:00"},
    "days_of_week": [1, 2, 3, 4, 5],  # 0=Dom, 1=Lun, ..., 6=Sab
    "timezone": "America/Santiago"
  }
}
```

#### Opción 2: Permitir configurar al crear campaña
```python
# POST /api/v1/batches/excel/create
# Agregar parámetro opcional call_settings:
{
  "file": File,
  "account_id": "retail_express",
  "batch_name": "Campaña Octubre",
  "call_settings": {  # ← NUEVO (opcional)
    "max_call_duration": 300,
    "ring_timeout": 30,
    "max_attempts": 3,
    "retry_delay_hours": 24,
    "allowed_hours": {"start": "09:00", "end": "20:00"},
    "days_of_week": [1, 2, 3, 4, 5],
    "timezone": "America/Santiago"
  }
}
```

#### Opción 3: Permitir editar configuración (PATCH)
```python
# Modificar endpoint existente para aceptar call_settings:
PATCH /api/v1/batches/{batch_id}
{
  "name": "Nueva Campaña",          # Ya soportado
  "description": "...",              # Ya soportado
  "priority": 2,                     # Ya soportado
  "is_active": true,                 # Ya soportado
  
  "call_settings": {                 # ← AGREGAR
    "max_call_duration": 300,
    "ring_timeout": 30,
    "max_attempts": 3,
    "retry_delay_hours": 24,
    "allowed_hours": {"start": "09:00", "end": "20:00"},
    "days_of_week": [1, 2, 3, 4, 5],
    "timezone": "America/Santiago"
  }
}
```

**Recomendación**: Implementar las 3 opciones para tener funcionalidad completa (GET, POST, PATCH).

### 🔧 Workaround Actual en Frontend

Por ahora, el frontend:
- ✅ Eliminó visualización de campos no disponibles (`voice_settings`, `script_content`)
- ✅ Muestra mensaje informativo en "Editar Configuración" explicando limitaciones de la API
- ✅ Implementó "Duplicar Campaña" que copia solo campos disponibles (nombre, descripción, prioridad)
- ⚠️ Mantiene tab "Configuración" pero con funcionalidad muy limitada (solo visualización, sin datos reales)

### 📅 Prioridad y Estado

- **Detectado**: 28 de octubre de 2025
- **Prioridad**: Media-Alta (funcionalidad importante para control de campañas)
- **Asignado a**: Backend Team
- **Estado**: Pendiente de implementación

---

## 📝 Resumen de Issues

| # | Issue | Severidad | Estado |
|---|-------|-----------|--------|
| 1 | Campos de compromiso de pago | ✅ RESUELTO | Funcionando correctamente |
| 2 | Configuración de llamadas no expuesta (`call_settings`) | 🟡 IMPORTANTE | Pendiente |

---

**Última actualización**: 28 de octubre de 2025  
**Responsable**: Backend Team

**Issues Cerrados**: 1 de 2 (50%)  
**Issues Pendientes**: 1 de 2 (50%)

**Nota**: El Issue #2 se enfoca solo en `call_settings`. Los campos `voice_settings` y `script_content` no se implementarán por ahora en el frontend.
