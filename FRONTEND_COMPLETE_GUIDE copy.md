# 📱 Guía Completa de la Aplicación SpeechAI - Frontend

**Fecha:** 16 Octubre 2025  
**Propósito:** Documentación exhaustiva de todas las pantallas, funcionalidades y endpoints esperados

---

## 🎯 Descripción General de la Aplicación

**SpeechAI** es una plataforma de gestión de campañas de llamadas automatizadas con IA. Permite a empresas gestionar:
- **Cuentas de clientes** con planes y créditos
- **Campañas (Batches)** de llamadas automatizadas
- **Jobs** (tareas individuales de llamadas)
- **Reportes** y analytics en tiempo real

---

## 🗺️ Mapa de Navegación

```
/
├── /login                 # Login (público)
└── / (protegido)          # Layout principal con sidebar
    ├── /dashboard         # Dashboard principal con métricas
    ├── /accounts          # Gestión de cuentas de empresa
    ├── /batches           # Lista de campañas de llamadas
    │   ├── /batches/:id   # Detalle de campaña específica
    │   └── /batches/new   # Wizard para crear nueva campaña
    ├── /jobs              # Lista de tareas de llamadas
    ├── /reports           # Reportes y analytics
    └── /test-api          # Página de testing de API
```

---

## 📄 PANTALLA 1: LOGIN PAGE

**Ruta:** `/login`  
**Archivo:** `src/pages/Auth/LoginPage.tsx`  
**Acceso:** Público

### Descripción:
Pantalla de autenticación para acceder al sistema.

### Funcionalidades:
1. **Login con email y password**
2. Validación de credenciales
3. Almacenamiento de token en localStorage
4. Redirección a /dashboard después del login exitoso

### Endpoints Esperados:

#### 🔵 POST `/api/v1/auth/login`
**Request:**
```json
{
  "email": "usuario@empresa.com",
  "password": "password123"
}
```

