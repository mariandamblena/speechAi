# 🔴 ERROR ACTUAL: account_id = "string"

## 📊 Logs del Backend

```
2025-10-24 01:12:43,362 | INFO | services.batch_creation_service | Procesando archivo Excel para cuenta string
2025-10-24 01:12:44,350 | WARNING | services.batch_creation_service | Se encontraron 10 duplicados, procesando 0 deudores únicos
INFO:     127.0.0.1:51160 - "POST /api/v1/batches/excel/create HTTP/1.1" 400 Bad Request
```

## 🔍 Problema Identificado

El frontend está enviando la palabra literal `"string"` en vez del ID real de la cuenta:

```typescript
// ❌ INCORRECTO - Enviando el tipo en vez del valor
formData.append('account_id', 'string');  // Literal "string"

// ✅ CORRECTO - Debe enviar el ID real
formData.append('account_id', 'acc-a1b2c3d4e5f6');  // ID real
```

---

## 🎯 Solución para el Frontend

### Paso 1: Verificar que tienes el account_id correcto

En el **Paso 1: Información Básica**, cuando el usuario selecciona una cuenta del dropdown, debes capturar el **ID real**:

```typescript
interface Account {
  account_id: string;      // ej: "acc-a1b2c3d4e5f6"
  account_name: string;    // ej: "Empresa XYZ"
  balance: {
    credits: number;
  };
}

// Estado del modal
const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);

// Dropdown de cuentas
<Select
  value={selectedAccount?.account_id}
  onChange={(accountId) => {
    const account = accounts.find(a => a.account_id === accountId);
    setSelectedAccount(account);
  }}
>
  {accounts.map(account => (
    <Option key={account.account_id} value={account.account_id}>
      {account.account_name} ({account.balance.credits} créditos)
    </Option>
  ))}
</Select>
```

### Paso 2: Al enviar el FormData, usar el ID real

```typescript
const handleSubmit = async () => {
  // 1. Validar que tenemos un account_id real
  if (!selectedAccount || !selectedAccount.account_id) {
    alert('❌ Debes seleccionar una cuenta primero');
    return;
  }

  // 2. Log para debugging
  console.log('📤 Enviando batch con account_id:', selectedAccount.account_id);
  
  // 3. Crear FormData
  const formData = new FormData();
  
  // 4. Agregar account_id REAL (no la palabra "string")
  formData.append('account_id', selectedAccount.account_id);  // ✅ ID real
  
  // 5. Resto de campos
  formData.append('file', excelFile);
  formData.append('batch_name', batchName);
  formData.append('batch_description', description);
  formData.append('allow_duplicates', String(allowDuplicates));
  
  // 6. call_settings como JSON string
  if (callSettings) {
    formData.append('call_settings_json', JSON.stringify(callSettings));
  }
  
  // 7. Log del FormData (para debugging)
  console.log('📤 FormData entries:');
  for (const [key, value] of formData.entries()) {
    console.log(`   ${key}:`, value);
  }
  
  // 8. Enviar
  try {
    const response = await api.post('/batches/excel/create', formData);
    console.log('✅ Batch creado:', response.data);
  } catch (error) {
    console.error('❌ Error:', error);
  }
};
```

---

## 🔧 Debugging: Verificar qué estás enviando

Agrega estos logs ANTES de enviar el request:

```typescript
console.log('🔍 DEBUG ANTES DE ENVIAR:');
console.log('   selectedAccount:', selectedAccount);
console.log('   account_id:', selectedAccount?.account_id);
console.log('   batch_name:', batchName);
console.log('   file:', excelFile?.name);

// Si ves "string" aquí, el problema está en cómo capturas el account_id
if (selectedAccount?.account_id === 'string') {
  console.error('❌ ERROR: account_id es la palabra "string", no un ID real!');
  alert('Error: account_id inválido');
  return;
}
```

---

## ⚠️ Errores Comunes del Frontend

