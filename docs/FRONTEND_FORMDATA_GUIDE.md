# 📋 Guía para Frontend: Crear Batch desde Excel

## 🎯 Endpoint
```
POST /api/v1/batches/excel/create
```

## 📝 Formato de Request

### Content-Type
```
multipart/form-data
```

### Campos del FormData

| Campo | Tipo | Requerido | Default | Descripción |
|-------|------|-----------|---------|-------------|
| `file` | File | ✅ SÍ | - | Archivo Excel (.xlsx, .xls) |
| `account_id` | string | ✅ SÍ | - | ID de la cuenta (ej: "acc-a1b2c3d4e5f6") |
| `batch_name` | string | ❌ NO | Auto-generado | Nombre de la campaña |
| `batch_description` | string | ❌ NO | "" | Descripción opcional |
| `allow_duplicates` | boolean | ❌ NO | false | Permitir contactos duplicados |
| `processing_type` | string | ❌ NO | "basic" | "basic" o "acquisition" |
| `dias_fecha_limite` | number | ❌ NO | null | Días para calcular fecha_limite |
| `dias_fecha_maxima` | number | ❌ NO | null | Días para calcular fecha_maxima |
| `call_settings_json` | string | ❌ NO | null | **JSON STRING** con configuración |

---

## 🔧 Ejemplo de Código TypeScript/JavaScript

### ✅ CORRECTO - Enviar call_settings como JSON STRING

```typescript
// 1. Crear el objeto call_settings
const callSettings = {
  max_call_duration: 300,           // Segundos
  ring_timeout: 30,                 // Segundos
  max_attempts: 3,                  // Reintentos
  retry_delay_hours: 24,            // Horas entre reintentos
  allowed_hours: {
    start: "09:00",
    end: "18:00"
  },
  days_of_week: [1, 2, 3, 4, 5],   // Lun-Vie
  timezone: "America/Santiago"
};

// 2. Crear FormData
const formData = new FormData();

// 3. Agregar archivo
formData.append('file', excelFile);

// 4. Agregar campos básicos
formData.append('account_id', selectedAccountId);
formData.append('batch_name', batchName);
formData.append('batch_description', description);

// 5. Agregar call_settings como JSON STRING ⚠️ IMPORTANTE
formData.append('call_settings_json', JSON.stringify(callSettings));

// 6. Agregar otros campos opcionales
formData.append('allow_duplicates', 'false');
formData.append('processing_type', 'basic');

// 7. Enviar request
const response = await axios.post('/api/v1/batches/excel/create', formData, {
  headers: {
    'Content-Type': 'multipart/form-data'
  }
});
```

### ❌ INCORRECTO - NO enviar call_settings como objeto

```typescript
// ❌ ESTO CAUSARÁ ERROR 422
formData.append('call_settings', callSettings);  // NO FUNCIONA
formData.append('call_settings', { ...callSettings });  // NO FUNCIONA
```

---

## 📊 Estructura del Excel

El Excel debe tener estas columnas (pueden variar según use case):

### Columnas Básicas (Requeridas)
- `nombre` - Nombre del contacto
- `telefono_1` - Teléfono principal
- `telefono_2` - Teléfono secundario (opcional)

### Columnas Variables (Opcionales)
Estas columnas se convierten en variables dinámicas para el script:
- `monto_deuda` - Monto adeudado
- `fecha_vencimiento` - Fecha de vencimiento
- `numero_factura` - Número de factura
- `empresa` - Nombre de la empresa
- `rut` - RUT del cliente
- etc.

### Ejemplo de Excel:

| nombre | telefono_1 | telefono_2 | monto_deuda | empresa |
|--------|------------|------------|-------------|---------|
| Juan Pérez | +56912345678 | +56987654321 | 50000 | Acme Corp |
| María González | +56911111111 | | 75000 | Tech SA |
| Carlos Rodríguez | +56955555555 | | 180000 | Global Ltd |

---

## 📤 Response Esperada

### Éxito (200 OK)
```json
{
  "success": true,
  "batch_id": "batch-20251024-a1b2c3d4",
  "batch_name": "Campaña Octubre",
  "jobs_created": 100,
  "contacts_processed": 100,
  "duplicates_skipped": 5,
  "errors": []
}
```

### Error (422 Unprocessable Entity)
```json
{
  "detail": "call_settings_json debe ser un JSON válido: Expecting property name enclosed in double quotes"
}
```

### Error (400 Bad Request)
```json
{
  "detail": "Solo se permiten archivos Excel (.xlsx, .xls)"
}
```

---

## 🔍 Debugging

### Error: "account_id inválido: 'string'"

**Causa:** Estás enviando la palabra literal `"string"` en vez del ID real de la cuenta.

**Solución:** Verifica que estás capturando el `account_id` correcto del dropdown:

```typescript
// ❌ MAL - Enviando el tipo literal
formData.append('account_id', 'string');

// ✅ BIEN - Enviando el ID real de la cuenta seleccionada
const selectedAccount = accounts.find(a => a.account_id === selectedValue);
formData.append('account_id', selectedAccount.account_id);  // "acc-a1b2c3d4e5f6"
```

