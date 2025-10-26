# 📋 Requerimientos Faltantes - Frontend SpeechAI

## 🎯 Resumen Ejecutivo

Este documento detalla las funcionalidades que el **frontend debe implementar** para completar la integración del sistema de creación de batches con configuración de llamadas y cálculo dinámico de fechas.

**Fecha:** 26 de Octubre, 2025  
**Estado:** ⚠️ PENDIENTE DE IMPLEMENTACIÓN EN FRONTEND  
**Prioridad:** 🔴 ALTA

---

## ⚠️ Problema Actual Detectado

Al crear batches desde el frontend, se envían los siguientes datos:

```javascript
POST /api/v1/batches/excel/create
FormData {
  file: archivo.xlsx,
  account_id: "retail_express",
  batch_name: "HHJHJHJ",
  allow_duplicates: true
}
```

### ❌ **Faltan estos datos críticos:**

1. **`call_settings_json`** - Configuración de llamadas del formulario
2. **`dias_fecha_limite`** - Días para calcular fecha límite de pago
3. **`dias_fecha_maxima`** - Días para calcular fecha máxima de compromiso
4. **`processing_type`** - Tipo de procesamiento ("basic" o "acquisition")

**Impacto:**
- ❌ Las llamadas se ejecutan **24/7 sin restricciones** (ignora horarios configurados)
- ❌ Las fechas no se calculan dinámicamente
- ❌ La configuración no se guarda para reutilizar en el siguiente batch

---

## ✅ REQUERIMIENTO 1: Enviar Configuración de Llamadas

### 📸 **Pantalla: "Configuración de Llamadas"**

Tu frontend tiene este formulario:

```
┌────────────────────────────────────────────────────────┐
│ Configuración de Llamadas                              │
│                                                        │
│ Duración Máxima (segundos):        300                │
│ Tiempo de Timbrado (segundos):     30                 │
│ Intentos Máximos:                  3                  │
│ Horas entre Intentos:              24                 │
│ Hora de Inicio:                    09:00 AM           │
│ Hora de Fin:                       06:00 PM           │
│ Días de la Semana:    ☑Lun ☑Mar ☑Mie ☑Jue ☑Vie      │
│ Zona Horaria:         Santiago (GMT-3)                │
│ Prioridad:            Baja                            │
│                                                        │
│         [Anterior]              [Crear Campaña]       │
└────────────────────────────────────────────────────────┘
```

### 🔧 **Implementación Requerida**

Cuando el usuario presiona **"Crear Campaña"**, el frontend debe capturar estos valores y agregarlos al `FormData`:

```javascript
// 1. Capturar valores del formulario de configuración
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
  priority: prioridad                               // "low", "medium", "high"
};

// 2. Crear el FormData con TODOS los campos
const formData = new FormData();
formData.append('file', archivoExcel);
formData.append('account_id', accountId);
formData.append('batch_name', batchName);
formData.append('processing_type', 'basic');      // ← NUEVO: Tipo de procesamiento
formData.append('allow_duplicates', allowDuplicates);

// ← CRÍTICO: Enviar call_settings como JSON string
formData.append('call_settings_json', JSON.stringify(callSettings));

// 3. Enviar el request
const response = await fetch('/api/v1/batches/excel/create', {
  method: 'POST',
  body: formData
});
```

### 📊 **Mapeo de Campos del Formulario**

| Campo del Formulario | Variable Backend | Tipo | Ejemplo |
|---------------------|------------------|------|---------|
| Duración Máxima (segundos) | `max_call_duration` | `number` | `300` |
| Tiempo de Timbrado (segundos) | `ring_timeout` | `number` | `30` |
| Intentos Máximos | `max_attempts` | `number` | `3` |
| Horas entre Intentos | `retry_delay_hours` | `number` | `24` |
| Hora de Inicio | `allowed_hours.start` | `string` | `"09:00"` |
| Hora de Fin | `allowed_hours.end` | `string` | `"18:00"` |
| Días Permitidos | `days_of_week` | `number[]` | `[1,2,3,4,5]` |
| Zona Horaria | `timezone` | `string` | `"America/Santiago"` |
| Prioridad | `priority` | `string` | `"low"` / `"medium"` / `"high"` |

