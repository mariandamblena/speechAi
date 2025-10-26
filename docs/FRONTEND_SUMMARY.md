# 📊 Resumen Ejecutivo - Requerimientos Frontend

## ✅ Estado del Backend

**Fecha:** 26 de Octubre, 2025  
**Sistema:** SpeechAI - Sistema de Llamadas Automatizadas  
**Estado Backend:** ✅ **100% FUNCIONAL Y LISTO**

---

## 🎯 Qué Funciona Actualmente

✅ **Creación de batches desde Excel** - Endpoint operativo  
✅ **Procesamiento de contactos** - 12 jobs creados exitosamente en último test  
✅ **Deduplicación de contactos** - Sistema anti-duplicados funcionando  
✅ **Worker procesando jobs** - Sistema de llamadas operativo  
✅ **Integración con Retell AI** - Variables mapeadas correctamente  

---

## ⚠️ Qué Falta Implementar en el Frontend

### 🔴 **CRÍTICO - Implementar YA**

#### **1. Enviar Configuración de Llamadas (`call_settings_json`)**

**Problema actual:**
```log
2025-10-26 13:56:46 | Batch batch-2025-10-26-135646-520145 creado
❌ call_settings: null
```

Sin esto, las llamadas se ejecutan **24/7 sin restricciones** (incluye fines de semana y horarios nocturnos).

**Solución:**
```javascript
// Capturar del formulario "Configuración de Llamadas"
const callSettings = {
  max_call_duration: 300,           // Duración Máxima
  ring_timeout: 30,                 // Tiempo de Timbrado
  max_attempts: 3,                  // Intentos Máximos
  retry_delay_hours: 24,            // Horas entre Intentos
  timezone: "America/Santiago",     // Zona Horaria
  days_of_week: [1, 2, 3, 4, 5],   // Lun-Vie
  allowed_hours: {
    start: "09:00",                 // Hora de Inicio
    end: "18:00"                    // Hora de Fin
  },
  priority: "low"                   // Prioridad
};

// Agregar al FormData
formData.append('call_settings_json', JSON.stringify(callSettings));
```

---

#### **2. Especificar Tipo de Procesamiento (`processing_type`)**

**Problema actual:**
No se envía el tipo de campaña (cobranza vs marketing).

**Solución:**
```javascript
formData.append('processing_type', 'basic');  // o 'acquisition'
```

---

### 🟡 **IMPORTANTE - Implementar Esta Semana**

#### **3. Cálculo Dinámico de Fechas**

**Objetivo:**
Permitir que el usuario ingrese **número de días** para calcular:
- `fecha_limite`: Fecha hasta la cual puede pagar sin recargos
- `fecha_maxima`: Fecha máxima para aceptar compromiso de pago

**Propuesta de UI:**
```
┌─────────────────────────────────────────┐
│ Configuración de Fechas                 │
│                                         │
│ Días para Fecha Límite:     [30] días │
│ Resultado: 25 de noviembre, 2025       │
│                                         │
│ Días para Fecha Máxima:     [45] días │
│ Resultado: 10 de diciembre, 2025       │
└─────────────────────────────────────────┘
```

**Implementación:**
```javascript
formData.append('dias_fecha_limite', 30);  // HOY + 30 días
formData.append('dias_fecha_maxima', 45);  // HOY + 45 días
```

**Logs esperados:**
```log
INFO | Fecha límite calculada: HOY + 30 días = 2025-11-25
INFO | Fecha máxima calculada: HOY + 45 días = 2025-12-10
```

---

#### **4. Persistencia de Configuración**

**Objetivo:**
Reutilizar la configuración del batch anterior al crear uno nuevo.

**Nuevo Endpoint Disponible:**
```
GET /api/v1/accounts/{account_id}/last-call-settings
```

**Respuesta:**
```json
{
  "success": true,
  "call_settings": {
    "max_call_duration": 300,
    "ring_timeout": 30,
    "max_attempts": 3,
    "retry_delay_hours": 24,
    "timezone": "America/Santiago",
    "days_of_week": [1, 2, 3, 4, 5],
    "allowed_hours": {
      "start": "09:00",
      "end": "18:00"
    },
    "priority": "low"
  },
  "from_batch": "batch-2025-10-26-135646-520145",
  "created_at": "2025-10-26T16:56:46.650744"
}
```

**Implementación:**
```javascript
// Al abrir formulario "Configuración de Llamadas"
async function cargarConfiguracionAnterior() {
  const response = await fetch(
    `/api/v1/accounts/${accountId}/last-call-settings`
  );
  const data = await response.json();
  
  if (data.success && data.call_settings) {
    // Pre-llenar formulario con configuración anterior
    setDuracionMaxima(data.call_settings.max_call_duration);
    setTiempoTimbrado(data.call_settings.ring_timeout);
    // ... etc
  }
}
```

