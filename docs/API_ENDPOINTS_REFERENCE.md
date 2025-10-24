# 📡 API Endpoints Reference - Speech AI Backend

**Versión:** 1.0.0  
**Base URL:** `http://localhost:8000`  
**Fecha:** Octubre 2025

---

## 📋 Índice

1. [🏠 Sistema](#-sistema)
2. [👤 Cuentas (Accounts)](#-cuentas-accounts)
3. [📦 Campañas/Batches](#-campañasbatches)
4. [📞 Jobs (Llamadas Individuales)](#-jobs-llamadas-individuales)
5. [📊 Dashboard](#-dashboard)
6. [📜 Historial de Llamadas](#-historial-de-llamadas)
7. [🌍 Endpoints Específicos por País](#-endpoints-específicos-por-país)

---

## 🏠 Sistema

### `GET /`
**Descripción:** Endpoint raíz con información de la API.

**Response:**
```json
{
  "message": "Speech AI Call Tracking API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

---

### `GET /health`
**Descripción:** Health check para monitoreo.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-24T10:30:00"
}
```

---

## 👤 Cuentas (Accounts)

### `POST /api/v1/accounts`
**Descripción:** Crear nueva cuenta de cliente.

**Request Body:**
```json
{
  "account_name": "Empresa XYZ",           // REQUIRED
  "contact_name": "María González",        // REQUIRED
  "contact_email": "maria@empresa.cl",     // REQUIRED
  "contact_phone": "+56987654321",         // OPTIONAL
  "plan_type": "credit_based",             // OPTIONAL (default: "credit_based")
  "initial_credits": 1000,                 // OPTIONAL (si plan es credit_based)
  "initial_minutes": 500,                  // OPTIONAL (si plan es minutes_based)
  "features": {                            // OPTIONAL
    "max_concurrent_calls": 5
  },
  "settings": {                            // OPTIONAL
    "timezone": "America/Santiago"
  }
}
```

**Response:**
```json
{
  "success": true,
  "account": {
    "_id": "...",
    "account_id": "acc-a1b2c3d4e5f6",     // Auto-generado
    "account_name": "Empresa XYZ",
    "contact_name": "María González",
    "contact_email": "maria@empresa.cl",
    "contact_phone": "+56987654321",
    "plan_type": "credit_based",
    "status": "active",
    "balance": {
      "credits": 1000,
      "minutes": 0
    },
    "features": {
      "max_concurrent_calls": 5
    },
    "settings": {
      "timezone": "America/Santiago"
    },
    "created_at": "2025-10-24T10:30:00"
  }
}
```

**Notas:**
- ✅ `account_id` se genera automáticamente en el backend
- ✅ `contact_name`, `contact_email`, `contact_phone` son campos del contacto
- ✅ `features` y `settings` son diccionarios opcionales
- ⚠️ NO enviar `call_settings` aquí (eso va en batches)

---

### `GET /api/v1/accounts`
**Descripción:** Listar todas las cuentas.

**Query Parameters:**
- `limit` (int, default: 100, max: 1000) - Número de resultados
- `skip` (int, default: 0) - Offset para paginación

**Response:**
```json
[
  {
    "account_id": "acc-a1b2c3d4e5f6",
    "account_name": "Empresa XYZ",
    "status": "active",
    "plan_type": "credit_based",
    "balance": {
      "credits": 1000,
      "minutes": 0
    },
    "created_at": "2025-10-24T10:30:00"
  }
]
```

---

### `GET /api/v1/accounts/{account_id}`
**Descripción:** Obtener detalles de una cuenta específica.

**Path Parameters:**
- `account_id` (string) - ID de la cuenta

**Response:**
```json
{
  "account_id": "acc-a1b2c3d4e5f6",
  "account_name": "Empresa XYZ",
  "contact_name": "María González",
  "contact_email": "maria@empresa.cl",
  "status": "active",
  "plan_type": "credit_based",
  "balance": {
    "credits": 850,
    "minutes": 0
  },
  "features": {
    "max_concurrent_calls": 5
  },
  "created_at": "2025-10-24T10:30:00"
}
```

---

### `GET /api/v1/accounts/{account_id}/balance`
**Descripción:** Obtener balance actual de la cuenta.

**Response:**
```json
{
  "account_id": "acc-a1b2c3d4e5f6",
  "credits": 850,
  "minutes": 0,
  "plan_type": "credit_based"
}
```

---

### `POST /api/v1/accounts/{account_id}/topup`
**Descripción:** Recargar créditos o minutos a una cuenta.

**Request Body:**
```json
{
  "credits": 500,    // OPTIONAL - para plan credit_based
  "minutes": 250     // OPTIONAL - para plan minutes_based
}
```

**Response:**
```json
{
  "success": true,
  "message": "Recarga exitosa",
  "new_balance": {
    "credits": 1350,
    "minutes": 0
  }
}
```

---

### `GET /api/v1/accounts/{account_id}/stats`
**Descripción:** Obtener estadísticas de la cuenta.

**Response:**
```json
{
  "account_id": "acc-a1b2c3d4e5f6",
  "total_batches": 15,
  "active_batches": 3,
  "total_calls": 450,
  "successful_calls": 380,
  "failed_calls": 70,
  "success_rate": 84.4,
  "total_cost": 150.0
}
```

---

### `PUT /api/v1/accounts/{account_id}/suspend`
**Descripción:** Suspender una cuenta.

**Response:**
```json
{
  "success": true,
  "message": "Cuenta suspendida",
  "account_id": "acc-a1b2c3d4e5f6",
  "status": "suspended"
}
```

---

### `PUT /api/v1/accounts/{account_id}/activate`
**Descripción:** Reactivar una cuenta suspendida.

**Response:**
```json
{
  "success": true,
  "message": "Cuenta activada",
  "account_id": "acc-a1b2c3d4e5f6",
  "status": "active"
}
```

---

### `GET /api/v1/accounts/{account_id}/batches`
**Descripción:** Listar todos los batches de una cuenta.

**Query Parameters:**
- `is_active` (bool, optional) - Filtrar por estado activo/inactivo
- `limit` (int, default: 100)
- `skip` (int, default: 0)

**Response:**
```json
[
  {
    "batch_id": "batch-20251024-a1b2c3d4",
    "name": "Campaña Octubre",
    "status": "active",
    "total_jobs": 100,
    "completed_jobs": 45,
    "pending_jobs": 55,
    "created_at": "2025-10-24T10:30:00"
  }
]
```

---

### `GET /api/v1/accounts/{account_id}/transactions`
**Descripción:** Historial de transacciones (recargas, consumos).

**Query Parameters:**
- `limit` (int, default: 100)
- `skip` (int, default: 0)

**Response:**
```json
[
  {
    "transaction_id": "txn-...",
    "type": "topup",
    "amount": 500,
    "currency": "credits",
    "timestamp": "2025-10-24T10:00:00",
    "description": "Recarga manual"
  },
  {
    "transaction_id": "txn-...",
    "type": "usage",
    "amount": -150,
    "currency": "credits",
    "timestamp": "2025-10-24T11:00:00",
    "description": "Batch: Campaña Octubre"
  }
]
```

---

### `GET /api/v1/accounts/{account_id}/summary`
**Descripción:** Resumen completo de la cuenta con todas las métricas.

**Response:**
```json
{
  "account": {
    "account_id": "acc-a1b2c3d4e5f6",
    "account_name": "Empresa XYZ",
    "status": "active"
  },
  "balance": {
    "credits": 850,
    "minutes": 0
  },
  "stats": {
    "total_batches": 15,
    "total_calls": 450,
    "success_rate": 84.4
  },
  "recent_batches": [...],
  "recent_transactions": [...]
}
```

---

## 📦 Campañas/Batches

### `POST /api/v1/batches`
**Descripción:** Crear nuevo batch/campaña de llamadas.

**Request Body:**
```json
{
  "account_id": "acc-a1b2c3d4e5f6",        // REQUIRED
  "name": "Campaña Octubre",               // REQUIRED
  "description": "Cobranza mes octubre",   // OPTIONAL (default: "")
  "priority": 1,                           // OPTIONAL (default: 1)
  "call_settings": {                       // OPTIONAL
    "max_call_duration": 300,              // Segundos (default: 300)
    "ring_timeout": 30,                    // Segundos (default: 30)
    "max_attempts": 3,                     // Reintentos (default: 3)
    "retry_delay_hours": 24,               // Horas entre reintentos (default: 24)
    "allowed_hours": {
      "start": "09:00",
      "end": "18:00"
    },
    "days_of_week": [1, 2, 3, 4, 5],      // 1=Lun, 7=Dom
    "timezone": "America/Santiago"
  }
}
```

**Response:**
```json
{
  "success": true,
  "batch": {
    "_id": "...",
    "batch_id": "batch-20251024-a1b2c3d4",  // Auto-generado
    "account_id": "acc-a1b2c3d4e5f6",
    "name": "Campaña Octubre",
    "description": "Cobranza mes octubre",
    "priority": 1,
    "call_settings": { ... },
    "is_active": true,
    "total_jobs": 0,
    "pending_jobs": 0,
    "completed_jobs": 0,
    "created_at": "2025-10-24T10:30:00"
  }
}
```

**Notas:**
- ✅ `batch_id` se genera automáticamente
- ✅ `call_settings` es completamente opcional (usa defaults del worker si no se envía)
- ⚠️ NO incluir `script_content`, `voice_settings`, `schedule_type` (no se usan actualmente)

---

### `GET /api/v1/batches`
**Descripción:** Listar batches con filtros.

**Query Parameters:**
- `account_id` (string, optional) - Filtrar por cuenta
- `is_active` (bool, optional) - Filtrar por estado
- `limit` (int, default: 100, max: 1000)
- `skip` (int, default: 0)

**Response:**
```json
[
  {
    "batch_id": "batch-20251024-a1b2c3d4",
    "account_id": "acc-a1b2c3d4e5f6",
    "name": "Campaña Octubre",
    "is_active": true,
    "total_jobs": 100,
    "pending_jobs": 55,
    "completed_jobs": 45,
    "created_at": "2025-10-24T10:30:00"
  }
]
```

---

### `GET /api/v1/batches/{batch_id}`
**Descripción:** Obtener detalles de un batch.

**Response:**
```json
{
  "batch_id": "batch-20251024-a1b2c3d4",
  "account_id": "acc-a1b2c3d4e5f6",
  "name": "Campaña Octubre",
  "description": "Cobranza mes octubre",
  "priority": 1,
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
  },
  "is_active": true,
  "total_jobs": 100,
  "pending_jobs": 55,
  "completed_jobs": 45,
  "failed_jobs": 0,
  "total_cost": 15.0,
  "total_minutes": 75.5,
  "created_at": "2025-10-24T10:30:00"
}
```

---

### `GET /api/v1/batches/{batch_id}/summary`
**Descripción:** Resumen con estadísticas detalladas del batch.

**Response:**
```json
{
  "batch_id": "batch-20251024-a1b2c3d4",
  "name": "Campaña Octubre",
  "stats": {
    "total_jobs": 100,
    "pending_jobs": 55,
    "completed_jobs": 45,
    "failed_jobs": 0,
    "success_rate": 100.0,
    "completion_rate": 45.0
  },
  "costs": {
    "total_cost": 15.0,
    "total_minutes": 75.5,
    "estimated_cost": 30.0
  }
}
```

---

### `GET /api/v1/batches/{batch_id}/status`
**Descripción:** Status en tiempo real del batch.

**Response:**
```json
{
  "batch_id": "batch-20251024-a1b2c3d4",
  "is_active": true,
  "status": "in_progress",
  "progress": {
    "total": 100,
    "pending": 55,
    "in_progress": 5,
    "completed": 40,
    "failed": 0
  },
  "next_execution": "2025-10-25T09:00:00"
}
```

---

### `GET /api/v1/batches/{batch_id}/jobs`
**Descripción:** Listar jobs/llamadas del batch.

**Query Parameters:**
- `status` (string, optional) - Filtrar por estado: pending, in_progress, completed, failed
- `limit` (int, default: 100)
- `skip` (int, default: 0)

**Response:**
```json
[
  {
    "job_id": "job-...",
    "batch_id": "batch-20251024-a1b2c3d4",
    "status": "completed",
    "contact": {
      "name": "Juan Pérez",
      "phone": "+56912345678"
    },
    "attempts": 1,
    "last_call_duration": 65,
    "cost": 0.15,
    "created_at": "2025-10-24T10:30:00",
    "completed_at": "2025-10-24T10:31:05"
  }
]
```

---

### `POST /api/v1/batches/{batch_id}/upload`
**Descripción:** Subir contactos a un batch existente (CSV/Excel).

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (UploadFile)

**CSV Format Example:**
```csv
nombre,telefono_1,telefono_2,monto_deuda
Juan Pérez,+56912345678,+56987654321,50000
María González,+56911111111,,75000
```

**Response:**
```json
{
  "success": true,
  "batch_id": "batch-20251024-a1b2c3d4",
  "jobs_created": 2,
  "contacts_processed": 2,
  "errors": []
}
```

---

### `POST /api/v1/batches/excel/preview`
**Descripción:** Vista previa de un Excel antes de crear batch.

**Request:**
- Content-Type: `multipart/form-data`
- Field: `file` (UploadFile)

**Response:**
```json
{
  "success": true,
  "preview": {
    "total_rows": 100,
    "columns": ["nombre", "telefono_1", "telefono_2", "monto_deuda"],
    "sample_rows": [
      {
        "nombre": "Juan Pérez",
        "telefono_1": "+56912345678",
        "telefono_2": "+56987654321",
        "monto_deuda": "50000"
      }
    ],
    "detected_variables": ["nombre", "monto_deuda"]
  }
}
```

---

### `POST /api/v1/batches/excel/create`
**Descripción:** Crear batch desde Excel (crea batch + jobs en un solo paso).

**Request:**
- Content-Type: `multipart/form-data`
- Fields:
  - `file` (File) - **REQUIRED** - Excel con contactos (.xlsx, .xls)
  - `account_id` (string) - **REQUIRED** - ID de la cuenta
  - `batch_name` (string) - **OPTIONAL** - Nombre del batch
  - `batch_description` (string) - **OPTIONAL** - Descripción
  - `allow_duplicates` (boolean) - **OPTIONAL** - Default: false
  - `processing_type` (string) - **OPTIONAL** - Default: "basic" ("basic" o "acquisition")
  - `dias_fecha_limite` (number) - **OPTIONAL** - Días para calcular fecha_limite
  - `dias_fecha_maxima` (number) - **OPTIONAL** - Días para calcular fecha_maxima
  - `call_settings_json` (string) - **OPTIONAL** - JSON string con call_settings

**Ejemplo de call_settings_json:**
```json
{
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
```

**IMPORTANTE:** El campo `call_settings_json` debe ser un **string JSON**, no un objeto. 
Para enviarlo desde el frontend:
```typescript
formData.append('call_settings_json', JSON.stringify(callSettings));
```

**Response:**
```json
{
  "success": true,
  "batch_id": "batch-20251024-a1b2c3d4",
  "batch_name": "Batch desde Excel",
  "jobs_created": 100,
  "contacts_processed": 100,
  "duplicates_skipped": 5
}
```

---

### `PUT /api/v1/batches/{batch_id}/pause`
**Descripción:** Pausar ejecución del batch.

**Response:**
```json
{
  "success": true,
  "message": "Batch pausado",
  "batch_id": "batch-20251024-a1b2c3d4",
  "is_active": false
}
```

---

### `PUT /api/v1/batches/{batch_id}/resume`
**Descripción:** Reanudar batch pausado.

**Response:**
```json
{
  "success": true,
  "message": "Batch reanudado",
  "batch_id": "batch-20251024-a1b2c3d4",
  "is_active": true
}
```

---

### `POST /api/v1/batches/{batch_id}/cancel`
**Descripción:** Cancelar batch (marca todos los jobs como cancelados).

**Response:**
```json
{
  "success": true,
  "message": "Batch cancelado",
  "batch_id": "batch-20251024-a1b2c3d4",
  "jobs_cancelled": 55
}
```

---

### `DELETE /api/v1/batches/{batch_id}`
**Descripción:** Eliminar batch y todos sus jobs.

**Response:**
```json
{
  "success": true,
  "message": "Batch eliminado",
  "batch_id": "batch-20251024-a1b2c3d4",
  "jobs_deleted": 100
}
```

---

## 📞 Jobs (Llamadas Individuales)

### `GET /api/v1/jobs`
**Descripción:** Listar jobs con filtros.

**Query Parameters:**
- `batch_id` (string, optional) - Filtrar por batch
- `account_id` (string, optional) - Filtrar por cuenta
- `status` (string, optional) - pending, in_progress, completed, failed
- `limit` (int, default: 100)
- `skip` (int, default: 0)

**Response:**
```json
[
  {
    "job_id": "job-...",
    "batch_id": "batch-20251024-a1b2c3d4",
    "account_id": "acc-a1b2c3d4e5f6",
    "status": "completed",
    "contact": {
      "name": "Juan Pérez",
      "phone": "+56912345678"
    },
    "attempts": 1,
    "cost": 0.15,
    "created_at": "2025-10-24T10:30:00"
  }
]
```

---

### `GET /api/v1/jobs/{job_id}`
**Descripción:** Obtener detalles de un job específico.

**Response:**
```json
{
  "job_id": "job-...",
  "batch_id": "batch-20251024-a1b2c3d4",
  "account_id": "acc-a1b2c3d4e5f6",
  "status": "completed",
  "contact": {
    "name": "Juan Pérez",
    "phone": "+56912345678",
    "secondary_phone": "+56987654321"
  },
  "variables": {
    "nombre": "Juan Pérez",
    "monto_deuda": "50000"
  },
  "call_history": [
    {
      "attempt": 1,
      "call_id": "call-...",
      "status": "completed",
      "duration": 65,
      "cost": 0.15,
      "timestamp": "2025-10-24T10:30:00"
    }
  ],
  "attempts": 1,
  "max_attempts": 3,
  "total_cost": 0.15,
  "created_at": "2025-10-24T10:30:00",
  "completed_at": "2025-10-24T10:31:05"
}
```

---

### `PUT /api/v1/jobs/{job_id}/retry`
**Descripción:** Reintentar un job manualmente.

**Response:**
```json
{
  "success": true,
  "message": "Job marcado para reintentar",
  "job_id": "job-...",
  "status": "pending",
  "next_try_at": "2025-10-24T12:00:00"
}
```

---

### `DELETE /api/v1/jobs/{job_id}`
**Descripción:** Eliminar un job específico.

**Response:**
```json
{
  "success": true,
  "message": "Job eliminado",
  "job_id": "job-..."
}
```

---

## 📊 Dashboard

### `GET /api/v1/dashboard/stats`
**Descripción:** Estadísticas generales del sistema.

**Response:**
```json
{
  "total_accounts": 25,
  "active_accounts": 22,
  "total_batches": 150,
  "active_batches": 12,
  "total_jobs": 5000,
  "pending_jobs": 500,
  "completed_jobs": 4200,
  "failed_jobs": 300,
  "success_rate": 93.3,
  "total_revenue": 1500.0
}
```

---

### `GET /api/v1/dashboard/overview`
**Descripción:** Vista general del dashboard con métricas clave.

**Response:**
```json
{
  "summary": {
    "total_accounts": 25,
    "active_batches": 12,
    "calls_today": 250,
    "success_rate_today": 88.0
  },
  "recent_activity": [
    {
      "type": "batch_created",
      "account_id": "acc-...",
      "batch_id": "batch-...",
      "timestamp": "2025-10-24T10:30:00"
    }
  ],
  "top_accounts": [
    {
      "account_id": "acc-...",
      "account_name": "Empresa XYZ",
      "total_calls": 450,
      "success_rate": 92.5
    }
  ]
}
```

---

## 📜 Historial de Llamadas

### `GET /api/v1/calls/history`
**Descripción:** Historial completo de llamadas con filtros.

**Query Parameters:**
- `account_id` (string, optional)
- `batch_id` (string, optional)
- `status` (string, optional) - completed, failed, no_answer
- `start_date` (datetime, optional)
- `end_date` (datetime, optional)
- `limit` (int, default: 100)
- `skip` (int, default: 0)

**Response:**
```json
[
  {
    "call_id": "call-...",
    "job_id": "job-...",
    "batch_id": "batch-20251024-a1b2c3d4",
    "account_id": "acc-a1b2c3d4e5f6",
    "contact": {
      "name": "Juan Pérez",
      "phone": "+56912345678"
    },
    "status": "completed",
    "duration": 65,
    "cost": 0.15,
    "recording_url": "https://...",
    "transcript": "...",
    "timestamp": "2025-10-24T10:30:00"
  }
]
```

---

## 🌍 Endpoints Específicos por País

### `POST /api/v1/batches/chile/{use_case}`
**Descripción:** Crear batch especializado para Chile según caso de uso.

**Path Parameters:**
- `use_case` (string) - Tipo de campaña: `debt_collection`, `marketing`, `surveys`, etc.

**Request Body:**
```json
{
  "account_id": "acc-a1b2c3d4e5f6",
  "batch_name": "Cobranza Chile Octubre",
  "contacts": [
    {
      "name": "Juan Pérez",
      "phone": "+56912345678",
      "variables": {
        "monto_deuda": "50000",
        "empresa": "Empresa XYZ"
      }
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "batch_id": "batch-20251024-chile-a1b2",
  "use_case": "debt_collection",
  "country": "chile",
  "jobs_created": 100,
  "estimated_cost": 30.0
}
```

---

### `POST /api/v1/batches/argentina/{use_case}`
**Descripción:** Crear batch especializado para Argentina según caso de uso.

**Path Parameters:**
- `use_case` (string) - Tipo de campaña

**Request Body:** (igual que Chile)

**Response:** (igual que Chile, con `"country": "argentina"`)

---

### `GET /api/v1/use-cases`
**Descripción:** Listar casos de uso disponibles por país.

**Response:**
```json
{
  "chile": [
    {
      "use_case": "debt_collection",
      "name": "Cobranza",
      "description": "Llamadas automatizadas para cobranza",
      "default_settings": {
        "timezone": "America/Santiago",
        "allowed_hours": {
          "start": "09:00",
          "end": "20:00"
        }
      }
    }
  ],
  "argentina": [...]
}
```

---

## 📝 Notas Importantes para el Frontend

### ✅ Campos Auto-generados (NO enviar en request)
- `account_id` → Generado por backend
- `batch_id` → Generado por backend
- `job_id` → Generado por backend
- `_id` → MongoDB ObjectId (interno)
- `created_at`, `updated_at` → Timestamps automáticos

### ✅ Campos Opcionales con Defaults
- `CreateAccountRequest.plan_type` → Default: `"credit_based"`
- `CreateAccountRequest.features` → Default: `null`
- `CreateAccountRequest.settings` → Default: `null`
- `CreateBatchRequest.description` → Default: `""`
- `CreateBatchRequest.priority` → Default: `1`
- `CreateBatchRequest.call_settings` → Default: `null` (worker usa defaults)

### ⚠️ Campos que NO se usan actualmente
- `script_content` (no está en BatchModel)
- `voice_settings` (no está en BatchModel)
- `schedule_type`, `scheduled_at`, `recurring_config` (no implementado)

### 📌 Estructura de `call_settings` (OPCIONAL)
```json
{
  "max_call_duration": 300,           // Segundos (default: 300)
  "ring_timeout": 30,                 // Segundos (default: 30)
  "max_attempts": 3,                  // Reintentos (default: 3)
  "retry_delay_hours": 24,            // Horas entre reintentos (default: 24)
  "allowed_hours": {                  // Horario permitido
    "start": "09:00",
    "end": "18:00"
  },
  "days_of_week": [1, 2, 3, 4, 5],   // 1=Lun, 7=Dom (default: [1,2,3,4,5])
  "timezone": "America/Santiago"      // Zona horaria (default: "America/Santiago")
}
```

**Si no se envía `call_settings`:** El worker usa valores hardcoded:
- `max_call_duration`: 300 seg
- `ring_timeout`: 30 seg
- `max_attempts`: 3
- `retry_delay_hours`: 30 (⚠️ no 24)
- `allowed_hours`: 09:00 - 20:00
- `days_of_week`: [1,2,3,4,5]
- `timezone`: "America/Santiago"

---

## 🔐 Autenticación
**Estado actual:** Sin autenticación implementada  
**TODO:** Implementar JWT tokens en futuro

---

## 🚀 Rate Limiting
**Estado actual:** Sin rate limiting  
**TODO:** Implementar límites por cuenta en futuro

---

## 📦 Paginación
**Patrón estándar:**
- `limit` (int, default: 100, max: 1000)
- `skip` (int, default: 0)

**Ejemplo:**
```
GET /api/v1/batches?limit=50&skip=100
```

---

## ❌ Manejo de Errores

**Formato estándar:**
```json
{
  "detail": "Mensaje de error descriptivo"
}
```

**Códigos HTTP:**
- `200` - Éxito
- `400` - Bad Request (parámetros inválidos)
- `404` - Not Found (recurso no existe)
- `422` - Unprocessable Entity (validación de Pydantic falló)
- `500` - Internal Server Error

---

**Fin del documento** 📄