### 🔢 **Mapeo de Días de la Semana**

```javascript
const diasSemanaMap = {
  'Lun': 1,
  'Mar': 2,
  'Mie': 3,
  'Jue': 4,
  'Vie': 5,
  'Sab': 6,
  'Dom': 7
};

// Ejemplo: Si usuario selecciona Lun, Mar, Mie, Jue, Vie
const diasSeleccionados = [1, 2, 3, 4, 5];
```

---

## ✅ REQUERIMIENTO 2: Cálculo Dinámico de Fechas

### 🎯 **Objetivo**

Permitir que el usuario ingrese **días a sumar** para calcular automáticamente:
- **Fecha Límite** (`fecha_limite`): Fecha hasta la cual puede pagar sin recargos
- **Fecha Máxima** (`fecha_maxima`): Fecha máxima para aceptar compromiso de pago

### 📸 **Propuesta de UI: Agregar Campo en el Formulario**

```
┌────────────────────────────────────────────────────────┐
│ Configuración de Fechas                                │
│                                                        │
│ Días para Fecha Límite:           30 días            │
│   (Se suma a la fecha actual)                         │
│   Resultado: 25 de noviembre, 2025                    │
│                                                        │
│ Días para Fecha Máxima:           45 días            │
│   (Se suma a la fecha actual)                         │
│   Resultado: 10 de diciembre, 2025                    │
│                                                        │
│ ℹ️ Las fechas se calculan automáticamente para cada   │
│    contacto al crear el batch                         │
└────────────────────────────────────────────────────────┘
```

### 🔧 **Implementación Requerida**

```javascript
// 1. Capturar valores del formulario
const diasFechaLimite = parseInt(inputDiasFechaLimite);  // 30
const diasFechaMaxima = parseInt(inputDiasFechaMaxima);  // 45

// 2. Agregar al FormData
const formData = new FormData();
// ... otros campos ...

// ← NUEVO: Días para cálculo dinámico de fechas
if (diasFechaLimite > 0) {
  formData.append('dias_fecha_limite', diasFechaLimite);
}

if (diasFechaMaxima > 0) {
  formData.append('dias_fecha_maxima', diasFechaMaxima);
}

// 3. Mostrar preview de fechas calculadas (opcional)
const hoy = new Date();
const fechaLimiteCalculada = new Date(hoy);
fechaLimiteCalculada.setDate(hoy.getDate() + diasFechaLimite);

const fechaMaximaCalculada = new Date(hoy);
fechaMaximaCalculada.setDate(hoy.getDate() + diasFechaMaxima);

console.log('Fecha Límite:', fechaLimiteCalculada.toLocaleDateString('es-CL'));
console.log('Fecha Máxima:', fechaMaximaCalculada.toLocaleDateString('es-CL'));
```

### 📋 **Ejemplo de FormData Completo**

```javascript
const formData = new FormData();
formData.append('file', archivoExcel);
formData.append('account_id', 'retail_express');
formData.append('batch_name', 'Campaña Enero 2025');
formData.append('processing_type', 'basic');
formData.append('allow_duplicates', false);

// Configuración de llamadas
const callSettings = {
  max_call_duration: 300,
  ring_timeout: 30,
  max_attempts: 3,
  retry_delay_hours: 24,
  timezone: "America/Santiago",
  days_of_week: [1, 2, 3, 4, 5],
  allowed_hours: {
    start: "09:00",
    end: "18:00"
  },
  priority: "low"
};
formData.append('call_settings_json', JSON.stringify(callSettings));

// Cálculo dinámico de fechas
formData.append('dias_fecha_limite', 30);
formData.append('dias_fecha_maxima', 45);
```

### 📊 **Cómo Funciona el Backend**

Cuando recibe `dias_fecha_limite` y `dias_fecha_maxima`, el backend:

```python
# Para cada contacto en el Excel:
hoy = datetime.utcnow()

# Calcula fecha_limite
fecha_limite = hoy + timedelta(days=30)  # "2025-11-25"

# Calcula fecha_maxima
fecha_maxima = hoy + timedelta(days=45)  # "2025-12-10"

# Las guarda en el job
job.payload.due_date = "2025-11-25"
job.payload.additional_info.fecha_maxima = "2025-12-10"
```