### Error 1: Enviar el tipo en vez del valor
```typescript
// ❌ MAL
const accountId: string = 'string';  // Literal
formData.append('account_id', accountId);

// ✅ BIEN
const accountId = selectedAccount.account_id;  // Valor real
formData.append('account_id', accountId);
```

### Error 2: No seleccionar cuenta del dropdown
```typescript
// ❌ MAL - cuenta no seleccionada
const selectedAccount = null;
formData.append('account_id', selectedAccount?.account_id ?? 'string');

// ✅ BIEN - validar primero
if (!selectedAccount) {
  alert('Selecciona una cuenta');
  return;
}
formData.append('account_id', selectedAccount.account_id);
```

### Error 3: Capturar mal el evento del dropdown
```typescript
// ❌ MAL
<Select onChange={(e) => setAccountId(e.target.type)}>  // 'type' es "string"

// ✅ BIEN
<Select onChange={(value) => setAccountId(value)}>  // 'value' es el ID
```

---

## 🧪 Test Rápido en Consola del Frontend

Abre las DevTools del navegador y ejecuta:

```javascript
// 1. Verificar cuentas disponibles
console.log('Cuentas disponibles:', accounts);

// 2. Verificar cuenta seleccionada
console.log('Cuenta seleccionada:', selectedAccount);
console.log('ID de la cuenta:', selectedAccount?.account_id);

// 3. Verificar tipo
console.log('Tipo de account_id:', typeof selectedAccount?.account_id);

// Si el tipo es "string" pero el valor ES "string", hay problema:
if (selectedAccount?.account_id === 'string') {
  console.error('❌ PROBLEMA: account_id es literal "string"');
} else {
  console.log('✅ OK: account_id tiene valor real');
}
```

---

## 📋 Checklist para el Frontend

Antes de enviar el FormData, verifica:

- [ ] ✅ El usuario seleccionó una cuenta del dropdown
- [ ] ✅ `selectedAccount` no es `null` o `undefined`
- [ ] ✅ `selectedAccount.account_id` tiene formato `"acc-XXXXXXXXXXXX"` (no "string")
- [ ] ✅ `formData.get('account_id')` devuelve el ID real (no "string")
- [ ] ✅ El archivo Excel está seleccionado
- [ ] ✅ `batch_name` no está vacío

---

## 🚀 Próximos Pasos

1. **Reinicia el API** para aplicar las validaciones nuevas:
   ```bash
   python app/run_api.py
   ```

2. **En el frontend**, verifica que estás capturando el `account_id` correcto del dropdown

3. **Agrega logs** antes de enviar el FormData:
   ```typescript
   console.log('📤 account_id a enviar:', selectedAccount?.account_id);
   ```

4. **Intenta crear el batch de nuevo**

5. **Revisa los logs del backend** - ahora mostrará más detalles:
   ```
   📥 Recibiendo request para crear batch desde Excel
      - account_id: 'acc-a1b2c3d4e5f6'  ← Debe ser esto, NO "string"
      - batch_name: 'Campaña Octubre'
      - file: contactos.xlsx
   ```

---

## 🎯 Error Backend Esperado

Si sigues enviando "string", verás este error claro:

```
400 Bad Request
{
  "detail": "❌ account_id inválido: 'string'. Debe ser un ID válido como 'acc-a1b2c3d4e5f6'. El frontend debe enviar el ID real de la cuenta seleccionada."
}
```

---

## 🔍 Segundo Problema: Duplicados

El log también muestra:
```
Se encontraron 10 duplicados, procesando 0 deudores únicos
```

Esto significa que:
- Tienes 10 contactos en el Excel
- Todos tienen el mismo teléfono (duplicados)
- No se procesó ninguno porque `allow_duplicates=false`

**Solución:**

Opción 1: Permite duplicados
```typescript
formData.append('allow_duplicates', 'true');
```

Opción 2: Verifica que el Excel tenga teléfonos únicos

---

**Fin del documento** 📄
