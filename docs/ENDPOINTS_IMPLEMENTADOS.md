# 📚 ENDPOINTS IMPLEMENTADOS - SPEECHAI BACKEND

## ✅ **ENDPOINTS COMPLETADOS**

Los siguientes **4 endpoints principales** + **2 endpoints adicionales** han sido **implementados completamente** y están listos para usar desde el frontend:

## 🎯 **ENDPOINTS PRINCIPALES** (Los que pediste)

### 1. **GET /api/v1/accounts** ✅
**Descripción**: Lista todas las cuentas del sistema con filtros opcionales  
**Query Parameters**:
- `status`: Filtrar por estado (`active`, `suspended`, `expired`)
- `plan_type`: Filtrar por tipo de plan (`minutes_based`, `credit_based`, `unlimited`)
- `limit`: Máximo de resultados (default: 100, max: 1000)
- `skip`: Número de resultados a saltar para paginación

**Response Example**:
```json
[
  {
    "_id": "507f1f77bcf86cd799439011",
    "account_id": "strasing",
    "account_name": "Strasing Corp",
    "status": "active",
    "plan_type": "credit_based",
    "credit_balance": 1500.0,
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

### 2. **GET /api/v1/batches/{batch_id}/jobs** ✅
**Descripción**: Obtiene todos los jobs/tareas de un batch específico  
**Path Parameters**:
- `batch_id`: ID del batch

**Query Parameters**:
- `status`: Filtrar por estado del job (`pending`, `completed`, `failed`, etc.)
- `limit`: Máximo de resultados (default: 100, max: 1000)
- `skip`: Número de resultados a saltar

**Response Example**:
```json
[
  {
    "_id": "507f1f77bcf86cd799439012",
    "job_id": "job_xyz789",
    "batch_id": "batch_abc123",
    "account_id": "strasing",
    "status": "completed",
    "contact": {
      "name": "Juan Pérez",
      "dni": "12345678",
      "phones": ["+56992125907"]
    },
    "attempts": 1,
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

### 3. **GET /api/v1/accounts/{account_id}/batches** ✅
**Descripción**: Obtiene todas las campañas/batches de una cuenta específica  
**Path Parameters**:
- `account_id`: ID de la cuenta

**Query Parameters**:
- `is_active`: Filtrar por batches activos (`true`/`false`)
- `limit`: Máximo de resultados (default: 100, max: 1000)
- `skip`: Número de resultados a saltar

**Response Example**:
```json
[
  {
    "_id": "507f1f77bcf86cd799439013",
    "batch_id": "batch_abc123",
    "account_id": "strasing",
    "name": "Campaña Cobranza Q1",
    "description": "Cobranza de deudas trimestre 1",
    "status": "active",
    "total_jobs": 150,
    "completed_jobs": 85,
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

### 4. **GET /api/v1/accounts/{account_id}/transactions** ✅
**Descripción**: Obtiene el historial de transacciones financieras de una cuenta  
**Path Parameters**:
- `account_id`: ID de la cuenta

**Query Parameters**:
- `transaction_type`: Filtrar por tipo (`topup_credits`, `call_usage`, `bonus`, etc.)
- `limit`: Máximo de resultados (default: 50, max: 200)
- `skip`: Número de resultados a saltar

**Response Example**:
```json
[
  {
    "_id": "507f1f77bcf86cd799439014",
    "transaction_id": "txn_abc12345",
    "account_id": "strasing",
    "type": "topup_credits",
    "amount": 1000.0,
    "cost": 50000,
    "description": "Recarga plan mensual - 1000 créditos",
    "created_at": "2025-01-15T10:30:00Z"
  },
  {
    "_id": "507f1f77bcf86cd799439015",
    "transaction_id": "txn_def67890",
    "account_id": "strasing", 
    "type": "call_usage",
    "amount": -180.0,
    "cost": 9000,
    "description": "Uso en campaña: Basic Batch 2025-10-03",
    "created_at": "2025-01-14T15:20:00Z"
  }
]
```

## 🌟 **ENDPOINTS ADICIONALES** (Bonus para el frontend)

### 5. **GET /api/v1/dashboard/overview** ✅
**Descripción**: Resumen ejecutivo para el dashboard principal  
**Query Parameters**:
- `account_id`: ID de cuenta (opcional, si no se proporciona retorna stats globales)

**Response Example**:
```json
{
  "jobs_today": 15,
  "success_rate": "69.4%",
  "active_batches": 3,
  "pending_jobs": 8,
  "recent_batches": [
    {
      "name": "Basic Batch 2025-10-03 16:49",
      "status": "RUNNING",
      "jobs_count": "12 jobs",
      "description": "RUNNING"
    }
  ],
  "daily_summary": {
    "completed": 10,
    "in_progress": 3,
    "failed": 2,
    "revenue": "$0"
  }
}
```

### 6. **GET /api/v1/accounts/{account_id}/summary** ✅
**Descripción**: Resumen completo de una cuenta (ideal para modales de detalle)  
**Path Parameters**:
- `account_id`: ID de la cuenta

**Response Example**:
```json
{
  "account": { /* AccountModel completo */ },
  "balance": { /* Balance actual */ },
  "stats": {
    "total_batches": 5,
    "active_batches": 2,
    "completed_batches": 3
  },
  "financial_summary": {
    "total_spent": 265.0,
    "total_recharges": 1500.0,
    "total_usage": 500.0,
    "transaction_count": 6
  }
}
```

---

## 📊 **TIPOS DE TRANSACCIONES**

### **Transacciones Positivas** (Recargas) ➕
- `topup_credits`: Recarga de créditos
- `topup_minutes`: Recarga de minutos  
- `bonus`: Bonos promocionales
- `refund`: Reembolsos

### **Transacciones Negativas** (Consumos) ➖
- `call_usage`: Uso en llamadas
- `call_setup`: Costo setup de llamada
- `penalty`: Penalizaciones

### **Transacciones Neutras** 🔄
- `plan_upgrade`: Upgrade de plan
- `plan_renewal`: Renovación de plan

---

## 🔧 **VALIDACIONES IMPLEMENTADAS**

### **Códigos de Error HTTP**
- **200 OK**: Operación exitosa
- **400 Bad Request**: Parámetros inválidos (ej: `status` incorrecto)
- **404 Not Found**: Recurso no encontrado (cuenta, batch)
- **500 Internal Server Error**: Error del servidor

### **Validaciones Específicas**
1. **GET /api/v1/accounts**: Valida `status` y `plan_type` contra enums
2. **GET /api/v1/batches/{batch_id}/jobs**: Verifica que el batch existe si no hay jobs
3. **GET /api/v1/accounts/{account_id}/batches**: Verifica que la cuenta existe
4. **GET /api/v1/accounts/{account_id}/transactions**: Verifica cuenta y tipo de transacción

---

## 🚀 **CÓMO USAR DESDE EL FRONTEND**

### **1. Listar todas las cuentas**
```typescript
// Obtener cuentas activas
const response = await fetch('/api/v1/accounts?status=active&limit=50');
const accounts = await response.json();
```

### **2. Obtener jobs de una campaña**
```typescript
// Jobs de un batch específico
const response = await fetch('/api/v1/batches/batch_abc123/jobs?status=completed');
const jobs = await response.json();
```

### **3. Obtener campañas de una cuenta**
```typescript
// Campañas activas de una cuenta
const response = await fetch('/api/v1/accounts/strasing/batches?is_active=true');
const batches = await response.json();
```

### **4. Obtener historial de transacciones**
```typescript
// Últimas 20 transacciones de una cuenta
const response = await fetch('/api/v1/accounts/strasing/transactions?limit=20');
const transactions = await response.json();
```

---

## 📝 **DATOS DE EJEMPLO**

Para facilitar el desarrollo del frontend, se ha creado un script de inicialización que popula la base de datos con:

- **3 cuentas de ejemplo** (Strasing Corp, Fintech Solutions, Retail Express)
- **3 batches por cuenta** con diferentes estados
- **5 jobs por batch** con estados variados (completed, failed, pending)
- **6 transacciones por cuenta** (recargas, usos, bonos) distribuidas en los últimos 30 días

### **Ejecutar datos de ejemplo**:
```bash
cd app
python scripts/init_sample_data.py
```

---

## ✅ **RESUMEN PARA EL FRONTEND**

**¡Los 4 endpoints están 100% funcionales + 2 endpoints bonus!** Puedes integrarlos inmediatamente en tu frontend React:

1. ✅ **Lista de cuentas** → Para poblar dropdown/selects
2. ✅ **Jobs de campaña** → Para mostrar detalle de progreso  
3. ✅ **Campañas por cuenta** → Para dashboard de cliente
4. ✅ **Transacciones financieras** → Para historial de pagos/uso
5. 🌟 **Dashboard overview** → Para métricas del dashboard principal
6. 🌟 **Account summary** → Para modales de detalle de cuenta

## 🛠️ **NUEVOS SERVICIOS CREADOS**

- **TransactionService**: Manejo completo de transacciones financieras
- **TransactionModel**: Modelo de datos para transacciones
- **TransactionType enum**: Tipos de transacciones (topup, usage, bonus, etc.)

## 🗄️ **NUEVAS COLECCIONES EN MONGODB**

- **transactions**: Almacena el historial financiero de cada cuenta

**Próximos pasos recomendados**:
1. Ejecutar `init_sample_data.py` para tener datos de prueba
2. Integrar endpoints en tu frontend React
3. Implementar paginación usando `limit` y `skip`
4. Agregar filtros usando los query parameters disponibles