# 🎯 Mapeo de Variables: Prompt Retell AI ↔ Backend

## 📋 Resumen
Este documento mapea las variables que usa el **prompt del agente en Retell AI** con las variables que envía el **backend (call_worker.py)** en el campo `retell_llm_dynamic_variables`.

---

## 🔍 Variables Requeridas por el Prompt

### Variables del Prompt de Cobranza

| Variable en Prompt | Descripción | Ejemplo |
|-------------------|-------------|---------|
| `{{nombre}}` | Nombre del cliente | "Juan Pérez" |
| `{{empresa}}` | Empresa acreedora | "Je Je Group" |
| `{{cuotas_adeudadas}}` | Número de cuotas pendientes | "3" |
| `{{monto_total}}` | Monto total de la deuda | "150000" |
| `{{fecha_limite}}` | Fecha límite sin recargo | "2025-02-07" |
| `{{fecha_maxima}}` | Fecha máxima para compromiso | "2025-02-22" |
| `{{current_time_America/Santiago}}` | Hora actual Chile para cálculo de fechas relativas | "Wednesday, January 08, 2025 at 03:00:00 PM CLT" |

---

## ✅ Variables Enviadas por el Backend

### Desde `call_worker.py` → Función `_context_from_job()`

El backend construye el context desde el job con esta estructura:

```python
context = {
    'tipo_llamada': 'cobranza',
    'nombre': str(contact_data.get('name', '')),           # ✅ Mapea a {{nombre}}
    'RUT': str(contact_data.get('dni', '')),
    'empresa': str(payload_data.get('company_name', '')),   # ✅ Mapea a {{empresa}}
    'monto_total': str(payload_data.get('debt_amount', '')),# ✅ Mapea a {{monto_total}}
    'fecha_limite': str(payload_data.get('due_date', '')), # ✅ Mapea a {{fecha_limite}}
    'cantidad_cupones': str(additional_info.get('cantidad_cupones', '')),
    'cuotas_adeudadas': str(additional_info.get('cantidad_cupones', '')), # ✅ Mapea a {{cuotas_adeudadas}}
    'fecha_maxima': str(additional_info.get('fecha_maxima', '')),         # ✅ Mapea a {{fecha_maxima}}
    'current_time_America_Santiago': now_chile             # ✅ Mapea a {{current_time_America/Santiago}}
}
```

### 📊 Tabla de Mapeo Completo

| Variable Prompt | Variable Backend | Origen de los Datos | Validación |
|----------------|------------------|---------------------|------------|
| `{{nombre}}` | `nombre` | `job.contact.name` | ✅ CORRECTO |
| `{{empresa}}` | `empresa` | `job.payload.company_name` | ✅ CORRECTO |
| `{{cuotas_adeudadas}}` | `cuotas_adeudadas` | `job.payload.additional_info.cantidad_cupones` | ✅ CORRECTO |
| `{{monto_total}}` | `monto_total` | `job.payload.debt_amount` | ✅ CORRECTO |
| `{{fecha_limite}}` | `fecha_limite` | `job.payload.due_date` | ✅ CORRECTO |
| `{{fecha_maxima}}` | `fecha_maxima` | `job.payload.additional_info.fecha_maxima` | ✅ CORRECTO |
| `{{current_time_America/Santiago}}` | `current_time_America_Santiago` | Generado por `chile_time_display()` | ✅ CORRECTO |

**Nota sobre el slash:** El prompt usa `{{current_time_America/Santiago}}` pero el backend envía `current_time_America_Santiago` (con guión bajo). Retell AI acepta ambos formatos.

---

## 🔄 Flujo de Datos Completo

### 1️⃣ Excel → API → BatchCreationService

**Excel (columnas):**
```
nombre | rut | to_number | monto_total | origen_empresa | cantidad_cupones
```

**BatchCreationService crea el job con:**
```python
job = JobModel(
    contact=ContactInfo(
        name=debtor['nombre'],           # → {{nombre}}
        dni=debtor['rut'],
        phones=[debtor['to_number']]
    ),
    payload=CallPayload(
        debt_amount=debtor['monto_total'],      # → {{monto_total}}
        due_date=fecha_limite_calculada,        # → {{fecha_limite}}
        company_name=debtor['origen_empresa'],  # → {{empresa}}
        additional_info={
            'cantidad_cupones': debtor['cantidad_cupones'],  # → {{cuotas_adeudadas}}
            'fecha_maxima': fecha_maxima_calculada          # → {{fecha_maxima}}
        }
    )
)
```

### 2️⃣ Worker → Retell AI