**Logs que verás:**
```log
INFO | Fecha límite calculada dinámicamente: HOY + 30 días = 2025-11-25
INFO | Fecha máxima calculada dinámicamente: HOY + 45 días = 2025-12-10
```

---

## ✅ REQUERIMIENTO 3: Persistencia de Configuración

### 🎯 **Objetivo**

Que la configuración de llamadas se guarde automáticamente y se reutilice en el siguiente batch.

### 🔧 **Flujo Deseado**

1. **Usuario crea primer batch:**
   - Configura horarios: 09:00 - 18:00
   - Configura días: Lun-Vie
   - Configura intentos: 3
   - Presiona "Crear Campaña"
   - ✅ Backend guarda estos `call_settings` en el batch

2. **Usuario va a crear segundo batch:**
   - Abre el formulario de "Configuración de Llamadas"
   - ✅ **El formulario se pre-llena con la configuración anterior**
   - Usuario puede modificar o dejar igual
   - Presiona "Crear Campaña"

### 📡 **Endpoint Requerido (Ya Existe en Backend)**

#### **Obtener última configuración de una cuenta:**

```javascript
// GET /api/v1/accounts/{account_id}/last-call-settings
const response = await fetch(
  `/api/v1/accounts/${accountId}/last-call-settings`,
  { method: 'GET' }
);

const data = await response.json();

// Respuesta:
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
  "from_batch": "batch-2025-10-26-135646-520145"
}
```

### 🔧 **Implementación en Frontend**

```javascript
// 1. Al abrir el formulario de "Configuración de Llamadas"
async function cargarConfiguracionAnterior() {
  try {
    const response = await fetch(
      `/api/v1/accounts/${accountId}/last-call-settings`
    );
    
    const data = await response.json();
    
    if (data.success && data.call_settings) {
      // Pre-llenar el formulario con la configuración anterior
      const settings = data.call_settings;
      
      setDuracionMaxima(settings.max_call_duration);      // 300
      setTiempoTimbrado(settings.ring_timeout);           // 30
      setIntentosMaximos(settings.max_attempts);          // 3
      setHorasEntreIntentos(settings.retry_delay_hours);  // 24
      setHoraInicio(settings.allowed_hours.start);        // "09:00"
      setHoraFin(settings.allowed_hours.end);             // "18:00"
      setDiasSeleccionados(settings.days_of_week);        // [1,2,3,4,5]
      setZonaHoraria(settings.timezone);                  // "America/Santiago"
      setPrioridad(settings.priority);                    // "low"
      
      console.log('✅ Configuración anterior cargada desde:', data.from_batch);
    } else {
      // Primera vez, usar valores por defecto
      console.log('ℹ️ Sin configuración anterior, usando defaults');
    }
  } catch (error) {
    console.error('Error cargando configuración:', error);
    // Usar valores por defecto
  }
}

// 2. Llamar esta función cuando el usuario llegue al paso 3
useEffect(() => {
  if (pasoActual === 3) {  // "Configuración de Llamadas"
    cargarConfiguracionAnterior();
  }
}, [pasoActual]);
```

---

## ✅ REQUERIMIENTO 4: Validaciones Frontend

### 🔍 **Validaciones Requeridas Antes de Enviar**

