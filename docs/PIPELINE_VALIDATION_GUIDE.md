# 📋 Guía de Validación del Pipeline de Llamadas

## 🎯 Objetivo
Este documento te ayuda a validar el flujo completo desde que el frontend crea un batch hasta que el worker ejecuta las llamadas, verificando que los datos lleguen correctamente a Retell AI.

**📚 Documentos Relacionados:**
- **Mapeo de Variables Prompt:** `docs/RETELL_PROMPT_VARIABLES_MAPPING.md` - Mapeo detallado entre variables del prompt de Retell AI y variables del backend

---

## 🔄 Flujo Completo del Pipeline

```
Frontend → API (Excel Upload) → Batch Creation Service → MongoDB → Worker → Retell AI
```

---

## 📍 Paso 1: Creación del Batch (Frontend → API)

### Endpoint
```
POST /api/v1/batches/excel/create
```

### Logs a Buscar en la API

#### 1.1 Inicio del Request
```log
INFO | Received Excel batch creation request for account: {account_id}
INFO | Batch name: {batch_name}, Processing type: {processing_type}
INFO | File details: {file details}
```

**Qué Validar:**
- ✅ `account_id` debe ser un ID válido (no "string" ni "undefined")
- ✅ `processing_type` debe ser "basic" o "acquisition"
- ✅ El archivo Excel fue recibido correctamente

#### 1.2 Validación de Cuenta
```log
INFO | Procesando archivo Excel para cuenta {account_id}
```

**Si la cuenta no existe:**
```log
ERROR | Cuenta {account_id} no encontrada
```

**Si la cuenta no puede hacer llamadas:**
```log
ERROR | Cuenta {account_id} no puede realizar llamadas
```

---

## 📍 Paso 2: Procesamiento del Excel (BatchCreationService)

### Logs del Servicio

#### 2.1 Creación de Deudores
```log
INFO | Creando {N} deudores para batch {batch_id}
INFO | Deudores creados: {N}
```

#### 2.2 Creación de Jobs
```log
INFO | Creando jobs de llamadas para {N} deudores
INFO | _create_jobs_from_debtors iniciado: {N} deudores, account={account_id}, batch={batch_id}
```

**Logs de Cálculo de Fechas Dinámicas:**
```log
INFO | Fecha límite calculada dinámicamente: HOY + {dias_fecha_limite} días = {fecha}
INFO | Fecha máxima calculada dinámicamente: HOY + {dias_fecha_maxima} días = {fecha}
```

#### 2.3 Creación Individual de Cada Job
```log
INFO | Job creado para {rut}: {deduplication_key}, teléfono: {telefono}
```

**Ejemplo Real:**
```log
INFO | Job creado para 12345678-9: acc123::12345678-9::batch-2025-01-08-150000-ABCDEF, teléfono: +56912345678
```

#### 2.4 Inserción en MongoDB
```log
INFO | Preparados {N} jobs para insertar en DB
INFO | Deudores creados/actualizados: {N}
INFO | Jobs de llamadas creados: {N}
```

#### 2.5 Resultado Final
```log
INFO | Batch {batch_id} procesado exitosamente: {result}
```

**Estructura del `result`:**
```json
{
  "success": true,
  "batch_id": "batch-2025-01-08-150000-ABCDEF",
  "batch_name": "Campaña Enero 2025",
  "total_debtors": 100,
  "total_jobs": 100,
  "estimated_cost": 15.0,
  "duplicates_found": 0,
  "created_at": "2025-01-08T15:00:00.000Z"
}
```

---

## 📍 Paso 3: Verificación en MongoDB

### 3.1 Verificar Batch Creado
```bash
db.batches.findOne({batch_id: "batch-2025-01-08-150000-ABCDEF"})
```

