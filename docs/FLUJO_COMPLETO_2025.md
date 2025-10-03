# 🎯 FLUJO COMPLETO: EXCEL → LLAMADA AUTOMÁTICA

## 📋 ARCHIVOS ELIMINADOS (Innecesarios)

### ✅ ELIMINADOS:
- `services/acquisition_batch_service.py` → **Renombrado a** `chile_batch_service.py`
- `utils/legacy_adapter.py` → **No utilizado** (179 líneas)
- `domain/abstract/` → **Carpeta completa eliminada** (~300 líneas)
- `universal_*.py` → **Movidos a** `_deprecated/` (over-engineering)

### 💡 RESULTADO: 
- **~600 líneas eliminadas** de código innecesario
- **Arquitectura más limpia** y mantenible
- **Sin funcionalidad perdida**

---

## 🔄 FLUJO PRINCIPAL: EXCEL → LLAMADA

### 1️⃣ **CARGA DE EXCEL**
```
📁 Excel File → [API] POST /api/v1/batches/chile/{use_case}
```

**Archivos involucrados:**
- `api.py` - Endpoint principal
- `chile_batch_service.py` - Procesamiento

**Qué sucede:**
- Usuario sube Excel con datos chilenos (RUT, teléfonos 09-XXXX, fechas DD/MM/YYYY)
- API valida archivo (.xlsx, .xls)
- Pasa control a `ChileBatchService`

---

### 2️⃣ **NORMALIZACIÓN CHILENA**
```
📊 Raw Excel → [ChileBatchService] → 🇨🇱 Datos Normalizados
```

**Servicio:** `chile_batch_service.py`
**Método:** `create_batch_for_use_case()`

**Transformaciones:**
- **RUT:** `12.345.678-9` → `123456789`
- **Teléfono:** `09-2125907` → `+56992125907`  
- **Fecha:** `01/09/2025` → `2025-09-01`
- **Validaciones:** RUT válido, teléfono chileno

---

### 3️⃣ **PROCESAMIENTO POR CASO DE USO**
```
🇨🇱 Datos Normalizados → [Use Case Processor] → 📞 Jobs Especializados
```

**Casos de uso disponibles:**

#### **DEBT_COLLECTION:**
- **Procesador:** `domain/use_cases/debt_collection_processor.py`
- **Modelo:** `DebtCollectionPayload`
- **Especialización:** 
  - Calcula días de vencimiento
  - Contexto específico para cobranza
  - Template script para deudas

#### **MARKETING:**
- **Procesador:** `domain/use_cases/marketing_processor.py`
- **Modelo:** `MarketingPayload`
- **Especialización:**
  - Descuentos y ofertas
  - Segmentación por categoría
  - Template script promocional

---

### 4️⃣ **CREACIÓN DE JOBS**
```
📞 Jobs Especializados → [MongoDB] → ✅ Jobs Listos para Llamar
```

**Archivos involucrados:**
- `domain/models.py` - `JobModel`, `ContactInfo`, `CallPayload`
- `services/job_service.py` - CRUD operations
- `infrastructure/database_manager.py` - MongoDB connection

**Estructura del Job:**
```python
JobModel {
    job_id: "job_cl_debt_20250928_001",
    account_id: "cuenta123",
    contact: ContactInfo {
        name: "Juan Pérez",
        phones: ["+56992125907"],
        identifier: "123456789"  # RUT normalizado
    },
    payload: DebtCollectionPayload {
        debt_amount: 150000.0,
        due_date: "2025-09-01",
        company_name: "Empresa ABC",
        overdue_days: 27
    },
    status: PENDING,
    retell_agent_id: "agent_cobranza_cl"
}
```

---

### 5️⃣ **WORKER TOMA EL JOB**
```
✅ Job PENDING → [call_worker.py] → 🔄 Job IN_PROGRESS
```

**Archivo:** `call_worker.py`
**Método:** `claim_pending_job()`

**Qué sucede:**
- Worker busca job más antiguo con status PENDING
- Marca job como IN_PROGRESS
- Prepara datos para Retell AI

---

### 6️⃣ **INTEGRACIÓN CON RETELL AI**
```
🔄 Job IN_PROGRESS → [Retell API] → 📱 Llamada Real
```

**Archivos involucrados:**
- `infrastructure/retell_client.py` - Cliente para Retell AI
- `services/call_service.py` - Lógica de llamadas

**Proceso:**
1. **Preparar contexto:** Convierte `payload` a strings para Retell
2. **Crear llamada:** POST a Retell AI API
3. **Monitoreo:** WebHooks reciben eventos de llamada
4. **Actualizar status:** COMPLETED/FAILED según resultado

---

## 🏗️ ARQUITECTURA DE SERVICIOS

### **CAPA API** (Entrada)
- `api.py` - FastAPI endpoints
- `call_worker.py` - Worker para procesar jobs

### **CAPA LÓGICA DE NEGOCIO**
- `services/chile_batch_service.py` - Normalización específica de Chile
- `services/job_service.py` - CRUD consolidado
- `services/batch_service.py` - Gestión de batches  
- `services/call_service.py` - Lógica de llamadas

### **CAPA DOMINIO** (Core)
- `domain/models.py` - JobModel, ContactInfo, CallPayload
- `domain/enums.py` - JobStatus, UseCaseType, CallMode
- `domain/use_cases/debt_collection_processor.py` - Cobranza
- `domain/use_cases/marketing_processor.py` - Marketing
- `domain/use_case_registry.py` - Registry pattern

### **CAPA INFRAESTRUCTURA**
- `infrastructure/database_manager.py` - MongoDB
- `infrastructure/retell_client.py` - Retell AI API
- `config/settings.py` - Configuración

### **UTILIDADES**
- `utils/excel_processor.py` - Procesamiento Excel genérico
- `utils/helpers.py` - Funciones auxiliares

---

## 🎯 EJEMPLO COMPLETO

### **Input Excel:**
```
| RUT         | Nombre    | Telefono    | Deuda   | Fecha_Limite |
|-------------|-----------|-------------|---------|--------------|
| 12.345.678-9| Juan Pérez| 09-2125907  | 150000  | 01/09/2025   |
```

### **Endpoint Call:**
```bash
POST /api/v1/batches/chile/debt_collection
Content-Type: multipart/form-data
- file: excel.xlsx
- account_id: "cuenta123"
- company_name: "Empresa ABC"
```

### **Flujo Interno:**
1. **ChileBatchService** normaliza: RUT=123456789, phone=+56992125907
2. **DebtCollectionProcessor** crea job especializado con overdue_days=27
3. **JobService** guarda en MongoDB con status=PENDING
4. **call_worker.py** toma job y llama a Retell AI
5. **Retell AI** ejecuta llamada real al +56992125907

### **Resultado:** 
📞 **Llamada automática a Juan Pérez sobre deuda vencida**

---

## 🚀 VENTAJAS DE LA NUEVA ARQUITECTURA

1. **Extensible:** Agregar nuevo país = nuevo `{country}_batch_service.py`
2. **Modular:** Agregar caso de uso = nuevo processor en `use_cases/`
3. **Mantenible:** Cada servicio tiene responsabilidad única
4. **Testeable:** Servicios independientes, fácil testing
5. **Escalable:** N países × M casos de uso = N+M implementaciones (no N×M)

### **Próxima expansión:**
- **Argentina:** `argentina_batch_service.py` + normalización DNI
- **México:** `mexico_batch_service.py` + normalización CURP  
- **Nuevos casos:** `survey_processor.py`, `reminder_processor.py`