**Debug:** Agrega logs antes de enviar:
```typescript
console.log('📤 account_id:', selectedAccount?.account_id);
// Debe mostrar: "acc-a1b2c3d4e5f6" (NO "string")
```

---

### Error: "Se encontraron X duplicados, procesando 0 deudores únicos"

**Causa:** Todos los contactos del Excel tienen el mismo teléfono y `allow_duplicates=false`.

**Solución:**
- Opción 1: Permite duplicados: `formData.append('allow_duplicates', 'true')`
- Opción 2: Verifica que el Excel tenga teléfonos únicos

---

### Error: "Unexpected token 'o', "[object FormData]" is not valid JSON"

**Causa:** Estás enviando el objeto call_settings directamente en vez de un JSON string.

**Solución:**
```typescript
// ❌ MAL
formData.append('call_settings_json', callSettings);

// ✅ BIEN
formData.append('call_settings_json', JSON.stringify(callSettings));
```

---

### Error: 422 - "call_settings_json debe ser un JSON válido"

**Causa:** El JSON string está malformado.

**Solución:** Verifica que estás usando `JSON.stringify()` correctamente:
```typescript
const callSettingsString = JSON.stringify(callSettings);
console.log('📤 Sending call_settings_json:', callSettingsString);
formData.append('call_settings_json', callSettingsString);
```

---

### Error: 400 - "Solo se permiten archivos Excel"

**Causa:** El archivo no tiene extensión .xlsx o .xls

**Solución:** Verifica que el archivo tenga la extensión correcta:
```typescript
const file = event.target.files[0];
console.log('📎 File name:', file.name);
console.log('📎 File type:', file.type);

if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
  alert('Solo se permiten archivos Excel');
  return;
}
```

---

## 📝 Ejemplo Completo con React

```typescript
import { useState } from 'react';
import axios from 'axios';

interface CallSettings {
  max_call_duration: number;
  ring_timeout: number;
  max_attempts: number;
  retry_delay_hours: number;
  allowed_hours: {
    start: string;
    end: string;
  };
  days_of_week: number[];
  timezone: string;
}

const CreateBatchModal = () => {
  const [file, setFile] = useState<File | null>(null);
  const [accountId, setAccountId] = useState('');
  const [batchName, setBatchName] = useState('');
  const [callSettings, setCallSettings] = useState<CallSettings>({
    max_call_duration: 300,
    ring_timeout: 30,
    max_attempts: 3,
    retry_delay_hours: 24,
    allowed_hours: {
      start: '09:00',
      end: '18:00'
    },
    days_of_week: [1, 2, 3, 4, 5],
    timezone: 'America/Santiago'
  });

  const handleSubmit = async () => {
    if (!file || !accountId) {
      alert('Archivo y cuenta son requeridos');
      return;
    }

    // Crear FormData
    const formData = new FormData();
    formData.append('file', file);
    formData.append('account_id', accountId);
    formData.append('batch_name', batchName);
    
    // ⚠️ IMPORTANTE: Convertir call_settings a JSON string
    formData.append('call_settings_json', JSON.stringify(callSettings));

    try {
      const response = await axios.post(
        'http://localhost:8000/api/v1/batches/excel/create',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      console.log('✅ Batch creado:', response.data);
      alert(`Batch creado exitosamente: ${response.data.batch_id}`);
    } catch (error) {
      console.error('❌ Error:', error);
      alert('Error al crear batch');
    }
  };

  return (
    <div>
      {/* Formulario aquí */}
      <input
        type="file"
        accept=".xlsx,.xls"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <button onClick={handleSubmit}>Crear Batch</button>
    </div>
  );
};
```

---

## 🎯 Checklist para el Frontend

Antes de enviar el request, verifica:

- [ ] ✅ El archivo tiene extensión `.xlsx` o `.xls`
- [ ] ✅ `account_id` es un string válido (ej: "acc-a1b2c3d4e5f6")
- [ ] ✅ `call_settings_json` se envía como **JSON STRING** usando `JSON.stringify()`
- [ ] ✅ Content-Type es `multipart/form-data`
- [ ] ✅ Todos los campos boolean se envían como string: "true" o "false"
- [ ] ✅ Números se envían como string si es necesario: "300", "30", etc.

---

## 🔄 Flujo Completo

```
1. Usuario selecciona cuenta → account_id
2. Usuario ingresa nombre → batch_name
3. Usuario sube Excel → file
4. Usuario configura horarios → call_settings
5. Frontend crea FormData:
   - file: File
   - account_id: string
   - batch_name: string
   - call_settings_json: JSON.stringify(call_settings) ⚠️
6. Frontend envía POST /api/v1/batches/excel/create
7. Backend valida parámetros
8. Backend parsea call_settings_json a objeto
9. Backend crea batch en MongoDB
10. Backend procesa Excel y crea jobs
11. Backend retorna batch_id y resumen
```

---

**Fin del documento** 📄