**Campos Importantes:**
```json
{
  "batch_id": "batch-2025-01-08-150000-ABCDEF",
  "account_id": "acc123",
  "name": "Campaña Enero 2025",
  "total_jobs": 100,
  "pending_jobs": 100,
  "is_active": true,  // ⚠️ CRÍTICO: debe ser true para que worker procese
  "estimated_cost": 15.0,
  "call_settings": {
    "timezone": "America/Santiago",
    "days_of_week": [1, 2, 3, 4, 5],
    "allowed_hours": {
      "start": "09:00",
      "end": "18:00"
    },
    "ring_timeout": 30,
    "max_attempts": 3
  }
}
```

### 3.2 Verificar Jobs Creados
```bash
db.jobs.find({batch_id: "batch-2025-01-08-150000-ABCDEF"}).limit(1).pretty()
```

**Estructura Esperada de un Job:**
```json
{
  "_id": ObjectId("..."),
  "account_id": "acc123",
  "batch_id": "batch-2025-01-08-150000-ABCDEF",
  "status": "pending",
  "deduplication_key": "acc123::12345678-9::batch-2025-01-08-150000-ABCDEF",
  
  // Información del contacto
  "contact": {
    "name": "Juan Pérez",
    "dni": "12345678-9",
    "phones": ["+56912345678"]
  },
  
  // Datos para Retell AI
  "payload": {
    "debt_amount": 150000,
    "due_date": "2025-02-07",  // Calculada dinámicamente
    "company_name": "Empresa ABC",
    "additional_info": {
      "cantidad_cupones": 3,
      "fecha_maxima": "2025-02-22",  // Calculada dinámicamente
      "current_time_America_Santiago": "Wednesday, January 08, 2025 at 03:00:00 PM CLT"
    }
  },
  
  "mode": "single",
  "tries": 0,
  "attempts": 0,
  "created_at": ISODate("2025-01-08T15:00:00.000Z")
}
```

---

## 📍 Paso 4: Worker Procesa el Job

### 4.1 Worker Reclama el Job (claim_one)

**Logs del Worker:**
```log
[DEBUG] [worker-1] Buscando batches activos...
[DEBUG] [worker-1] Se encontraron 5 batches activos
[DEBUG] [worker-1] Batch IDs activos: ['batch-2025-01-08-150000-ABCDEF', ...]
[DEBUG] [worker-1] ✅ Job encontrado: {job_id}
[DEBUG] [worker-1] Job data: RUT=12345678-9, Status=in_progress, Attempts=1
[DEBUG] [worker-1] Phone: +56912345678, Try_phones: ['+56912345678']
```

**⚠️ Si el batch está pausado:**
```log
[DEBUG] [worker-1] ❌ No se encontraron jobs pendientes
```
Esto significa que el filtro `is_active: true` está funcionando correctamente.

### 4.2 Validación de Horarios (call_settings)

```log
[DEBUG] [{job_id}] Obteniendo configuración del batch {batch_id}...
[DEBUG] [{job_id}] ✅ Call settings encontrados: {...}
[DEBUG] [{job_id}] ✅ Dentro de horario permitido
```

**Si está fuera de horario:**
```log
[INFO] [{job_id}] 🚫 FUERA DE HORARIO PERMITIDO - Día 7 (Sunday) no está en días permitidos [1, 2, 3, 4, 5]
[DEBUG] [{job_id}] Job reprogramado para 2025-01-09T09:00:00Z
```

### 4.3 Validación de Intentos

```log
[DEBUG] [{job_id}] Intentos: 1/3
```

**Si alcanza el máximo:**
```log
[ERROR] [{job_id}] 🚫 MÁXIMO DE INTENTOS ALCANZADO (3/3)
```

### 4.4 Validación de Balance (CRÍTICO)

```log
[DEBUG] [{job_id}] ✅ Balance suficiente - Plan: minutes_based
```

**Si no hay saldo:**
```log
[ERROR] [{job_id}] 🚫 SALDO INSUFICIENTE - Plan: credit_based, Sin créditos suficientes (disponibles: 0.50, necesarios: 2.00)
```

### 4.5 Construcción del Context para Retell

```log
[DEBUG] [{job_id}] Context enviado a Retell: {context}
```