**Worker llama a `_context_from_job()` y obtiene:**
```json
{
  "tipo_llamada": "cobranza",
  "nombre": "Juan Pérez",
  "RUT": "12345678-9",
  "empresa": "Je Je Group",
  "monto_total": "150000",
  "fecha_limite": "2025-02-07",
  "cantidad_cupones": "3",
  "cuotas_adeudadas": "3",
  "fecha_maxima": "2025-02-22",
  "current_time_America_Santiago": "Wednesday, January 08, 2025 at 03:00:00 PM CLT"
}
```

**Retell AI recibe en el request:**
```json
{
  "from_number": "+56XXXXXXXXX",
  "to_number": "+56912345678",
  "agent_id": "agent_abc123",
  "retell_llm_dynamic_variables": {
    "tipo_llamada": "cobranza",
    "nombre": "Juan Pérez",
    "RUT": "12345678-9",
    "empresa": "Je Je Group",
    "monto_total": "150000",
    "fecha_limite": "2025-02-07",
    "cantidad_cupones": "3",
    "cuotas_adeudadas": "3",
    "fecha_maxima": "2025-02-22",
    "current_time_America_Santiago": "Wednesday, January 08, 2025 at 03:00:00 PM CLT"
  }
}
```

### 3️⃣ Retell AI usa el Prompt

El agente reemplaza las variables en el prompt:

```
Hi, is this Juan Pérez?
If yes continue.
I am Sofía from Je Je Group, collections for Je Je Group in Chile.

I am calling about your debt with Je Je Group, with 3 pending installments, 
total 150000 pesos. You can pay without extra charges until 2025-02-07.

...

If the client says they cannot pay by 2025-02-07, ask again for the exact date 
and amount. Accept the commitment only if the date is not later than 2025-02-22.

...

If the client uses relative dates like tomorrow or Monday convert to exact Chile 
date based on Wednesday, January 08, 2025 at 03:00:00 PM CLT, and then restate 
it in natural spoken format.
```

---

## 📝 Validación de Tipos de Datos

### ⚠️ Requerimiento Crítico de Retell AI

**Retell AI requiere que TODAS las variables sean strings**, incluso números y fechas.

#### ✅ Validación del Backend

El worker convierte todo a string explícitamente:

```python
context.update({
    'empresa': str(payload_data.get('company_name', '')),      # ✅ String
    'monto_total': str(payload_data.get('debt_amount', '')),   # ✅ String (era número)
    'fecha_limite': str(payload_data.get('due_date', '')),     # ✅ String (era fecha)
    'cantidad_cupones': str(additional_info.get('cantidad_cupones', '')), # ✅ String (era número)
    'cuotas_adeudadas': str(additional_info.get('cantidad_cupones', '')), # ✅ String (era número)
    'fecha_maxima': str(additional_info.get('fecha_maxima', '')),         # ✅ String (era fecha)
})
```

#### ❌ Ejemplo de Error (si no se convierte)

```json
{
  "monto_total": 150000,           // ❌ Número - Retell rechazará
  "cantidad_cupones": 3,           // ❌ Número - Retell rechazará
  "fecha_limite": "2025-02-07"     // ✅ String - OK
}
```

#### ✅ Formato Correcto

```json
{
  "monto_total": "150000",         // ✅ String
  "cantidad_cupones": "3",         // ✅ String
  "fecha_limite": "2025-02-07"     // ✅ String
}
```

---

## 🔍 Cómo Validar en Logs

### Logs del Worker

Busca esta línea en los logs del worker:

```log
[DEBUG] [{job_id}] Context enviado a Retell: {
  "tipo_llamada": "cobranza",
  "nombre": "Juan Pérez",
  "RUT": "12345678-9",
  "empresa": "Je Je Group",
  "monto_total": "150000",
  "fecha_limite": "2025-02-07",
  "cantidad_cupones": "3",
  "cuotas_adeudadas": "3",
  "fecha_maxima": "2025-02-22",
  "current_time_America_Santiago": "Wednesday, January 08, 2025 at 03:00:00 PM CLT"
}
```

**Checklist de Validación:**
- [ ] ✅ Todas las variables están presentes
- [ ] ✅ Todos los valores son strings (entre comillas)
- [ ] ✅ No hay valores vacíos ni `null`
- [ ] ✅ Las fechas están en formato YYYY-MM-DD
- [ ] ✅ `current_time_America_Santiago` tiene formato legible

---

## 🐛 Problemas Comunes

### ❌ Problema 1: Variables Faltantes

**Síntoma:** El agente no menciona la empresa o el monto

**Causa:** Excel no tiene la columna `origen_empresa` o `monto_total`

**Solución:** Verificar que el Excel tenga todas las columnas requeridas:
```
nombre, rut, to_number, monto_total, origen_empresa, cantidad_cupones
```

### ❌ Problema 2: Fechas No Calculadas

**Síntoma:** `fecha_limite` o `fecha_maxima` están vacías

**Causa:** No se enviaron `dias_fecha_limite` o `dias_fecha_maxima` en el request

