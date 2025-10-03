# 📊 ESTRUCTURA DE JOBS CREADOS POR CADA ENDPOINT

## 📋 DATOS DE EJEMPLO (Excel)
```
| RUT         | Nombre      | Telefono    | Deuda   | Fecha_Limite | Empresa   |
|-------------|-------------|-------------|---------|--------------|-----------|
| 12.345.678-9| Juan Pérez  | 09-2125907  | 150000  | 01/09/2025   | Empresa ABC |
| 98.765.432-1| Ana García  | 09-8765432  | 250000  | 15/08/2025   | Empresa ABC |
```

---

## 1️⃣ POST `/api/v1/batches/excel/create?processing_type=acquisition`

### **SERVICIO:** ChileBatchService (método legacy)
### **JOBS CREADOS:**
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f678901234"),
  "job_id": "job_cl_acq_20250928_001",
  "account_id": "cuenta123",
  "batch_id": "batch_acquisition_20250928_143055",
  "contact": {
    "name": "Juan Pérez",
    "dni": "123456789",  // RUT normalizado
    "phones": ["+56992125907"],  // Teléfono normalizado
    "next_phone_index": 0
  },
  "payload": {
    "debt_amount": 150000.0,
    "due_date": "2025-09-01",  // Fecha normalizada
    "company_name": "Empresa ABC",
    "reference_number": "",
    "additional_info": {
      "cantidad_cupones": 1,
      "rut": "123456789",
      "origen_empresa": "Empresa ABC",
      "processing_type": "acquisition"
    }
  },
  "status": "pending",
  "use_case": "acquisition",  // Caso de uso genérico
  "country": "CL",
  "created_at": "2025-09-28T14:30:55Z",
  "max_attempts": 3,
  "retell_agent_id": null,
  "deduplication_key": "cuenta123::123456789::batch_acquisition_20250928_143055"
}
```

---

## 2️⃣ POST `/api/v1/batches/chile/debt_collection`

### **SERVICIO:** ChileBatchService + DebtCollectionProcessor
### **JOBS CREADOS:**
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f678901235"),
  "job_id": "job_cl_debt_20250928_001",
  "account_id": "cuenta123", 
  "batch_id": "cl_debt_20250928_143055",
  "contact": {
    "name": "Juan Pérez",
    "dni": "123456789",  // RUT normalizado
    "phones": ["+56992125907"],  // Teléfono normalizado
    "next_phone_index": 0
  },
  "payload": {
    "debt_amount": 150000.0,
    "due_date": "2025-09-01",
    "company_name": "Empresa ABC",
    "overdue_days": 27,  // ← CALCULADO AUTOMÁTICAMENTE
    "debt_type": "consolidated",
    "payment_options": ["full_payment", "installment_plan"],
    "additional_info": {
      "cantidad_cupones": 1,
      "fecha_maxima": "2025-10-01",
      "rut": "123456789",
      "batch_origen": "cl_debt_20250928_143055"
    }
  },
  "status": "pending",
  "use_case": "debt_collection",  // Caso de uso ESPECÍFICO
  "country": "CL",
  "created_at": "2025-09-28T14:30:55Z",
  "max_attempts": 3,
  "retell_agent_id": "agent_cobranza_cl",  // ← AGENTE ESPECÍFICO
  "deduplication_key": "cuenta123::123456789::cl_debt_20250928_143055"
}
```

---

## 3️⃣ POST `/api/v1/batches/chile/marketing`

### **SERVICIO:** ChileBatchService + MarketingProcessor  
### **JOBS CREADOS:**
```json
{
  "_id": ObjectId("66f8a1b2c3d4e5f678901236"),
  "job_id": "job_cl_mkt_20250928_001",
  "account_id": "cuenta123",
  "batch_id": "cl_marketing_20250928_143055", 
  "contact": {
    "name": "Juan Pérez",
    "dni": "123456789",  // RUT normalizado
    "phones": ["+56992125907"],  // Teléfono normalizado
    "next_phone_index": 0
  },
  "payload": {
    "offer_description": "Descuento especial en productos financieros",
    "discount_percentage": 20.0,
    "product_category": "tarjetas_credito", 
    "campaign_type": "promotional",
    "valid_until": "2025-10-28",
    "company_name": "Empresa ABC",
    "additional_info": {
      "customer_segment": "premium",
      "previous_customer": true,
      "rut": "123456789"
    }
  },
  "status": "pending",
  "use_case": "marketing",  // Caso de uso MARKETING
  "country": "CL",
  "created_at": "2025-09-28T14:30:55Z", 
  "max_attempts": 2,  // ← MENOS intentos para marketing
  "retell_agent_id": "agent_marketing_cl",  // ← AGENTE MARKETING
  "deduplication_key": "cuenta123::123456789::cl_marketing_20250928_143055"
}
```

---

## 🎯 DIFERENCIAS CLAVE EN LOS JOBS

| **Campo** | **excel/create** | **chile/debt_collection** | **chile/marketing** |
|-----------|------------------|---------------------------|---------------------|
| **job_id** | `job_cl_acq_*` | `job_cl_debt_*` | `job_cl_mkt_*` |
| **use_case** | `acquisition` | `debt_collection` | `marketing` |
| **payload** | CallPayload básico | DebtCollectionPayload | MarketingPayload |
| **retell_agent_id** | `null` | `agent_cobranza_cl` | `agent_marketing_cl` |
| **max_attempts** | 3 | 3 | 2 |
| **campos_específicos** | ❌ Básicos | ✅ `overdue_days`, `debt_type` | ✅ `discount_percentage`, `campaign_type` |

---

## 📞 CONTEXTO PARA RETELL AI

### **Cobranza (debt_collection):**
```python
retell_context = {
    "nombre": "Juan Pérez",
    "rut": "12.345.678-9",  # Formato amigable
    "monto_total": "150000",
    "dias_atraso": "27", 
    "fecha_limite": "01/09/2025",
    "empresa": "Empresa ABC",
    "tipo_deuda": "consolidated",
    "opciones_pago": "pago_completo,plan_cuotas"
}
```

### **Marketing:**
```python
retell_context = {
    "nombre": "Juan Pérez",
    "rut": "12.345.678-9",
    "descripcion_oferta": "Descuento especial en productos financieros", 
    "porcentaje_descuento": "20",
    "categoria_producto": "tarjetas_credito",
    "valido_hasta": "28/10/2025",
    "empresa": "Empresa ABC",
    "segmento_cliente": "premium"
}
```

---

## 🚀 VENTAJAS DE LA NUEVA ARQUITECTURA

### **Jobs más inteligentes:**
- ✅ **Contexto especializado** por caso de uso
- ✅ **Agentes específicos** de Retell AI  
- ✅ **Campos calculados** (días de atraso)
- ✅ **Configuración diferenciada** (max_attempts)

### **Mejor experiencia:**
- 📞 **Cobranza:** "Juan, tienes 27 días de atraso..."
- 🎯 **Marketing:** "Juan, oferta especial con 20% descuento..."

### **Trazabilidad:**
- 🔍 **use_case** específico en cada job
- 🏷️ **deduplication_key** único por batch
- 📊 **Métricas** separadas por tipo de campaña

**Los jobs creados por `/api/v1/batches/chile/{use_case}` son más inteligentes y específicos** ✨