---

## 📋 Checklist de Implementación

### **Para el Desarrollador Frontend:**

**Alta Prioridad (Esta Semana):**
- [ ] Capturar valores del formulario "Configuración de Llamadas"
- [ ] Construir objeto `callSettings` con todos los campos
- [ ] Agregar `call_settings_json` al FormData como JSON string
- [ ] Agregar campo `processing_type` al FormData
- [ ] Probar creación de batch y verificar logs del backend
- [ ] Verificar en MongoDB que `call_settings` se guardaron

**Media Prioridad (Próxima Semana):**
- [ ] Agregar UI para "Días para Fecha Límite" y "Días para Fecha Máxima"
- [ ] Agregar campos `dias_fecha_limite` y `dias_fecha_maxima` al FormData
- [ ] Implementar función para cargar configuración anterior
- [ ] Integrar endpoint `/last-call-settings` al abrir formulario
- [ ] Agregar validaciones antes de enviar

---

## 🔍 Cómo Validar que Funciona

### **1. Crear batch con configuración completa**

**Request del Frontend:**
```javascript
POST /api/v1/batches/excel/create
FormData {
  file: archivo.xlsx,
  account_id: "retail_express",
  batch_name: "Campaña Test",
  processing_type: "basic",                    // ← NUEVO
  allow_duplicates: false,
  call_settings_json: '{"max_call_duration":300,...}',  // ← NUEVO
  dias_fecha_limite: 30,                       // ← NUEVO (opcional)
  dias_fecha_maxima: 45                        // ← NUEVO (opcional)
}
```

**Logs esperados en el backend:**
```log
INFO | 📥 Recibiendo request para crear batch desde Excel
INFO |    - account_id: 'retail_express'
INFO |    - batch_name: 'Campaña Test'
INFO |    - processing_type: 'basic'           ← ✅ DEBE APARECER
INFO |    - call_settings: {...}               ← ✅ DEBE APARECER
INFO |    - dias_fecha_limite: 30              ← ✅ DEBE APARECER
INFO |    - dias_fecha_maxima: 45              ← ✅ DEBE APARECER
INFO | Fecha límite calculada dinámicamente: HOY + 30 días = 2025-11-25
INFO | Fecha máxima calculada dinámicamente: HOY + 45 días = 2025-12-10
INFO | Batch batch-2025-10-26-... procesado exitosamente
```

### **2. Verificar en MongoDB**

```javascript
// Batch debe tener call_settings
db.batches.findOne({batch_id: "batch-2025-10-26-..."})

// Resultado esperado:
{
  "batch_id": "batch-2025-10-26-...",
  "call_settings": {                    // ← ✅ DEBE EXISTIR
    "max_call_duration": 300,
    "ring_timeout": 30,
    "max_attempts": 3,
    "retry_delay_hours": 24,
    "timezone": "America/Santiago",
    "days_of_week": [1, 2, 3, 4, 5],
    "allowed_hours": {
      "start": "09:00",
      "end": "18:00"
    }
  }
}
```

### **3. Verificar Worker respeta horarios**

**Logs del worker:**
```log
[DEBUG] [{job_id}] ✅ Call settings encontrados
[DEBUG] [{job_id}] ✅ Dentro de horario permitido
```

**Si está fuera de horario:**
```log
[INFO] [{job_id}] 🚫 FUERA DE HORARIO - Día 6 (Saturday) no permitido
[DEBUG] [{job_id}] Job reprogramado para 2025-10-28T09:00:00Z
```

---

## 📚 Documentación de Referencia

### **Para el Frontend:**
1. **`docs/FRONTEND_MISSING_REQUIREMENTS.md`** ← **LEER PRIMERO**
   - Requerimientos detallados
   - Ejemplos de código completos
   - Mapeo de campos del formulario
   - Validaciones requeridas

2. **`docs/API_FRONTEND_REFERENCE.md`**
   - Referencia completa de endpoints
   - Ejemplos de uso con curl
   - Códigos de error

3. **`docs/RETELL_PROMPT_VARIABLES_MAPPING.md`**
   - Mapeo de variables para Retell AI
   - Qué columnas debe tener el Excel

### **Para Validación:**
4. **`docs/PIPELINE_VALIDATION_GUIDE.md`**
   - Cómo validar el flujo completo
   - Logs esperados en cada paso
   - Comandos MongoDB útiles