**Logs a buscar:**
```log
INFO | Fecha límite calculada dinámicamente: HOY + 30 días = 2025-02-07
INFO | Fecha máxima calculada dinámicamente: HOY + 45 días = 2025-02-22
```

**Solución:** Asegurar que el frontend envíe estos parámetros en el POST:
```javascript
const formData = new FormData();
formData.append('file', excelFile);
formData.append('account_id', accountId);
formData.append('batch_name', batchName);
formData.append('processing_type', 'basic');
formData.append('dias_fecha_limite', 30);    // ← IMPORTANTE
formData.append('dias_fecha_maxima', 45);    // ← IMPORTANTE
```

### ❌ Problema 3: Tipos Incorrectos

**Síntoma:** Retell rechaza la llamada con error "Invalid dynamic variables"

**Causa:** Alguna variable no es string

**Solución:** Verificar en logs que todos los valores estén entre comillas:
```json
"monto_total": "150000"   // ✅ Correcto
"monto_total": 150000     // ❌ Incorrecto
```

---

## 📊 Ejemplo Completo de Validación

### Job en MongoDB
```json
{
  "_id": ObjectId("6789abcd1234..."),
  "account_id": "acc123",
  "batch_id": "batch-2025-01-08-150000-ABC",
  "status": "pending",
  "contact": {
    "name": "Juan Pérez",          // ✅ → {{nombre}}
    "dni": "12345678-9",
    "phones": ["+56912345678"]
  },
  "payload": {
    "debt_amount": 150000,          // ✅ → {{monto_total}}
    "due_date": "2025-02-07",       // ✅ → {{fecha_limite}}
    "company_name": "Je Je Group",  // ✅ → {{empresa}}
    "additional_info": {
      "cantidad_cupones": 3,        // ✅ → {{cuotas_adeudadas}}
      "fecha_maxima": "2025-02-22"  // ✅ → {{fecha_maxima}}
    }
  }
}
```

### Context Enviado a Retell
```json
{
  "tipo_llamada": "cobranza",
  "nombre": "Juan Pérez",                     // ✅ String
  "RUT": "12345678-9",                        // ✅ String
  "empresa": "Je Je Group",                   // ✅ String
  "monto_total": "150000",                    // ✅ String (convertido de número)
  "fecha_limite": "2025-02-07",               // ✅ String
  "cantidad_cupones": "3",                    // ✅ String (convertido de número)
  "cuotas_adeudadas": "3",                    // ✅ String (convertido de número)
  "fecha_maxima": "2025-02-22",               // ✅ String
  "current_time_America_Santiago": "Wednesday, January 08, 2025 at 03:00:00 PM CLT"  // ✅ String
}
```

### Prompt Renderizado
```
Hi, is this Juan Pérez?

I am Sofía from Je Je Group, collections for Je Je Group in Chile.

I am calling about your debt with Je Je Group, with 3 pending installments, 
total 150000 pesos. You can pay without extra charges until 2025-02-07.

If the client says they cannot pay by 2025-02-07, ask again for the exact date 
and amount. Accept the commitment only if the date is not later than 2025-02-22.
```

✅ **Todas las variables fueron reemplazadas correctamente**

---

## 🎯 Checklist Final de Validación

### Para Desarrolladores Frontend

- [ ] Excel tiene columnas: `nombre`, `rut`, `to_number`, `monto_total`, `origen_empresa`, `cantidad_cupones`
- [ ] POST incluye `dias_fecha_limite` y `dias_fecha_maxima` si se requiere cálculo dinámico
- [ ] POST incluye `processing_type: "basic"` para cobranza

### Para Validación en Backend

- [ ] Logs API muestran: "Fecha límite calculada dinámicamente"
- [ ] Logs API muestran: "Jobs de llamadas creados: N"
- [ ] MongoDB: Jobs tienen `contact.phones` válidos
- [ ] MongoDB: Jobs tienen `payload.debt_amount` y `payload.company_name`
- [ ] MongoDB: Jobs tienen `payload.additional_info.fecha_maxima`

### Para Validación en Worker

- [ ] Worker encuentra jobs (batch debe estar activo)
- [ ] Log muestra: "Context enviado a Retell" con todas las variables
- [ ] Todas las variables son strings (entre comillas en JSON)
- [ ] Log muestra: "Resultado Retell: success=True"
- [ ] Log muestra: "Call_id: call_xyz789"

---

## 📞 Contacto de Soporte

Si alguna variable no se está enviando correctamente:

1. Revisa logs de API: ¿Se creó el job con los datos correctos?
2. Revisa MongoDB: ¿El job tiene la estructura esperada?
3. Revisa logs del worker: ¿El context tiene todas las variables?
4. Verifica en Retell AI: ¿La llamada llegó con las variables?

Para debugging adicional, consulta: `docs/PIPELINE_VALIDATION_GUIDE.md`