**Response exitoso (200):**
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user_123",
    "email": "usuario@empresa.com",
    "name": "Juan Pérez",
    "role": "admin",
    "permissions": ["read", "write", "admin"]
  }
}
```

**Response error (401):**
```json
{
  "success": false,
  "message": "Credenciales inválidas",
  "code": "INVALID_CREDENTIALS"
}
```

### Estado Actual:
⚠️ **Mock:** Actualmente usa autenticación mock (cualquier email/password funciona)  
🔧 **Pendiente:** Implementar endpoint real de autenticación

---

## 📄 PANTALLA 2: DASHBOARD

**Ruta:** `/dashboard`  
**Archivo:** `src/pages/Dashboard/DashboardPage.tsx`  
**Acceso:** Protegido (requiere login)

### Descripción:
Pantalla principal con métricas y overview del sistema. Muestra estadísticas en tiempo real de todas las operaciones.

### Componentes Visuales:

#### 1. **Cards de Métricas Principales** (4 cards en fila)
- 📞 **Jobs Hoy**: Total de llamadas procesadas hoy
- 📊 **Tasa de Éxito**: Porcentaje de llamadas exitosas
- 🏢 **Cuentas Activas**: Cuentas con estado ACTIVE
- ⏳ **Jobs Pendientes**: Llamadas en cola

#### 2. **Cards de Métricas Secundarias** (4 cards en segunda fila)
- 💰 **Revenue Hoy**: Ingresos del día actual
- ⏱️ **Minutos Usados**: Total de minutos consumidos
- ▶️ **Jobs en Progreso**: Llamadas actualmente en proceso
- ❌ **Jobs Fallidos Hoy**: Llamadas que fallaron hoy

#### 3. **Sección de Batches Recientes**
Lista de las últimas 5 campañas con:
- Nombre de la campaña
- Estado (RUNNING, PAUSED, COMPLETED, etc.)
- Progreso visual (barra de progreso)
- Estadísticas: completados/total
- Botón "Ver Detalle"

#### 4. **Gráfico de Actividad** (placeholder)
Visualización de actividad de llamadas en las últimas 24 horas

### Endpoints Esperados:

#### 🟢 GET `/api/v1/dashboard/stats`
**Implementado:** ✅ SÍ (actualizado a `/dashboard/overview`)

**Request:**
```http
GET /api/v1/dashboard/stats?account_id=acc_123
```

Query params opcionales:
- `account_id`: Filtrar por cuenta específica

**Response:**
```json
{
  "total_accounts": 25,
  "active_batches": 8,
  "total_jobs_today": 1234,
  "success_rate": 87.5,
  "total_minutes_used": 456.75,
  "revenue_today": 2345.50,
  "pending_jobs": 234,
  "in_progress_jobs": 12,
  "completed_jobs_today": 987,
  "failed_jobs_today": 135,
  "recent_batches": [
    {
      "_id": "batch_001",
      "batch_id": "batch-20251016-001",
      "name": "Campaña Cobranza Octubre",
      "status": "RUNNING",
      "progress": {
        "total": 1000,
        "completed": 450,
        "pending": 550
      }
    }
  ]
}
```

#### 🟢 GET `/api/v1/batches`
**Implementado:** ✅ SÍ

Para obtener los últimos 5 batches:
```http
GET /api/v1/batches?limit=5&sort=-created_at
```

**Response:**
```json
[
  {
    "_id": "batch_001",
    "batch_id": "batch-20251016-001",
    "account_id": "acc_123",
    "name": "Campaña Cobranza Octubre",
    "status": "RUNNING",
    "total_jobs": 1000,
    "pending_jobs": 550,
    "completed_jobs": 450,
    "failed_jobs": 50,
    "created_at": "2025-10-16T10:30:00Z"
  }
]
```

### Frecuencia de Actualización:
- Métricas principales: Cada 30 segundos (auto-refresh)
- Batches recientes: Cada 30 segundos

### Estado Actual:
✅ **Implementado:** Endpoints `/dashboard/overview` y `/batches` funcionando  
⚠️ **Pendiente:** Integrar refresh automático en frontend

---

## 📄 PANTALLA 3: ACCOUNTS (CUENTAS)

**Ruta:** `/accounts`  
**Archivo:** `src/pages/Accounts/AccountsPage.tsx`  
**Acceso:** Protegido

### Descripción:
Gestión completa de cuentas de clientes empresariales. Permite crear, editar, suspender y activar cuentas.

### Componentes Visuales:

#### 1. **Header con Botón de Acción**
- Título: "Cuentas de Empresa"
- Botón: "+ Nueva Cuenta"

#### 2. **Stats Cards** (4 cards)
- 🏢 **Total Cuentas**: Cantidad total
- ✅ **Activas**: Cuentas con status ACTIVE
- ⏸️ **Suspendidas**: Cuentas con status SUSPENDED
- 💰 **Créditos Totales**: Suma de créditos de todas las cuentas

#### 3. **Tabla de Cuentas**
Columnas:
- **Empresa**: Nombre de la cuenta + email de contacto
- **Plan**: minutes_based o credit_based
- **Balance**: Créditos/minutos disponibles
- **Estado**: Badge con color (ACTIVE=verde, SUSPENDED=rojo, INACTIVE=gris)
- **Creado**: Fecha de creación
- **Acciones**: Botones "Ver Detalle", "Suspender/Activar"

### Modales:

#### **Modal: Crear Cuenta** (`CreateAccountModal`)
Formulario con 4 secciones:

**Sección 1: Información de la Empresa**
- Nombre de la Empresa (requerido)
- Nombre de Contacto (requerido)
- Email de Contacto (requerido, validación email)
- Teléfono de Contacto (opcional)

**Sección 2: Plan y Facturación**
- Tipo de Plan: Radio buttons
  - Por Créditos (credit_based)
  - Por Minutos (minutes_based)
- Créditos Iniciales / Minutos Iniciales (según tipo seleccionado)

**Sección 3: Límites Técnicos**
- Llamadas Concurrentes Máximas (número, 1-50)
  - Define cuántas llamadas simultáneas puede hacer esta cuenta

**Sección 4: Configuración Regional**
- Zona Horaria por Defecto (select)
  - Esta será la zona horaria predeterminada para las campañas de esta cuenta

> ✅ **CORREGIDO**: Ya NO incluye call_settings (horarios, reintentos) ni features extra (voice cloning, analytics)
> Esas configuraciones ahora van en el Batch/Campaña donde corresponden.

#### **Modal: Detalle de Cuenta** (`AccountDetailModal`)
Pestañas:
1. **Información**: Datos generales de la cuenta
2. **Balance**: Créditos/minutos, historial de recargas
3. **Batches**: Lista de campañas de esta cuenta
4. **Transacciones**: Historial de movimientos

### Endpoints Esperados:

#### 🟢 GET `/api/v1/accounts`
**Implementado:** ✅ SÍ

**Response:**
```json
[
  {
    "_id": "acc_001",
    "account_id": "acc-chile-001",
    "account_name": "Empresa ABC",
    "contact_name": "Juan Pérez",
    "contact_email": "contacto@empresaabc.cl",
    "contact_phone": "+56912345678",
    "status": "ACTIVE",
    "plan_type": "credit_based",
    "balance": {
      "minutes": 0,
      "credits": 5000,
      "total_spent": 1250.50
    },
    "features": {
      "max_concurrent_calls": 10,
      "voice_cloning": true,
      "advanced_analytics": true,
      "custom_integration": false,
      "priority_support": true
    },
    "settings": {
      "timezone": "America/Santiago"
    },
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-10-16T08:30:00Z"
  }
]
```

#### 🟢 POST `/api/v1/accounts`
**Implementado:** ✅ SÍ

**Request:**
```json
{
  "account_name": "Empresa XYZ",
  "contact_name": "María González",
  "contact_email": "maria@empresaxyz.cl",
  "contact_phone": "+56987654321",
  "plan_type": "credit_based",
  "initial_credits": 1000,
  "features": {
    "max_concurrent_calls": 5,
    "voice_cloning": false,
    "advanced_analytics": false,
    "custom_integration": false,
    "priority_support": false
  },
  "settings": {
    "timezone": "America/Santiago"
  }
}
```

**Response (201):**
```json
{
  "_id": "acc_002",
  "account_id": "acc-chile-002",
  "account_name": "Empresa XYZ",
  ...resto de campos
}
```

#### 🔴 GET `/api/v1/accounts/{account_id}`
**Implementado:** ✅ SÍ

**Response:** Mismo formato que GET /accounts pero un solo objeto

#### 🔴 PUT `/api/v1/accounts/{account_id}`
**Implementado:** ✅ SÍ

**Request:** Campos a actualizar (parcial)
```json
{
  "account_name": "Nuevo Nombre",
  "features": {
    "max_concurrent_calls": 15
  }
}
```

#### 🔴 PUT `/api/v1/accounts/{account_id}/suspend`
**Implementado:** ✅ SÍ

**Request:**
```json
{
  "reason": "Impago de factura"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account suspended successfully"
}
```

#### 🔴 PUT `/api/v1/accounts/{account_id}/activate`
**Implementado:** ✅ SÍ

**Response:**
```json
{
  "success": true,
  "message": "Account activated successfully"
}
```

#### 🟡 GET `/api/v1/accounts/{account_id}/balance`
**Implementado:** ⚠️ FALTA

**Response esperado:**
```json
{
  "account_id": "acc-chile-001",
  "balance": {
    "credits": 5000,
    "minutes": 0
  },
  "last_topup": {
    "amount": 1000,
    "date": "2025-10-01T10:00:00Z"
  },
  "total_spent": 1250.50,
  "estimated_depletion_date": "2025-11-15T00:00:00Z"
}
```

#### 🟡 GET `/api/v1/accounts/{account_id}/stats`
**Implementado:** ⚠️ FALTA

**Response esperado:**
```json
{
  "account_id": "acc-chile-001",
  "total_batches": 45,
  "active_batches": 3,
  "total_calls": 12450,
  "calls_this_month": 3450,
  "success_rate": 87.5,
  "avg_call_duration": 180,
  "total_cost_this_month": 1250.75
}
```

#### 🟢 GET `/api/v1/accounts/{account_id}/batches`
**Implementado:** ✅ SÍ

Lista de batches de esta cuenta

#### 🟢 GET `/api/v1/accounts/{account_id}/transactions`
**Implementado:** ✅ SÍ

**Response:**
```json
[
  {
    "_id": "trans_001",
    "account_id": "acc-chile-001",
    "type": "topup",
    "amount": 1000,
    "cost": 0,
    "description": "Recarga de créditos",
    "created_at": "2025-10-01T10:00:00Z"
  },
  {
    "_id": "trans_002",
    "account_id": "acc-chile-001",
    "type": "usage",
    "amount": -10,
    "cost": 5.50,
    "description": "Llamada completada - Job job_123",
    "created_at": "2025-10-16T14:30:00Z"
  }
]
```

#### 🔴 POST `/api/v1/accounts/{account_id}/topup`
**Implementado:** ✅ SÍ

**Request:**
```json
{
  "credits": 1000
}
```
o
```json
{
  "minutes": 500
}
```

**Response:**
```json
{
  "success": true,
  "new_balance": {
    "credits": 6000,
    "minutes": 0
  }
}
```

### Acciones Disponibles:
1. ✅ **Listar cuentas** → GET /accounts
2. ✅ **Crear cuenta** → POST /accounts
3. ✅ **Ver detalle** → GET /accounts/{id}
4. ✅ **Editar cuenta** → PUT /accounts/{id}
5. ✅ **Suspender cuenta** → PUT /accounts/{id}/suspend
6. ✅ **Activar cuenta** → PUT /accounts/{id}/activate
7. ✅ **Recargar créditos** → POST /accounts/{id}/topup
8. ⚠️ **Ver balance detallado** → GET /accounts/{id}/balance (FALTA)
9. ⚠️ **Ver estadísticas** → GET /accounts/{id}/stats (FALTA)

### Estado Actual:
✅ **Mayoría implementado**  
⚠️ **Pendiente:** Simplificar CreateAccountModal (quitar call_settings)  
⚠️ **Pendiente:** Endpoints de balance y stats detallados

---

## 📄 PANTALLA 4: BATCHES (CAMPAÑAS)

**Ruta:** `/batches`  
**Archivo:** `src/pages/Batches/BatchesPage.tsx`  
**Acceso:** Protegido

### Descripción:
Gestión de campañas de llamadas. Permite crear, pausar, reanudar y cancelar campañas.

### Componentes Visuales:

#### 1. **Header con Botón**
- Título: "Campañas de Llamadas"
- Botón: "+ Nueva Campaña"

#### 2. **Filtros**
- Select de Estado: Todos / Pendientes / En Ejecución / Pausados / Completados / Cancelados

#### 3. **Stats Cards** (5 cards)
- 📋 **Total**: Todas las campañas
- ▶️ **En Ejecución**: Status RUNNING
- ⏸️ **Pausados**: Status PAUSED
- ✅ **Completados**: Status COMPLETED
- 💰 **Costo Total**: Suma de costos de todas las campañas

#### 4. **Tabla de Campañas**
Columnas:
- **Nombre**: Nombre de la campaña + descripción
- **Cuenta**: Nombre de la cuenta asociada
- **Estado**: Badge con color
- **Progreso**: Barra visual + "450/1000 (45%)"
- **Creado**: Fecha
- **Acciones**: Botones dinámicos según estado
  - RUNNING: "Pausar", "Ver Detalle"
  - PAUSED: "Reanudar", "Cancelar", "Ver Detalle"
  - PENDING: "Iniciar", "Editar", "Eliminar"

### Modal: Crear Campaña (`CreateBatchModal`)

**4 Pasos en wizard:**

**Paso 1: Información Básica**
- Seleccionar Cuenta (dropdown)
- Nombre de la Campaña
- Descripción (opcional)
- Script/Texto a enviar (textarea) ⚠️ Sin sistema de plantillas por ahora

**Paso 2: Subir Contactos**
- Upload Excel/CSV
- Preview de datos
- Validación de columnas

**Paso 3: Configuración de Llamadas** ✅ DEBE ESTAR AQUÍ
- Duración máxima de llamada (segundos)
- Timeout de ring (segundos)
- Horarios permitidos: Inicio - Fin
- Días de la semana: Checkboxes (Lun-Dom)
- Reintentos máximos
- Delay entre reintentos (horas)
- Zona horaria

**Paso 4: Configuración de Voz**
- Idioma (es-CL, es-AR, es-MX, etc.)
- Velocidad (0.5 - 2.0)
- Tono (pitch)
- Volumen

**Paso 5: Programación**
- Radio buttons:
  - Inmediato
  - Programado (fecha/hora)
  - Recurrente (configuración)

### Endpoints Esperados:

#### 🟢 GET `/api/v1/batches`
**Implementado:** ✅ SÍ

**Query params:**
- `account_id`: Filtrar por cuenta
- `status`: Filtrar por estado
- `limit`: Número de resultados
- `skip`: Paginación

**Response:**
```json
[
  {
    "_id": "batch_001",
    "batch_id": "batch-20251016-001",
    "account_id": "acc-chile-001",
    "name": "Campaña Cobranza Octubre",
    "description": "Recordatorio de pagos pendientes",
    "status": "RUNNING",
    "total_jobs": 1000,
    "pending_jobs": 550,
    "completed_jobs": 400,
    "failed_jobs": 50,
    "suspended_jobs": 0,
    "total_cost": 450.75,
    "total_minutes": 180.5,
    "is_active": true,
    "created_at": "2025-10-16T10:00:00Z",
    "started_at": "2025-10-16T10:05:00Z",
    "call_settings": {
      "allowed_hours": {
        "start": "09:00",
        "end": "18:00"
      },
      "days_of_week": [1, 2, 3, 4, 5],
      "max_attempts": 3,
      "retry_delay_hours": 24,
      "max_call_duration": 300,
      "ring_timeout": 30,
      "timezone": "America/Santiago"
    }
  }
]
```

#### 🟢 POST `/api/v1/batches`
**Implementado:** ✅ SÍ (con call_settings)

**Request:**
```json
{
  "account_id": "acc-chile-001",
  "name": "Campaña Cobranza Noviembre",
  "description": "Segunda ronda de recordatorios",
  "script_content": "Hola {{nombre}}, le llamo de {{empresa}}. Tenemos registrada una deuda pendiente...",
  "voice_settings": {
    "voice_id": "default",
    "speed": 1.0,
    "pitch": 0,
    "volume": 1.0,
    "language": "es-CL"
  },
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
  "schedule_type": "immediate",
  "priority": "normal"
}
```

**Response (201):**
```json
{
  "_id": "batch_002",
  "batch_id": "batch-20251016-002",
  ...resto de campos
}
```

#### 🟢 GET `/api/v1/batches/{batch_id}`
**Implementado:** ✅ SÍ

**Response:** Mismo formato que GET /batches pero un solo objeto

#### 🟡 GET `/api/v1/batches/{batch_id}/summary`
**Implementado:** ✅ SÍ

**Response:**
```json
{
  "batch": { ...objeto completo del batch },
  "stats": {
    "total_jobs": 1000,
    "pending": 550,
    "in_progress": 5,
    "completed": 400,
    "failed": 45
  },
  "jobs_sample": [
    ...primeros 10 jobs del batch
  ]
}
```

#### 🟢 GET `/api/v1/batches/{batch_id}/status`
**Implementado:** ✅ SÍ

Optimizado para polling cada 5 segundos.

**Response:**
```json
{
  "batch_id": "batch-20251016-001",
  "is_active": true,
  "total_jobs": 1000,
  "pending_jobs": 550,
  "completed_jobs": 400,
  "failed_jobs": 50,
  "suspended_jobs": 0,
  "total_cost": 450.75,
  "total_minutes": 180.5,
  "progress_percentage": 45.0,
  "started_at": "2025-10-16T10:05:00Z",
  "completed_at": null
}
```

#### 🟢 PUT `/api/v1/batches/{batch_id}/pause`
**Implementado:** ✅ SÍ

**Response:**
```json
{
  "success": true,
  "message": "Batch paused successfully"
}
```

#### 🟢 PUT `/api/v1/batches/{batch_id}/resume`
**Implementado:** ✅ SÍ

**Response:**
```json
{
  "success": true,
  "message": "Batch resumed successfully"
}
```

#### 🟢 POST `/api/v1/batches/{batch_id}/cancel`
**Implementado:** ✅ SÍ

**Query params:**
- `reason` (opcional): Razón de la cancelación

**Response:**
```json
{
  "success": true,
  "message": "Batch cancelled successfully",
  "reason": "Cliente solicitó detención"
}
```

#### 🟢 DELETE `/api/v1/batches/{batch_id}`
**Implementado:** ✅ SÍ

**Query params:**
- `delete_jobs` (boolean): Si debe eliminar los jobs también

**Response:**
```json
{
  "success": true,
  "message": "Batch deleted successfully",
  "jobs_deleted": 150
}
```

#### 🟢 POST `/api/v1/batches/{batch_id}/upload`
**Implementado:** ✅ SÍ

Subir CSV con contactos adicionales.

**Request:** multipart/form-data
```
file: archivo.csv
```

**Response:**
```json
{
  "success": true,
  "jobs_created": 150,
  "batch_id": "batch-20251016-001"
}
```

#### 🟢 GET `/api/v1/batches/{batch_id}/jobs`
**Implementado:** ✅ SÍ

Lista de jobs de este batch.

**Query params:**
- `status`: Filtrar por estado
- `limit`, `skip`: Paginación

### Endpoints de Excel (especializados):

#### 🟢 POST `/api/v1/batches/excel/preview`
**Implementado:** ✅ SÍ

Preview de archivo Excel antes de crear batch.

**Request:** multipart/form-data
```
file: archivo.xlsx
account_id: acc-chile-001
```

**Response:**
```json
{
  "success": true,
  "preview": {
    "total_rows": 1000,
    "sample_rows": [
      {
        "nombre": "Juan Pérez",
        "telefono": "+56912345678",
        "rut": "12345678-9",
        "deuda": 150000
      },
      ...5 más
    ],
    "detected_columns": ["nombre", "telefono", "rut", "deuda"],
    "country_format": "chile"
  }
}
```

#### 🟢 POST `/api/v1/batches/excel/create`
**Implementado:** ✅ SÍ

Crear batch directamente desde Excel.

**Request:** multipart/form-data
```
file: archivo.xlsx
account_id: acc-chile-001
processing_type: basic | acquisition
```

**Response:**
```json
{
  "success": true,
  "batch_id": "batch-20251016-003",
  "jobs_created": 1000,
  "errors": [],
  "warnings": []
}
```

#### 🟢 POST `/api/v1/batches/chile/debt_collection`
**Implementado:** ✅ SÍ

Crear batch especializado para cobranza en Chile.

#### 🟢 POST `/api/v1/batches/argentina/debt_collection`
**Implementado:** ✅ SÍ

Crear batch especializado para cobranza en Argentina.

### Acciones Disponibles:
1. ✅ **Listar batches** → GET /batches
2. ✅ **Crear batch** → POST /batches
3. ✅ **Ver detalle** → GET /batches/{id}
4. ✅ **Ver status (polling)** → GET /batches/{id}/status
5. ✅ **Pausar** → PUT /batches/{id}/pause
6. ✅ **Reanudar** → PUT /batches/{id}/resume
7. ✅ **Cancelar** → POST /batches/{id}/cancel
8. ✅ **Eliminar** → DELETE /batches/{id}
9. ✅ **Subir CSV** → POST /batches/{id}/upload
10. ✅ **Preview Excel** → POST /batches/excel/preview
11. ✅ **Crear desde Excel** → POST /batches/excel/create

### Estado Actual:
✅ **Todos los endpoints implementados**  
⚠️ **Pendiente Frontend:** Implementar polling de status cada 5s

---

## 📄 PANTALLA 5: BATCH DETAIL (DETALLE DE CAMPAÑA)

**Ruta:** `/batches/:id`  
**Archivo:** `src/pages/Batches/BatchDetailPage.tsx`  
**Acceso:** Protegido

### Descripción:
Vista detallada de una campaña específica con métricas en tiempo real, lista de jobs y acciones.

### Componentes Visuales:

#### 1. **Header con Acciones**
- Título: Nombre de la campaña
- Estado: Badge
- Botones según estado:
  - RUNNING: "Pausar", "Cancelar"
  - PAUSED: "Reanudar", "Cancelar"

#### 2. **Progress Section**
- Barra de progreso visual (0-100%)
- Texto: "450 de 1000 completados (45%)"
- Tiempo estimado de finalización

#### 3. **Stats Grid** (6 cards)
- ⏳ **Pendientes**: Jobs pending
- ▶️ **En Progreso**: Jobs in_progress
- ✅ **Completados**: Jobs completed
- ❌ **Fallidos**: Jobs failed
- 💰 **Costo Total**: Total cost
- ⏱️ **Minutos Usados**: Total minutes

#### 4. **Tabs (Pestañas)**

**Tab 1: Información**
- Nombre
- Descripción
- Script content
- Configuración de voz
- Call settings (horarios, reintentos, etc.)

**Tab 2: Jobs**
- Tabla con lista de jobs del batch
- Filtros por estado
- Paginación
- Botones: "Ver Detalle", "Reintentar" (si failed)

**Tab 3: Estadísticas**
- Gráfico de progreso en el tiempo
- Tasa de éxito por hora
- Distribución de estados

**Tab 4: Logs**
- Log de eventos del batch
- Inicios, pausas, reanudaciones, errores

### Endpoints Esperados:

Todos los mencionados en la sección de Batches, más:

#### 🟢 GET `/api/v1/batches/{batch_id}/status`
**Implementado:** ✅ SÍ

**Uso:** Polling cada 5 segundos para actualizar progreso en tiempo real

#### 🟢 GET `/api/v1/batches/{batch_id}/jobs`
**Implementado:** ✅ SÍ

**Response:** Lista de jobs del batch con paginación

### Polling en Tiempo Real:
```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    const status = await api.get(`/batches/${batchId}/status`);
    updateUI(status);
  }, 5000); // Cada 5 segundos
  
  return () => clearInterval(interval);
}, [batchId]);
```

### Estado Actual:
⚠️ **Página básica implementada**  
🔧 **Pendiente:** Implementar polling, stats, tabs completos

---

## 📄 PANTALLA 6: NEW BATCH WIZARD (CREAR CAMPAÑA)

**Ruta:** `/batches/new`  
**Archivo:** `src/pages/Batches/NewBatchWizard.tsx`  
**Acceso:** Protegido

### Descripción:
Wizard paso a paso para crear una nueva campaña de llamadas.

### Pasos del Wizard:

**Paso 1: Subir Archivo**
- Drag & drop o select de archivo Excel/CSV
- Validación de formato
- Preview de columnas detectadas

**Paso 2: Mapear Columnas**
- Mapeo de columnas del Excel a variables del sistema
- Nombre → campo "nombre"
- Teléfono → campo "telefono"
- Otras variables custom

**Paso 3: Revisar Datos**
- Tabla con preview de los datos mapeados
- Validación de datos
- Contador de filas válidas/inválidas

**Paso 4: Configurar Campaña**
- Nombre de la campaña
- Descripción
- Script/texto
- Configuración de voz
- Call settings (horarios, reintentos)
- Programación

### Endpoints Usados:
- POST `/api/v1/batches/excel/preview` → Paso 1
- POST `/api/v1/batches/excel/create` → Paso final

### Estado Actual:
⚠️ **Wizard básico implementado**  
🔧 **Pendiente:** Completar todos los pasos, validaciones

---

## 📄 PANTALLA 7: JOBS (TAREAS)

**Ruta:** `/jobs`  
**Archivo:** `src/pages/Jobs/JobsPage.tsx`  
**Acceso:** Protegido

### Descripción:
Lista de todas las tareas individuales de llamadas. Cada job representa una llamada a un contacto específico.

### Componentes Visuales:

#### 1. **Header**
- Título: "Tareas de Procesamiento"

#### 2. **Filter Tabs**
Tabs para filtrar por estado:
- Todas
- Pendientes (pending)
- En Progreso (in_progress)
- Completadas (completed)
- Terminadas (done)
- Fallidas (failed)

#### 3. **Tabla de Jobs**
Columnas:
- **Contacto**: Nombre + Batch ID
- **Estado**: Badge con color
- **Intentos**: Barra de progreso "2/3"
- **Creado**: Fecha
- **Acciones**: 
  - Si in_progress: "Pausar"
  - Si failed: "Reintentar"
  - Siempre: "Ver Detalle"

### Modal: Detalle de Job (`JobDetailModal`)

**Información mostrada:**
- Datos del contacto (nombre, teléfonos)
- Estado actual
- Batch asociado
- Cuenta asociada
- Intentos realizados
- Costo estimado
- Call result (si existe):
  - Estado de la llamada
  - Duración
  - Costo real
  - URL de grabación
  - Resumen de la conversación
  - Sentiment analysis
- Historial de intentos
- Logs de errores (si hay)

### Endpoints Esperados:

#### 🟢 GET `/api/v1/jobs`
**Implementado:** ✅ SÍ

**Query params:**
- `account_id`: Filtrar por cuenta
- `batch_id`: Filtrar por batch
- `status`: Filtrar por estado (pending, in_progress, completed, failed, cancelled, done)
- `limit`, `skip`: Paginación

**Response:**
```json
[
  {
    "_id": "job_001",
    "job_id": "job-20251016-001",
    "account_id": "acc-chile-001",
    "batch_id": "batch-20251016-001",
    "status": "completed",
    "contact": {
      "name": "Juan Pérez",
      "dni": "12345678-9",
      "phones": ["+56912345678", "+56987654321"],
      "next_phone_index": 1
    },
    "payload": {
      "company_name": "Empresa ABC",
      "debt_amount": 150000,
      "due_date": "2025-10-31",
      "reference_number": "INV-2025-001",
      "additional_info": {}
    },
    "mode": "CONTINUOUS",
    "attempts": 1,
    "max_attempts": 3,
    "estimated_cost": 5.50,
    "created_at": "2025-10-16T10:00:00Z",
    "started_at": "2025-10-16T10:05:00Z",
    "updated_at": "2025-10-16T10:08:00Z",
    "call_result": {
      "success": true,
      "status": "completed",
      "summary": {
        "call_status": "completed",
        "disconnection_reason": null,
        "duration_ms": 125000,
        "call_cost": {
          "total_duration_seconds": 125,
          "combined_cost": 5.50
        },
        "call_analysis": {
          "call_summary": "Cliente confirmó que realizará el pago antes del vencimiento",
          "user_sentiment": "positive",
          "call_successful": true
        },
        "recording_url": "https://storage.example.com/recordings/call_123.mp3",
        "public_log_url": "https://logs.example.com/job_001"
      }
    },
    "call_id": "call_vapi_123456",
    "call_duration_seconds": 125,
    "last_error": null
  }
]
```

#### 🟢 GET `/api/v1/jobs/{job_id}`
**Implementado:** ✅ SÍ

**Response:** Mismo formato que GET /jobs pero un solo objeto

#### 🟢 PUT `/api/v1/jobs/{job_id}/retry`
**Implementado:** ✅ SÍ

Reintentar un job que falló.

**Response:**
```json
{
  "success": true,
  "message": "Job retry scheduled",
  "job_id": "job-20251016-001"
}
```

#### 🟢 DELETE `/api/v1/jobs/{job_id}`
**Implementado:** ✅ SÍ

Cancelar un job.

**Response:**
```json
{
  "success": true,
  "message": "Job cancelled"
}
```

### Acciones Disponibles:
1. ✅ **Listar jobs** → GET /jobs
2. ✅ **Ver detalle** → GET /jobs/{id}
3. ✅ **Reintentar** → PUT /jobs/{id}/retry
4. ✅ **Cancelar** → DELETE /jobs/{id}

### Estado Actual:
✅ **Endpoints implementados**  
✅ **UI básica funcionando**

---

## 📄 PANTALLA 8: REPORTS (REPORTES)

**Ruta:** `/reports`  
**Archivo:** `src/pages/Reports/ReportsPage.tsx`  
**Acceso:** Protegido

### Descripción:
Generación y visualización de reportes de campañas y llamadas.

### Componentes Visuales:

#### 1. **Filtros de Reporte**
- Rango de fechas (desde - hasta)
- Seleccionar cuenta
- Seleccionar batch
- Tipo de reporte:
  - Resumen general
  - Por cuenta
  - Por batch
  - Por período

#### 2. **Botones de Exportación**
- Exportar a CSV
- Exportar a Excel
- Exportar a PDF

#### 3. **Visualizaciones**
- Gráfico de llamadas por día
- Gráfico de tasa de éxito
- Gráfico de costos
- Tabla de top accounts
- Tabla de top batches

### Endpoints Esperados:

#### 🔴 GET `/api/v1/reports`
**Implementado:** ❌ NO (placeholder)

**Query params:**
- `account_id`: Filtrar por cuenta
- `batch_id`: Filtrar por batch
- `start_date`: Fecha inicio (ISO 8601)
- `end_date`: Fecha fin (ISO 8601)
- `report_type`: Tipo de reporte

**Response esperado:**
```json
{
  "report_id": "report_001",
  "generated_at": "2025-10-16T15:30:00Z",
  "filters": {
    "start_date": "2025-10-01",
    "end_date": "2025-10-16",
    "account_id": "acc-chile-001"
  },
  "summary": {
    "total_calls": 12450,
    "successful_calls": 10893,
    "failed_calls": 1557,
    "success_rate": 87.5,
    "total_cost": 15450.75,
    "total_duration_minutes": 6225.5
  },
  "daily_breakdown": [
    {
      "date": "2025-10-01",
      "total_calls": 789,
      "successful": 690,
      "failed": 99,
      "cost": 987.50
    },
    ...
  ],
  "top_batches": [
    {
      "batch_id": "batch-001",
      "name": "Campaña Octubre",
      "total_calls": 1000,
      "success_rate": 92.5,
      "total_cost": 1250.00
    },
    ...
  ]
}
```

#### 🔴 POST `/api/v1/reports/generate`
**Implementado:** ❌ NO (placeholder)

**Request:**
```json
{
  "account_id": "acc-chile-001",
  "start_date": "2025-10-01",
  "end_date": "2025-10-16",
  "format": "csv",
  "report_type": "general"
}
```

**Response:**
```json
{
  "success": true,
  "report_id": "report_001",
  "download_url": "https://storage.example.com/reports/report_001.csv",
  "expires_at": "2025-10-17T15:30:00Z"
}
```

### Estado Actual:
❌ **NO IMPLEMENTADO**  
🔵 **NO PRIORITARIO** (se trabajará en el futuro)

---

## 📄 PANTALLA 9: API TEST

**Ruta:** `/test-api`  
**Archivo:** `src/pages/Test/ApiTestPage.tsx`  
**Acceso:** Protegido

### Descripción:
Página de testing para probar la conectividad con el backend y endpoints disponibles.

### Funcionalidades:
1. **Health Check** → GET /health
2. **Test de autenticación**
3. **Test de endpoints principales**
4. Visualización de respuestas JSON
5. Botones para cada endpoint

### Endpoints Usados:
- GET `/health` → Health check del backend

### Estado Actual:
✅ **Implementado para development**

---

## 📊 RESUMEN DE ENDPOINTS POR PRIORIDAD

### ✅ IMPLEMENTADOS Y FUNCIONANDO (Backend completo)

```
Autenticación:
❌ POST /api/v1/auth/login (falta implementar real)