```javascript
function validarFormulario() {
  const errores = [];
  
  // 1. Validar archivo Excel
  if (!archivoExcel) {
    errores.push('❌ Debe seleccionar un archivo Excel');
  }
  
  // 2. Validar account_id
  if (!accountId || accountId === 'string' || accountId === 'undefined') {
    errores.push('❌ Debe seleccionar una cuenta válida');
  }
  
  // 3. Validar batch_name
  if (!batchName || batchName.trim() === '') {
    errores.push('❌ Debe ingresar un nombre para el batch');
  }
  
  // 4. Validar configuración de llamadas
  if (duracionMaxima < 60 || duracionMaxima > 600) {
    errores.push('❌ Duración máxima debe estar entre 60 y 600 segundos');
  }
  
  if (tiempoTimbrado < 10 || tiempoTimbrado > 60) {
    errores.push('❌ Tiempo de timbrado debe estar entre 10 y 60 segundos');
  }
  
  if (intentosMaximos < 1 || intentosMaximos > 5) {
    errores.push('❌ Intentos máximos debe estar entre 1 y 5');
  }
  
  if (horasEntreIntentos < 1 || horasEntreIntentos > 72) {
    errores.push('❌ Horas entre intentos debe estar entre 1 y 72');
  }
  
  if (diasSeleccionados.length === 0) {
    errores.push('❌ Debe seleccionar al menos un día de la semana');
  }
  
  // 5. Validar horarios
  const [horaInicioHH, horaInicioMM] = horaInicio.split(':').map(Number);
  const [horaFinHH, horaFinMM] = horaFin.split(':').map(Number);
  const inicioMinutos = horaInicioHH * 60 + horaInicioMM;
  const finMinutos = horaFinHH * 60 + horaFinMM;
  
  if (inicioMinutos >= finMinutos) {
    errores.push('❌ Hora de inicio debe ser menor que hora de fin');
  }
  
  // 6. Validar fechas dinámicas (opcional)
  if (diasFechaLimite && (diasFechaLimite < 1 || diasFechaLimite > 365)) {
    errores.push('❌ Días para fecha límite debe estar entre 1 y 365');
  }
  
  if (diasFechaMaxima && (diasFechaMaxima < 1 || diasFechaMaxima > 365)) {
    errores.push('❌ Días para fecha máxima debe estar entre 1 y 365');
  }
  
  if (diasFechaLimite && diasFechaMaxima && diasFechaLimite >= diasFechaMaxima) {
    errores.push('❌ Días de fecha límite debe ser menor que días de fecha máxima');
  }
  
  return errores;
}

// Validar antes de enviar
function handleCrearCampaña() {
  const errores = validarFormulario();
  
  if (errores.length > 0) {
    alert(errores.join('\n'));
    return;
  }
  
  // Proceder a crear batch
  crearBatch();
}
```

---

## 📋 **Resumen de Cambios Requeridos**

### ✅ **1. Agregar Campo en FormData: `call_settings_json`**

```javascript
const callSettings = { /* ... */ };
formData.append('call_settings_json', JSON.stringify(callSettings));
```

### ✅ **2. Agregar Campo en FormData: `processing_type`**

```javascript
formData.append('processing_type', 'basic');  // o 'acquisition'
```

### ✅ **3. Agregar Campos Opcionales: `dias_fecha_limite` y `dias_fecha_maxima`**

```javascript
formData.append('dias_fecha_limite', 30);
formData.append('dias_fecha_maxima', 45);
```

### ✅ **4. Cargar Configuración Anterior al Abrir Formulario**

```javascript
useEffect(() => {
  if (pasoActual === 3) {
    cargarConfiguracionAnterior();
  }
}, [pasoActual]);
```

### ✅ **5. Agregar UI para Días de Fechas Dinámicas**

```jsx
<div className="fecha-config">
  <label>Días para Fecha Límite:</label>
  <input 
    type="number" 
    value={diasFechaLimite} 
    onChange={(e) => setDiasFechaLimite(e.target.value)}
    min="1"
    max="365"
  />
  <span className="preview">
    Resultado: {calcularFechaLimite()}
  </span>
</div>

<div className="fecha-config">
  <label>Días para Fecha Máxima:</label>
  <input 
    type="number" 
    value={diasFechaMaxima} 
    onChange={(e) => setDiasFechaMaxima(e.target.value)}
    min="1"
    max="365"
  />
  <span className="preview">
    Resultado: {calcularFechaMaxima()}
  </span>
</div>
```

---

## 🔍 **Cómo Verificar que Funciona**

### **1. Crear un batch con configuración completa**

En los logs del backend debes ver:

```log
INFO | 📥 Recibiendo request para crear batch desde Excel
INFO |    - account_id: 'retail_express'
INFO |    - batch_name: 'Campaña Test'
INFO |    - processing_type: 'basic'
INFO |    - call_settings: {...}  ← ✅ DEBE APARECER
INFO |    - dias_fecha_limite: 30  ← ✅ DEBE APARECER
INFO |    - dias_fecha_maxima: 45  ← ✅ DEBE APARECER
INFO | Fecha límite calculada dinámicamente: HOY + 30 días = 2025-11-25
INFO | Fecha máxima calculada dinámicamente: HOY + 45 días = 2025-12-10
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

// Jobs deben tener fechas calculadas
db.jobs.findOne({batch_id: "batch-2025-10-26-..."})

// Resultado esperado:
{
  "payload": {
    "due_date": "2025-11-25",           // ← ✅ Calculada: HOY + 30
    "additional_info": {
      "fecha_maxima": "2025-12-10"      // ← ✅ Calculada: HOY + 45
    }
  }
}
```

### **3. Verificar que el worker respeta los horarios**

En los logs del worker debes ver:

```log
[DEBUG] [{job_id}] Obteniendo configuración del batch...
[DEBUG] [{job_id}] ✅ Call settings encontrados: {
  "timezone": "America/Santiago",
  "days_of_week": [1, 2, 3, 4, 5],
  "allowed_hours": {"start": "09:00", "end": "18:00"}
}
[DEBUG] [{job_id}] ✅ Dentro de horario permitido
```

**Si está fuera de horario:**
```log
[INFO] [{job_id}] 🚫 FUERA DE HORARIO PERMITIDO - Día 6 (Saturday) no está en días permitidos [1,2,3,4,5]
[DEBUG] [{job_id}] Job reprogramado para 2025-10-28T09:00:00Z
```

---

## 🎯 **Prioridad de Implementación**

### 🔴 **ALTA PRIORIDAD (Implementar YA)**

1. **`call_settings_json`** → Sin esto, las llamadas se ejecutan 24/7
2. **`processing_type`** → Necesario para distinguir tipo de campaña

### 🟡 **MEDIA PRIORIDAD (Implementar esta semana)**

3. **`dias_fecha_limite` y `dias_fecha_maxima`** → Mejora UX, permite cálculo automático
4. **Persistencia de configuración** → Reutiliza configuración anterior

### 🟢 **BAJA PRIORIDAD (Nice to have)**

5. **Preview de fechas calculadas** → Ayuda visual para el usuario
6. **Validaciones avanzadas** → Mejora robustez del sistema

---

## 📞 **Soporte y Documentación**

### **Documentos de Referencia:**
- `docs/API_FRONTEND_REFERENCE.md` - Todos los endpoints disponibles
- `docs/PIPELINE_VALIDATION_GUIDE.md` - Cómo validar el flujo completo
- `docs/RETELL_PROMPT_VARIABLES_MAPPING.md` - Mapeo de variables para Retell AI

### **Endpoint del Backend:**
```
POST /api/v1/batches/excel/create
```

**Parámetros completos:**
```javascript
FormData {
  file: File,                           // REQUERIDO
  account_id: string,                   // REQUERIDO
  batch_name: string,                   // REQUERIDO
  processing_type: 'basic' | 'acquisition',  // REQUERIDO
  allow_duplicates: boolean,            // OPCIONAL (default: false)
  call_settings_json: string,           // REQUERIDO (JSON stringified)
  dias_fecha_limite: number,            // OPCIONAL (ej: 30)
  dias_fecha_maxima: number             // OPCIONAL (ej: 45)
}
```

---

## ✅ **Checklist de Implementación**

### **Para el Desarrollador Frontend:**

- [ ] Capturar valores del formulario "Configuración de Llamadas"
- [ ] Construir objeto `callSettings` con todos los campos
- [ ] Agregar `call_settings_json` al FormData como JSON string
- [ ] Agregar campo `processing_type` al FormData
- [ ] Agregar campos opcionales `dias_fecha_limite` y `dias_fecha_maxima`
- [ ] Implementar función para cargar configuración anterior
- [ ] Agregar validaciones antes de enviar
- [ ] Agregar UI para días de fechas dinámicas (opcional)
- [ ] Probar creación de batch y verificar logs del backend
- [ ] Verificar en MongoDB que `call_settings` se guardaron
- [ ] Confirmar que el worker respeta los horarios configurados

---

**¿Preguntas o dudas sobre la implementación?**

Revisa los documentos de referencia o consulta los logs del backend para validar que todo funciona correctamente.

**Fecha de entrega sugerida:** 🗓️ 30 de Octubre, 2025