**Ejemplo de Context (Cobranza):**
```json
{
  "tipo_llamada": "cobranza",
  "nombre": "Juan Pérez",
  "RUT": "12345678-9",
  "empresa": "Je Je Group",
  "monto_total": "150000",
  "fecha_limite": "2025-02-07",
  "cantidad_cupones": "3",
  "fecha_maxima": "2025-02-22",
  "cuotas_adeudadas": "3",
  "current_time_America_Santiago": "Wednesday, January 08, 2025 at 03:00:00 PM CLT"
}
```

**📋 Mapeo con Variables del Prompt:**
| Variable Prompt | Variable Backend | Valor Ejemplo |
|----------------|------------------|---------------|
| `{{nombre}}` | `nombre` | "Juan Pérez" |
| `{{empresa}}` | `empresa` | "Je Je Group" |
| `{{cuotas_adeudadas}}` | `cuotas_adeudadas` | "3" |
| `{{monto_total}}` | `monto_total` | "150000" |
| `{{fecha_limite}}` | `fecha_limite` | "2025-02-07" |
| `{{fecha_maxima}}` | `fecha_maxima` | "2025-02-22" |
| `{{current_time_America/Santiago}}` | `current_time_America_Santiago` | "Wednesday, January 08..." |

**Ver mapeo completo:** `docs/RETELL_PROMPT_VARIABLES_MAPPING.md`

**Ejemplo de Context (Marketing):**
```json
{
  "tipo_llamada": "marketing",
  "nombre": "María González",
  "empresa": "TiendaOnline",
  "descripcion_oferta": "50% de descuento en productos seleccionados",
  "descuento_porcentaje": "50",
  "categoria_producto": "Electrónica",
  "segmento_cliente": "Premium",
  "tipo_campana": "Venta Flash",
  "llamada_accion": "Ingresa a nuestra web con el código FLASH50",
  "valor_oferta": "50000",
  "oferta_expira": "2025-01-15",
  "current_time_America_Santiago": "Wednesday, January 08, 2025 at 03:00:00 PM CLT"
}
```

### 4.6 Llamada a Retell AI

```log
INFO | [{job_id}] Llamando a +56912345678 (RUT: 12345678-9, Nombre: Juan Pérez) - agent_id=agent_abc123
[DEBUG] [{job_id}] Iniciando llamada a Retell...
[DEBUG] [{job_id}] Parámetros: phone=+56912345678, agent_id=agent_abc123, from_number=+56XXXXXXXXX
[DEBUG] [{job_id}] Usando ring_timeout del batch: 30s
```

### 4.7 Respuesta de Retell

**Llamada Exitosa:**
```log
[DEBUG] [{job_id}] Resultado Retell: success=True, error=None
[DEBUG] [{job_id}] Call_id: call_xyz789, Raw response: {...}
[DEBUG] [{job_id}] ✅ Call_id guardado: call_xyz789
```

**Error al Iniciar:**
```log
[ERROR] [{job_id}] Resultado Retell: success=False, error=Invalid phone number
[ERROR] [{job_id}] Error al iniciar llamada: Invalid phone number
```

### 4.8 Seguimiento de la Llamada

```log
[DEBUG] [{job_id}] Monitoreando llamada call_xyz789...
[DEBUG] [{job_id}] Estado actual: ongoing, duración: 45s
[DEBUG] [{job_id}] Llamada finalizada: ended, duración: 120s
```

### 4.9 Actualización de Balance

```log
[DEBUG] [{job_id}] Updating usage: 2.00 minutes for account acc123
[DEBUG] [{job_id}] ✅ Account usage updated: 2.00 minutes for acc123
[DEBUG] [{job_id}] ✅ Batch stats updated for batch batch-2025-01-08-150000-ABCDEF
```

---

## 🔍 Verificación Completa: Checklist

### ✅ Checklist de Validación

#### 1. API Recibe el Request
- [ ] Logs muestran `account_id` correcto
- [ ] `processing_type` es "basic" o "acquisition"
- [ ] Archivo Excel procesado sin errores

#### 2. Batch Creado Correctamente
- [ ] `batch_id` generado (formato: batch-YYYY-MM-DD-HHMMSS-XXXXXX)
- [ ] `total_jobs` coincide con filas del Excel
- [ ] `is_active: true` en MongoDB
- [ ] `call_settings` configurados si se enviaron