Dashboard:
✅ GET  /api/v1/dashboard/overview (actualizado)
✅ GET  /health

Accounts:
✅ GET  /api/v1/accounts
✅ POST /api/v1/accounts
✅ GET  /api/v1/accounts/{id}
✅ PUT  /api/v1/accounts/{id}
✅ PUT  /api/v1/accounts/{id}/suspend
✅ PUT  /api/v1/accounts/{id}/activate
✅ POST /api/v1/accounts/{id}/topup
✅ GET  /api/v1/accounts/{id}/batches
✅ GET  /api/v1/accounts/{id}/transactions

Batches:
✅ GET    /api/v1/batches
✅ POST   /api/v1/batches (con call_settings)
✅ GET    /api/v1/batches/{id}
✅ GET    /api/v1/batches/{id}/summary
✅ GET    /api/v1/batches/{id}/status (polling)
✅ PUT    /api/v1/batches/{id}/pause
✅ PUT    /api/v1/batches/{id}/resume
✅ POST   /api/v1/batches/{id}/cancel
✅ DELETE /api/v1/batches/{id}
✅ POST   /api/v1/batches/{id}/upload
✅ GET    /api/v1/batches/{id}/jobs
✅ POST   /api/v1/batches/excel/preview
✅ POST   /api/v1/batches/excel/create
✅ POST   /api/v1/batches/chile/debt_collection
✅ POST   /api/v1/batches/argentina/debt_collection

