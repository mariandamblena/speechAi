# API Reference para Frontend - SpeechAI Backend

**Base URL:** `http://localhost:8000/api/v1`

**Última actualización:** 25 de Octubre, 2025

---

## 📋 Índice

- [System](#system)
- [Accounts (Cuentas)](#accounts-cuentas)
- [Batches (Campañas)](#batches-campañas)
- [Jobs (Llamadas Individuales)](#jobs-llamadas-individuales)
- [Dashboard & Reportes](#dashboard--reportes)
- [Use Cases](#use-cases)

---

## System

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-25T18:00:00.000000",
  "database": "connected"
}
```

---

## Accounts (Cuentas)

### Crear cuenta
```http
POST /api/v1/accounts
Content-Type: application/json
```

**Body:**
```json
{
  "account_name": "Mi Empresa",
  "contact_name": "Juan Pérez",
  "contact_email": "juan@empresa.com",
  "contact_phone": "+56912345678",
  "plan_type": "credit_based",
  "initial_credits": 100.0
}
```

**Response:**
```json
{
  "success": true,
  "account_id": "account-abc123",
  "message": "Account created successfully"
}
```

---

### Obtener cuenta
```http
GET /api/v1/accounts/{account_id}
```

**Response:**
```json
{
  "account_id": "retail_express",
  "account_name": "Retail Express Corp",
  "plan_type": "credit_based",
  "status": "active",
  "credit_balance": 150.50,
  "credit_used": 49.50,
  "created_at": "2025-10-01T10:00:00"
}
```

---

### Obtener balance
```http
GET /api/v1/accounts/{account_id}/balance
```

**Response:**
```json
{
  "account_id": "retail_express",
  "plan_type": "credit_based",
  "credit_balance": 150.50,
  "credit_available": 145.30,
  "credit_reserved": 5.20,
  "credit_used": 49.50
}
```

---

### Recargar créditos
```http
POST /api/v1/accounts/{account_id}/topup
Content-Type: application/json
```

**Body:**
```json
{
  "credits": 100.0
}
```

**Response:**
```json
{
  "success": true,
  "new_balance": 250.50,
  "amount_added": 100.0
}
```

---

### Obtener todas las cuentas
```http
GET /api/v1/accounts?limit=50&skip=0
```

**Response:**
```json
{
  "accounts": [
    {
      "account_id": "retail_express",
      "account_name": "Retail Express Corp",
      "status": "active",
      "credit_balance": 150.50
    }
  ],
  "total": 1
}
```

---

### Suspender cuenta
```http
PUT /api/v1/accounts/{account_id}/suspend
```

---

### Activar cuenta
```http
PUT /api/v1/accounts/{account_id}/activate
```

---

### Obtener transacciones
```http
GET /api/v1/accounts/{account_id}/transactions?limit=50&skip=0
```

**Response:**
```json
{
  "transactions": [
    {
      "transaction_id": "txn_abc123",
      "type": "topup_credits",
      "amount": 100.0,
      "cost": 10000,
      "description": "Recarga de créditos",
      "created_at": "2025-10-25T10:00:00"
    }
  ],
  "total": 1
}
```

---

## Batches (Campañas)

### ✨ Crear batch desde Excel
```http
POST /api/v1/batches/excel/create
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: Excel file (.xlsx, .xls)
- `account_id`: ID de la cuenta
- `batch_name`: Nombre del batch (opcional)
- `batch_description`: Descripción (opcional)
- `allow_duplicates`: boolean (default: false)
- `processing_type`: "basic" | "acquisition" (default: "basic")
- `dias_fecha_limite`: número de días para calcular fecha límite (opcional)

**Response:**
```json
{
  "success": true,
  "batch_id": "batch-2025-10-25-144129-862530",
  "batch_name": "Testing GG Group",
  "total_debtors": 12,
  "total_jobs": 12,
  "estimated_cost": 5.64,
  "duplicates_found": 0,
  "created_at": "2025-10-25T17:41:29.895169"
}
```

---

### Vista previa de Excel
```http
POST /api/v1/batches/excel/preview
Content-Type: multipart/form-data
```

**Form Data:**
- `file`: Excel file
- `account_id`: ID de la cuenta

**Response:**
```json
{
  "success": true,
  "filename": "contactos.xlsx",
  "preview": {
    "total_rows": 12,
    "valid_rows": 12,
    "invalid_rows": 0,
    "duplicates": 0,
    "estimated_cost": 5.64
  }
}
```

---

### Listar batches
```http
GET /api/v1/batches?account_id={account_id}&limit=50&skip=0
```

**Response:**
```json
{
  "batches": [
    {
      "_id": "68fd0cdc8ac7d47a518bc017",
      "batch_id": "batch-2025-10-25-144604-615037",
      "name": "Testing GG Group",
      "account_id": "retail_express",
      "total_jobs": 12,
      "pending_jobs": 12,
      "completed_jobs": 0,
      "failed_jobs": 0,
      "is_active": true,
      "created_at": "2025-10-25T17:46:04.648000"
    }
  ],
  "total": 1
}
```

---

### Obtener batch
```http
GET /api/v1/batches/{batch_id}
```

**Nota:** `batch_id` puede ser el ID personalizado (`batch-2025-10-25-144604-615037`) o el ObjectId de MongoDB (`68fd0cdc8ac7d47a518bc017`)

**Response:**
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

---

### Obtener resumen de batch
```http
GET /api/v1/batches/{batch_id}/summary
```

**Response:**
```json
{
  "batch_id": "batch-2025-10-25-144604-615037",
  "name": "Testing GG Group",
  "status": "active",
  "total_jobs": 12,
  "pending_jobs": 12,
  "completed_jobs": 0,
  "completion_rate": 0.0,
  "total_cost": 0.0,
  "total_minutes": 0.0,
  "hourly_stats": []
}
```

---

### 🔄 Actualizar batch (PAUSAR/REANUDAR)
```http
PATCH /api/v1/batches/{batch_id}
Content-Type: application/json
```

**Body (Pausar):**
```json
{
  "is_active": false
}
```

**Body (Reanudar):**
```json
{
  "is_active": true
}
```

**Body (Actualizar múltiples campos):**
```json
{
  "is_active": false,
  "name": "Campaña Actualizada",
  "description": "Nueva descripción",
  "priority": 2
}
```

**Response:**
```json
{
  "success": true,
  "message": "Batch paused",
  "batch_id": "68fd0cdc8ac7d47a518bc017",
  "updated_fields": ["is_active", "updated_at"]
}
```

---

### ⏸️ Pausar batch (Legacy)
```http
PUT /api/v1/batches/{batch_id}/pause
```

**Nota:** Usar `PATCH /api/v1/batches/{batch_id}` es preferible

---

### ▶️ Reanudar batch (Legacy)
```http
PUT /api/v1/batches/{batch_id}/resume
```

---

### 🚫 Cancelar batch (permanente)
```http
POST /api/v1/batches/{batch_id}/cancel?reason=Motivo+de+cancelación
```

**Response:**
```json
{
  "success": true,
  "message": "Batch cancelled successfully",
  "reason": "Motivo de cancelación"
}
```

**Diferencias entre Pause y Cancel:**
- **Pause:** Temporal, se puede reanudar, jobs quedan pendientes
- **Cancel:** Permanente, marca jobs como cancelados, no se puede reanudar

---

### 🗑️ Eliminar batch
```http
DELETE /api/v1/batches/{batch_id}?delete_jobs=false
```

**Query Parameters:**
- `delete_jobs`: `true` para eliminar jobs, `false` para solo cancelarlos (default: false)

**Response:**
```json
{
  "success": true,
  "message": "Batch deleted"
}
```

---

### Obtener jobs de un batch
```http
GET /api/v1/batches/{batch_id}/jobs?status=pending&limit=50&skip=0
```

**Query Parameters:**
- `status`: Filtrar por estado (opcional)
- `limit`: Límite de resultados (default: 100)
- `skip`: Offset para paginación (default: 0)

**Response:**
```json
{
  "jobs": [
    {
      "_id": "68fd0cdc8ac7d47a518bc018",
      "job_id": "job-abc123",
      "batch_id": "batch-2025-10-25-144604-615037",
      "status": "pending",
      "contact": {
        "name": "Juan Pérez",
        "dni": "12345678-9",
        "phones": ["+56912345678"]
      },
      "attempts": 0,
      "created_at": "2025-10-25T17:46:04.648000"
    }
  ],
  "total": 12
}
```

---

## Jobs (Llamadas Individuales)

### Listar jobs
```http
GET /api/v1/jobs?status=pending&limit=50&skip=0
```

**Query Parameters:**
- `status`: pending | in_progress | completed | failed | cancelled
- `limit`: número de resultados
- `skip`: offset para paginación

**Response:**
```json
{
  "jobs": [...],
  "total": 100
}
```

---

### Obtener job
```http
GET /api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "_id": "68fd0cdc8ac7d47a518bc018",
  "job_id": "job-abc123",
  "batch_id": "batch-2025-10-25-144604-615037",
  "account_id": "retail_express",
  "status": "pending",
  "contact": {
    "name": "Juan Pérez",
    "dni": "12345678-9",
    "phones": ["+56912345678"],
    "next_phone_index": 0
  },
  "payload": {
    "debt_amount": 1500.0,
    "due_date": "2025-11-30",
    "company_name": "Mi Empresa"
  },
  "attempts": 0,
  "max_attempts": 3,
  "estimated_cost": 0.47,
  "created_at": "2025-10-25T17:46:04.648000"
}
```

---

### ♻️ Reintentar job
```http
PUT /api/v1/jobs/{job_id}/retry
```

**Response:**
```json
{
  "success": true,
  "message": "Job will be retried"
}
```

---

### 🗑️ Cancelar/Eliminar job
```http
DELETE /api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled"
}
```

**Nota:** Este endpoint ELIMINA el job. Si solo quieres cancelarlo sin eliminar, el job debe estar en estado `pending` o `scheduled`.

---

## Dashboard & Reportes

### Estadísticas generales
```http
GET /api/v1/dashboard/stats?account_id={account_id}
```

**Response:**
```json
{
  "total_batches": 12,
  "active_batches": 8,
  "total_jobs": 150,
  "pending_jobs": 50,
  "completed_jobs": 80,
  "failed_jobs": 20,
  "total_cost": 47.50,
  "total_minutes": 316.67
}
```

---

### Overview del dashboard
```http
GET /api/v1/dashboard/overview?account_id={account_id}
```

**Response:**
```json
{
  "account": {
    "account_id": "retail_express",
    "credit_balance": 150.50
  },
  "batches": {
    "total": 12,
    "active": 8,
    "paused": 2,
    "completed": 2
  },
  "jobs": {
    "total": 150,
    "pending": 50,
    "in_progress": 10,
    "completed": 80,
    "failed": 10
  },
  "costs": {
    "total_spent": 47.50,
    "total_minutes": 316.67,
    "average_per_call": 0.59
  },
  "recent_activity": []
}
```

---

### Historial de llamadas
```http
GET /api/v1/calls/history?account_id={account_id}&limit=50&skip=0
```

**Response:**
```json
{
  "calls": [
    {
      "call_id": "call-abc123",
      "job_id": "job-xyz789",
      "batch_id": "batch-2025-10-25-144604-615037",
      "contact_name": "Juan Pérez",
      "phone": "+56912345678",
      "status": "ended",
      "duration_ms": 45000,
      "cost": 0.47,
      "created_at": "2025-10-25T10:00:00"
    }
  ],
  "total": 100
}
```

---

## Use Cases

### Listar casos de uso disponibles
```http
GET /api/v1/use-cases
```

**Response:**
```json
{
  "use_cases": [
    {
      "id": "debt_collection",
      "name": "Cobranza de Deudas",
      "description": "Llamadas automáticas para recordar pagos pendientes"
    },
    {
      "id": "marketing",
      "name": "Marketing",
      "description": "Campañas de marketing y promociones"
    }
  ]
}
```

---

### Crear batch para Chile (por caso de uso)
```http
POST /api/v1/batches/chile/{use_case}
Content-Type: multipart/form-data
```

**Path Parameters:**
- `use_case`: debt_collection | marketing

---

### Crear batch para Argentina (por caso de uso)
```http
POST /api/v1/batches/argentina/{use_case}
Content-Type: multipart/form-data
```

---

## 📊 Estados de Batch

| Estado | Descripción |
|--------|-------------|
| `active` | Batch activo, ejecutando llamadas |
| `paused` | Batch pausado temporalmente |
| `completed` | Batch completado (todos los jobs procesados) |
| `cancelled` | Batch cancelado permanentemente |

---

## 📊 Estados de Job

| Estado | Descripción |
|--------|-------------|
| `pending` | Job esperando ser ejecutado |
| `scheduled` | Job programado para fecha futura |
| `in_progress` | Job siendo procesado |
| `completed` | Job completado exitosamente |
| `done` | Alias de completed |
| `failed` | Job falló después de reintentos |
| `suspended` | Job suspendido por falta de créditos |
| `cancelled` | Job cancelado (batch pausado/eliminado) |

---

## 🔑 Notas Importantes

### IDs de Batch
Los endpoints aceptan **ambos formatos** de ID:
- **ObjectId de MongoDB**: `68fd0cdc8ac7d47a518bc017`
- **ID personalizado**: `batch-2025-10-25-144604-615037`

Esto permite flexibilidad en el frontend.

### Pausar vs Cancelar vs Eliminar

| Acción | Endpoint | Efecto en Jobs | Reversible |
|--------|----------|----------------|------------|
| **Pausar** | `PATCH /batches/{id}` con `is_active: false` | Quedan pendientes | ✅ Sí |
| **Cancelar** | `POST /batches/{id}/cancel` | Se marcan como cancelled | ❌ No |
| **Eliminar** | `DELETE /batches/{id}` | Se cancelan o eliminan | ❌ No |

### Paginación
Todos los endpoints de listado soportan:
- `limit`: Número de resultados (default: 50-100)
- `skip`: Offset para paginación (default: 0)

Ejemplo:
```http
GET /api/v1/batches?limit=20&skip=40
```
Esto retorna 20 batches, saltando los primeros 40 (página 3).

---

## 🚀 Ejemplos de Uso Común

### 1. Crear campaña desde Excel
```javascript
const formData = new FormData();
formData.append('file', excelFile);
formData.append('account_id', 'retail_express');
formData.append('batch_name', 'Campaña Octubre');
formData.append('allow_duplicates', 'false');

const response = await fetch('http://localhost:8000/api/v1/batches/excel/create', {
  method: 'POST',
  body: formData
});
```

### 2. Pausar una campaña
```javascript
const response = await fetch(`http://localhost:8000/api/v1/batches/${batchId}`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ is_active: false })
});
```

### 3. Eliminar un job específico
```javascript
const response = await fetch(`http://localhost:8000/api/v1/jobs/${jobId}`, {
  method: 'DELETE'
});
```

### 4. Obtener estadísticas del dashboard
```javascript
const response = await fetch(
  `http://localhost:8000/api/v1/dashboard/overview?account_id=retail_express`
);
const data = await response.json();
```

---

## 📝 Response Codes

| Code | Significado |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (datos inválidos) |
| 404 | Not Found (recurso no encontrado) |
| 405 | Method Not Allowed |
| 500 | Internal Server Error |
| 503 | Service Unavailable (database down) |

---

## 🔗 URLs de Documentación

- Documentación interactiva (Swagger): `http://localhost:8000/docs`
- Documentación alternativa (ReDoc): `http://localhost:8000/redoc`

---

**Última actualización:** 25 de Octubre, 2025  
**Versión API:** 1.0.0  
**Base URL:** `http://localhost:8000/api/v1`