#### 3. Jobs Creados con Datos Correctos
- [ ] Cada job tiene `contact.phones` con teléfono válido
- [ ] `payload.debt_amount` o `payload.offer_description` presente
- [ ] Fechas calculadas dinámicamente si se enviaron `dias_fecha_limite`/`dias_fecha_maxima`
- [ ] `deduplication_key` generada correctamente

#### 4. Worker Procesa el Job
- [ ] Worker encuentra el job (batch debe estar activo)
- [ ] Validación de horarios pasa
- [ ] Validación de balance pasa
- [ ] Context enviado a Retell contiene todos los campos necesarios

#### 5. Retell AI Recibe la Llamada
- [ ] `retell_llm_dynamic_variables` contiene el context
- [ ] Todos los valores son strings (requerimiento de Retell)
- [ ] `agent_id` es correcto
- [ ] `from_number` configurado
- [ ] `to_number` en formato E.164

---

## 🐛 Problemas Comunes y Soluciones

### ❌ Worker no procesa jobs
**Causa:** Batch tiene `is_active: false`

**Solución:**
```bash
# Verificar estado del batch
db.batches.findOne({batch_id: "batch-XXX"}, {is_active: 1})

# Activar batch
db.batches.updateOne(
  {batch_id: "batch-XXX"},
  {$set: {is_active: true}}
)
```

### ❌ Jobs no se crean
**Causa:** Validación de duplicados o teléfonos faltantes

**Logs a buscar:**
```log
WARNING | Deudor {rut} sin teléfono válido, saltando job
ERROR | No se pudieron crear jobs de llamadas
```

**Solución:** Verificar que el Excel tenga columna `to_number` con datos válidos.

### ❌ Worker marca job como "fuera de horario"
**Causa:** `call_settings.days_of_week` o `allowed_hours` restringe la ejecución

**Solución:**
```bash
# Verificar call_settings del batch
db.batches.findOne(
  {batch_id: "batch-XXX"},
  {call_settings: 1}
)

# Remover restricciones temporalmente
db.batches.updateOne(
  {batch_id: "batch-XXX"},
  {$unset: {call_settings: ""}}
)
```

### ❌ Retell rechaza la llamada
**Causa:** Variables de context no son strings o falta información

**Validar:**
1. Revisar logs: `[DEBUG] [{job_id}] Context enviado a Retell: {...}`
2. Verificar que todos los valores sean strings
3. Confirmar que `agent_id` existe en Retell

---

## 📊 Ejemplo de Flujo Exitoso Completo

```log
# 1. API recibe request
INFO | Received Excel batch creation request for account: acc123
INFO | Batch name: Campaña Enero, Processing type: basic

# 2. Procesa Excel
INFO | Procesando archivo Excel para cuenta acc123
INFO | Creando 100 deudores para batch batch-2025-01-08-150000-ABC
INFO | Deudores creados: 100

# 3. Crea jobs
INFO | Creando jobs de llamadas para 100 deudores
INFO | Fecha límite calculada dinámicamente: HOY + 30 días = 2025-02-07
INFO | Job creado para 12345678-9: acc123::12345678-9::batch-2025-01-08-150000-ABC, teléfono: +56912345678
INFO | Preparados 100 jobs para insertar en DB
INFO | Jobs de llamadas creados: 100

# 4. Batch guardado
INFO | Batch batch-2025-01-08-150000-ABC creado con ID 6789abcd1234...
INFO | Batch batch-2025-01-08-150000-ABC procesado exitosamente

# 5. Worker reclama job
[DEBUG] [worker-1] ✅ Job encontrado: 6789abcd5678...
[DEBUG] [worker-1] Job data: RUT=12345678-9, Status=in_progress, Attempts=1

# 6. Validaciones
[DEBUG] [6789abcd5678] ✅ Call settings encontrados
[DEBUG] [6789abcd5678] ✅ Dentro de horario permitido
[DEBUG] [6789abcd5678] Intentos: 1/3
[DEBUG] [6789abcd5678] ✅ Balance suficiente - Plan: minutes_based

# 7. Context construido
[DEBUG] [6789abcd5678] Context enviado a Retell: {
  "tipo_llamada": "cobranza",
  "nombre": "Juan Pérez",
  "RUT": "12345678-9",
  "monto_total": "150000",
  "fecha_limite": "2025-02-07",
  ...
}

# 8. Llamada a Retell
INFO | [6789abcd5678] Llamando a +56912345678 (RUT: 12345678-9, Nombre: Juan Pérez)
[DEBUG] [6789abcd5678] Resultado Retell: success=True, error=None
[DEBUG] [6789abcd5678] Call_id: call_xyz789

# 9. Seguimiento
[DEBUG] [6789abcd5678] Monitoreando llamada call_xyz789...
[DEBUG] [6789abcd5678] Estado actual: ongoing, duración: 45s
[DEBUG] [6789abcd5678] Llamada finalizada: ended, duración: 120s

# 10. Actualización de balance
[DEBUG] [6789abcd5678] ✅ Account usage updated: 2.00 minutes for acc123
[DEBUG] [6789abcd5678] ✅ Batch stats updated for batch batch-2025-01-08-150000-ABC
```