Jobs:
✅ GET    /api/v1/jobs
✅ GET    /api/v1/jobs/{id}
✅ PUT    /api/v1/jobs/{id}/retry
✅ DELETE /api/v1/jobs/{id}
```

### ⚠️ FALTA IMPLEMENTAR (Prioridad Media)

```
Accounts:
⚠️ GET /api/v1/accounts/{id}/balance
⚠️ GET /api/v1/accounts/{id}/stats
```

### 🔵 NO PRIORITARIO (Futuro)

```
Auth:
🔵 POST /api/v1/auth/login
🔵 POST /api/v1/auth/logout
🔵 POST /api/v1/auth/refresh
🔵 GET  /api/v1/auth/me

Reports:
🔵 GET  /api/v1/reports
🔵 POST /api/v1/reports/generate

Scripts (futuro):
🔵 GET  /api/v1/scripts/templates
🔵 POST /api/v1/scripts/templates
🔵 GET  /api/v1/scripts/templates/{id}
🔵 PUT  /api/v1/scripts/templates/{id}
```

---

## 🎯 PENDIENTES EN FRONTEND

### Prioridad ALTA 🔴

1. ✅ **~~Simplificar CreateAccountModal~~** → **COMPLETADO**
   - ✅ Quitada sección de "Configuraciones de Llamadas" (horarios, reintentos)
   - ✅ Quitados checkboxes de features (voice cloning, analytics, etc.)
   - ✅ Mantenido solo: max_concurrent_calls y timezone

2. **Implementar Polling en BatchDetailPage**
   - useEffect con setInterval(5000)
   - GET /batches/{id}/status

3. **Actualizar Dashboard con /overview**
   - Refresh automático cada 30s
   - Mostrar 4 métricas principales

4. **Implementar Botón Cancelar en Batches**
   - POST /batches/{id}/cancel
   - Confirmación + razón opcional

### Prioridad MEDIA 🟡

5. **Completar BatchDetailPage**
   - Tabs completos
   - Stats en tiempo real
   - Lista de jobs con paginación

6. **Completar NewBatchWizard**
   - Todos los pasos del wizard
   - Validaciones
   - Preview de datos

7. **JobDetailModal mejorado**
   - Mostrar toda la info de call_result
   - Reproducir grabación
   - Ver logs completos

---

## 📝 NOTAS IMPORTANTES

### Para el Backend Developer:

1. **call_settings va en Batch, NO en Account**
   - ✅ Ya implementado en backend
   - ⚠️ Frontend pendiente de actualizar

2. **Sistema de Scripts NO prioritario**
   - Por ahora script_content es un simple string
   - Futuro: plantillas con variables

3. **Polling optimizado**
   - `/batches/{id}/status` debe ser rápido
   - Payload mínimo
   - Cacheable

4. **Formato de fechas**
   - Siempre ISO 8601: "2025-10-16T10:00:00Z"
   - Timestamps en UTC

5. **Paginación**
   - Usar `limit` y `skip`
   - Default: limit=50

6. **Filtros**
   - Soportar múltiples filtros por query params
   - account_id, batch_id, status, etc.

---

## 🚀 QUICK START para Backend

### Endpoints que DEBES tener funcionando AHORA:

```bash
# Dashboard
GET /api/v1/dashboard/overview

# Accounts (CRUD completo)
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{id}
PUT    /api/v1/accounts/{id}
PUT    /api/v1/accounts/{id}/suspend
PUT    /api/v1/accounts/{id}/activate
POST   /api/v1/accounts/{id}/topup

# Batches (CRUD completo + control)
GET    /api/v1/batches
POST   /api/v1/batches
GET    /api/v1/batches/{id}
GET    /api/v1/batches/{id}/status
PUT    /api/v1/batches/{id}/pause
PUT    /api/v1/batches/{id}/resume
POST   /api/v1/batches/{id}/cancel

# Jobs (lectura + control)
GET    /api/v1/jobs
GET    /api/v1/jobs/{id}
PUT    /api/v1/jobs/{id}/retry
```

### Endpoints opcionales (mejorarían UX):

```bash
# Stats detallados
GET /api/v1/accounts/{id}/balance
GET /api/v1/accounts/{id}/stats
```

---

**Documento generado:** 16 Octubre 2025  
**Última actualización:** Estado actual del proyecto  
**Versión:** 1.0.0