5. **`docs/PIPELINE_VALIDATION_SUMMARY.md`**
   - Resumen ejecutivo de validación
   - Checklist paso a paso
   - Problemas comunes y soluciones

---

## 🎯 Ejemplo de Request Completo

```javascript
// Al presionar "Crear Campaña"
async function crearBatch() {
  // 1. Capturar configuración de llamadas
  const callSettings = {
    max_call_duration: parseInt(duracionMaxima),      // 300
    ring_timeout: parseInt(tiempoTimbrado),           // 30
    max_attempts: parseInt(intentosMaximos),          // 3
    retry_delay_hours: parseInt(horasEntreIntentos),  // 24
    timezone: zonaHoraria,                            // "America/Santiago"
    days_of_week: diasSeleccionados,                  // [1, 2, 3, 4, 5]
    allowed_hours: {
      start: horaInicio,                              // "09:00"
      end: horaFin                                    // "18:00"
    },
    priority: prioridad                               // "low"
  };
  
  // 2. Construir FormData
  const formData = new FormData();
  formData.append('file', archivoExcel);
  formData.append('account_id', accountId);
  formData.append('batch_name', batchName);
  formData.append('processing_type', 'basic');
  formData.append('allow_duplicates', allowDuplicates);
  
  // ← CRÍTICO: Enviar call_settings
  formData.append('call_settings_json', JSON.stringify(callSettings));
  
  // ← OPCIONAL: Cálculo dinámico de fechas
  if (diasFechaLimite > 0) {
    formData.append('dias_fecha_limite', diasFechaLimite);
  }
  if (diasFechaMaxima > 0) {
    formData.append('dias_fecha_maxima', diasFechaMaxima);
  }
  
  // 3. Enviar request
  const response = await fetch('/api/v1/batches/excel/create', {
    method: 'POST',
    body: formData
  });
  
  const result = await response.json();
  
  if (result.success) {
    console.log('✅ Batch creado:', result.batch_id);
    console.log('   Total jobs:', result.total_jobs);
    console.log('   Costo estimado:', result.estimated_cost);
  }
}
```

---

## 🚀 Próximos Pasos

### **Hoy (26 de Octubre):**
1. ✅ Lee `docs/FRONTEND_MISSING_REQUIREMENTS.md`
2. ✅ Identifica dónde capturar valores del formulario
3. ✅ Implementa construcción de objeto `callSettings`

### **Esta Semana:**
4. ✅ Agrega `call_settings_json` al FormData
5. ✅ Agrega `processing_type` al FormData
6. ✅ Prueba creación de batch
7. ✅ Valida logs del backend
8. ✅ Confirma `call_settings` en MongoDB

### **Próxima Semana:**
9. ✅ Agrega UI para días de fechas dinámicas
10. ✅ Implementa carga de configuración anterior
11. ✅ Integra endpoint `/last-call-settings`
12. ✅ Agrega validaciones del formulario

---

## ⚠️ Impacto de No Implementar

### **Sin `call_settings`:**
- ❌ Llamadas se ejecutan 24/7 (incluye fines de semana y madrugadas)
- ❌ No se respetan horarios laborales
- ❌ Posibles quejas de clientes por llamadas fuera de horario
- ❌ Consumo innecesario de créditos

### **Sin `dias_fecha_limite` / `dias_fecha_maxima`:**
- ⚠️ Fechas deben estar en el Excel manualmente
- ⚠️ Más trabajo manual para operaciones
- ⚠️ Posibles errores al calcular fechas

### **Sin persistencia de configuración:**
- ⚠️ Usuario debe reconfigurar todo en cada batch
- ⚠️ Pérdida de tiempo operativo
- ⚠️ Mayor probabilidad de errores de configuración

---

## ✅ Estado de Endpoints Backend

| Endpoint | Estado | Descripción |
|----------|--------|-------------|
| `POST /api/v1/batches/excel/create` | ✅ Funcional | Crear batch desde Excel |
| `GET /api/v1/accounts/{id}/last-call-settings` | ✅ NUEVO | Obtener última configuración |
| `GET /api/v1/batches` | ✅ Funcional | Listar batches |
| `GET /api/v1/batches/{id}` | ✅ Funcional | Obtener batch específico |
| `PATCH /api/v1/batches/{id}` | ✅ Funcional | Actualizar batch (pausar/reanudar) |
| `DELETE /api/v1/batches/{id}` | ✅ Funcional | Eliminar batch |

---

**¿Dudas o preguntas?**  
Consulta `docs/FRONTEND_MISSING_REQUIREMENTS.md` para detalles completos de implementación.

**Fecha de entrega sugerida:** 🗓️ 30 de Octubre, 2025