---

## 🎯 Comandos Útiles para Debugging

### Ver logs de la API en tiempo real
```bash
# Si usas systemd
journalctl -u speechai-api -f

# Si corres con uvicorn directamente
# Los logs aparecen en stdout
```

### Ver logs del worker en tiempo real
```bash
# Si usas systemd
journalctl -u speechai-worker -f

# Si corres con python
python app/call_worker.py
```

### Consultas MongoDB útiles

```javascript
// Ver jobs pendientes de un batch
db.jobs.find({
  batch_id: "batch-2025-01-08-150000-ABC",
  status: "pending"
}).count()

// Ver último job procesado
db.jobs.find({status: "in_progress"}).sort({updated_at: -1}).limit(1).pretty()

// Ver jobs fallidos con errores
db.jobs.find({
  status: "failed",
  last_error: {$exists: true}
}, {
  rut: 1,
  to_number: 1,
  last_error: 1,
  tries: 1
}).pretty()

// Ver estadísticas de un batch
db.batches.findOne({batch_id: "batch-2025-01-08-150000-ABC"}, {
  total_jobs: 1,
  pending_jobs: 1,
  total_cost: 1,
  total_minutes: 1,
  completed_jobs: 1
})
```

---

## 📝 Formato de Variables para Retell AI

### Variables de Cobranza
```json
{
  "tipo_llamada": "cobranza",
  "nombre": "string",
  "RUT": "string",
  "empresa": "string",
  "monto_total": "string",
  "fecha_limite": "string (YYYY-MM-DD)",
  "cantidad_cupones": "string",
  "fecha_maxima": "string (YYYY-MM-DD)",
  "cuotas_adeudadas": "string",
  "current_time_America_Santiago": "string"
}
```

### Variables de Marketing
```json
{
  "tipo_llamada": "marketing",
  "nombre": "string",
  "empresa": "string",
  "descripcion_oferta": "string",
  "descuento_porcentaje": "string",
  "categoria_producto": "string",
  "segmento_cliente": "string",
  "tipo_campana": "string",
  "llamada_accion": "string",
  "valor_oferta": "string",
  "oferta_expira": "string (YYYY-MM-DD)",
  "current_time_America_Santiago": "string"
}
```

**⚠️ IMPORTANTE:** Retell AI requiere que TODOS los valores sean strings, incluso números y fechas.

---

## 🚀 Siguiente Paso

Una vez que hagas una creación de batch desde el frontend:

1. **Revisa los logs de la API** para confirmar que el batch y jobs se crearon
2. **Consulta MongoDB** para ver la estructura de los datos
3. **Revisa los logs del worker** para ver el process completo
4. **Confirma en Retell AI** que la llamada llegó con las variables correctas

Si encuentras algún problema, busca el log específico en esta guía para identificar en qué paso falló.
