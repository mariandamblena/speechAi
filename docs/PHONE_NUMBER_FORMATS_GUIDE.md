# 📞 Guía de Formatos de Números Telefónicos

## Fecha de creación: 26 de Octubre, 2025

---

## 📋 Índice

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [País Soportado: Chile](#país-soportado-chile)
3. [Formato Final (Backend)](#formato-final-backend)
4. [Formatos de Entrada Aceptados](#formatos-de-entrada-aceptados)
5. [Validación del Frontend](#validación-del-frontend)
6. [Ejemplos de Normalización](#ejemplos-de-normalización)
7. [Recomendaciones UI/UX](#recomendaciones-uiux)
8. [Manejo de Errores](#manejo-de-errores)
9. [Testing](#testing)
10. [Casos Especiales](#casos-especiales)

---

## 🎯 Resumen Ejecutivo

### Estado Actual del Sistema

| Aspecto | Detalle |
|---------|---------|
| **País soportado** | 🇨🇱 **Chile únicamente** |
| **Formato final** | E.164: `+56XXXXXXXXX` (código país + 9 dígitos) |
| **Tipos válidos** | Móviles (inician con 9) y Fijos (inician con 2, 3, 4, etc.) |
| **Normalización** | ✅ Automática en backend |
| **Validación estricta** | ✅ 9 dígitos obligatorios después de normalizar |

### ⚠️ Importante

El backend **normaliza automáticamente** los números, por lo que el frontend puede ser **flexible** en lo que acepta. Sin embargo, es recomendable **validar y dar feedback visual** al usuario.

---

## 🇨🇱 País Soportado: Chile

### Formato E.164 (Estándar Internacional)

```
+56 9 XXXX XXXX    (Móvil - 9 dígitos comenzando con 9)
+56 2 XXXX XXXX    (Fijo Santiago - 9 dígitos comenzando con 2)
+56 XX XXX XXXX    (Fijo otras regiones - 9 dígitos)
```

### Características de Números Chilenos

#### 📱 Móviles
- **Longitud**: 9 dígitos
- **Primer dígito**: Siempre **9**
- **Ejemplo**: `938773910` → `+56938773910`
- **Formato común**: `9 XXXX XXXX`

#### 📞 Fijos
- **Longitud**: 9 dígitos (con código de área incluido)
- **Santiago**: Comienza con **2** (ej: `228151807`)
- **Otras ciudades**: Comienzan con otros dígitos (3, 4, 5, etc.)
- **Ejemplo**: `228151807` → `+56228151807`

---

## 🔄 Formato Final (Backend)

El backend **siempre convierte** los números al formato **E.164**:

```
+56XXXXXXXXX
│  │└─────────── 9 dígitos (móvil o fijo)
│  └───────────── Sin espacios ni caracteres especiales
└──────────────── Código de país Chile
```

### Proceso de Normalización Automática

```
Entrada (Excel/Frontend) → ChileBatchService._norm_cl_phone() → Formato E.164
```

---

## ✅ Formatos de Entrada Aceptados

El backend acepta **múltiples formatos** y los normaliza automáticamente:

### Tabla de Conversión

| Formato de Entrada | Tipo | Resultado Normalizado | ✅ Válido |
|-------------------|------|----------------------|-----------|
| `938773910` | Móvil | `+56938773910` | ✅ |
| `9 3877 3910` | Móvil | `+56938773910` | ✅ |
| `09-93877-3910` | Móvil | `+56938773910` | ✅ |
| `56938773910` | Móvil | `+56938773910` | ✅ |
| `+56938773910` | Móvil | `+56938773910` | ✅ |
| `+56 9 3877 3910` | Móvil | `+56938773910` | ✅ |
| `228151807` | Fijo | `+56228151807` | ✅ |
| `2 2815 1807` | Fijo | `+56228151807` | ✅ |
| `02-815-1807` | Fijo | `+56228151807` | ✅ |
| `28151807` | Fijo (legado) | `+56228151807` | ✅ |
| `92125907` | Móvil (legado 8 dígitos) | `+56992125907` | ✅ |
| `12345678` | Fijo sin código área | `+56212345678` | ✅ (asume Santiago) |
| `12345` | Incompleto | `null` | ❌ |
| `abc123` | Inválido | `null` | ❌ |
| `+54911234567` | Argentina | `null` | ❌ |

---

## 🎨 Validación del Frontend

### Nivel 1: Validación Básica (Recomendado Mínimo)

```javascript
// Validación básica para Chile
function validateChileanPhone(phone) {
  if (!phone || phone.trim() === '') {
    return { valid: false, error: 'Número requerido' };
  }
  
  // Extraer solo dígitos
  const digits = phone.replace(/\D/g, '');
  
  // Verificar longitud mínima (8-11 dígitos considerando variaciones)
  if (digits.length < 8 || digits.length > 11) {
    return { 
      valid: false, 
      error: 'Debe tener entre 8 y 11 dígitos' 
    };
  }
  
  return { valid: true, error: null };
}
```

### Nivel 2: Validación Intermedia (Recomendado)

```javascript
// Validación con normalización y preview
function validateAndPreviewChileanPhone(phone) {
  if (!phone || phone.trim() === '') {
    return { 
      valid: false, 
      error: 'Número requerido',
      preview: null 
    };
  }
  
  // Extraer solo dígitos
  let digits = phone.replace(/\D/g, '');
  
  // Remover 56 si está presente al inicio (código país)
  if (digits.startsWith('56')) {
    digits = digits.substring(2);
  }
  
  // Remover ceros iniciales (trunk)
  digits = digits.replace(/^0+/, '');
  
  // Validar longitud
  if (digits.length < 8 || digits.length > 9) {
    return { 
      valid: false, 
      error: 'Número inválido para Chile',
      preview: null 
    };
  }
  
  // Normalizar a 9 dígitos si tiene 8
  if (digits.length === 8) {
    // Si empieza con 9, es móvil legado → agregar 9
    if (digits.startsWith('9')) {
      digits = '9' + digits;
    }
    // Si empieza con 2, es fijo de Santiago → agregar 2
    else if (digits.startsWith('2')) {
      digits = '2' + digits;
    }
    // Otros casos, asumir fijo de Santiago
    else {
      digits = '2' + digits;
    }
  }
  
  // Validar que sea móvil o fijo válido
  const firstDigit = digits[0];
  const isMobile = firstDigit === '9';
  const isLandline = ['2', '3', '4', '5', '6', '7'].includes(firstDigit);
  
  if (!isMobile && !isLandline) {
    return { 
      valid: false, 
      error: 'Número no parece chileno',
      preview: null 
    };
  }
  
  const preview = `+56${digits}`;
  const type = isMobile ? 'Móvil' : 'Fijo';
  
  return { 
    valid: true, 
    error: null,
    preview: preview,
    type: type,
    formatted: formatChileanPhone(digits)
  };
}

// Formatear para mostrar al usuario
function formatChileanPhone(digits) {
  // Formato: +56 9 XXXX XXXX
  if (digits.length === 9) {
    return `+56 ${digits[0]} ${digits.substring(1, 5)} ${digits.substring(5)}`;
  }
  return `+56 ${digits}`;
}
```

### Nivel 3: Validación Avanzada (Opcional)

```javascript
// Validación completa con sugerencias
function advancedValidateChileanPhone(phone) {
  const result = validateAndPreviewChileanPhone(phone);
  
  if (!result.valid) {
    // Sugerir correcciones
    const digits = phone.replace(/\D/g, '');
    
    if (digits.length === 7) {
      return {
        ...result,
        suggestion: `¿Quisiste decir +56 2 ${digits}? (Fijo Santiago)`
      };
    }
    
    if (digits.length === 10 && digits.startsWith('56')) {
      return {
        ...result,
        suggestion: `Parece que incluiste el código de país. Intenta: ${digits.substring(2)}`
      };
    }
  }
  
  return result;
}
```

---

## 💡 Ejemplos de Normalización

### Caso 1: Móvil con guiones

```
Entrada:    "09-9387-7391"
↓
Dígitos:    "0993877391"
↓
Sin 0:      "993877391"
↓
Válido:     9 dígitos, comienza con 9 ✅
↓
Resultado:  "+56993877391"
```

### Caso 2: Fijo con código área

```
Entrada:    "02-815-1807"
↓
Dígitos:    "028151807"
↓
Sin 0:      "28151807" (8 dígitos)
↓
Agregar 2:  "228151807" (9 dígitos)
↓
Válido:     9 dígitos, comienza con 2 ✅
↓
Resultado:  "+56228151807"
```

### Caso 3: Ya normalizado

```
Entrada:    "+56 9 3877 3910"
↓
Dígitos:    "56938773910"
↓
Sin 56:     "938773910"
↓
Válido:     9 dígitos, comienza con 9 ✅
↓
Resultado:  "+56938773910"
```

### Caso 4: Número incompleto

```
Entrada:    "938773"
↓
Dígitos:    "938773" (6 dígitos)
↓
Error:      Menos de 8 dígitos ❌
↓
Resultado:  null
```

---

## 🎨 Recomendaciones UI/UX

### 1. Input Field

#### Opción A: Campo Libre con Preview

```jsx
<FormGroup>
  <Label>Número de Teléfono</Label>
  <Input
    type="text"
    placeholder="Ej: 9 3877 3910 o 02-815-1807"
    value={phone}
    onChange={handlePhoneChange}
    maxLength={20}
  />
  {preview && (
    <FormText color={isValid ? "success" : "muted"}>
      📞 Se enviará como: <strong>{preview}</strong> ({type})
    </FormText>
  )}
  {error && (
    <FormText color="danger">{error}</FormText>
  )}
</FormGroup>
```

#### Opción B: Campo con Prefijo Fijo

```jsx
<FormGroup>
  <Label>Número de Teléfono (Chile)</Label>
  <InputGroup>
    <InputGroupText>🇨🇱 +56</InputGroupText>
    <Input
      type="tel"
      placeholder="9 3877 3910"
      value={phone}
      onChange={handlePhoneChange}
      maxLength={12}
    />
  </InputGroup>
  <FormText>Ingresa solo los 9 dígitos (móvil o fijo)</FormText>
</FormGroup>
```

### 2. Validación en Tiempo Real

```javascript
const handlePhoneChange = (e) => {
  const value = e.target.value;
  setPhone(value);
  
  // Validar mientras escribe (debounce recomendado)
  const validation = validateAndPreviewChileanPhone(value);
  setIsValid(validation.valid);
  setPreview(validation.preview);
  setError(validation.error);
  setType(validation.type);
};
```

### 3. Indicadores Visuales

```jsx
// Icono según tipo de número
{type === 'Móvil' && <span>📱</span>}
{type === 'Fijo' && <span>📞</span>}

// Color según validez
<Input
  {...props}
  className={isValid ? 'is-valid' : (phone.length > 0 ? 'is-invalid' : '')}
/>
```

### 4. Tooltip con Ejemplos

```jsx
<Tooltip>
  <TooltipTrigger>
    <InfoIcon />
  </TooltipTrigger>
  <TooltipContent>
    <p><strong>Formatos aceptados:</strong></p>
    <ul>
      <li>Móvil: 9 3877 3910</li>
      <li>Móvil: 09-9387-7391</li>
      <li>Fijo: 2 2815 1807</li>
      <li>Fijo: 02-815-1807</li>
      <li>Con código: +56 9 3877 3910</li>
    </ul>
  </TooltipContent>
</Tooltip>
```

---

## 🚨 Manejo de Errores

### Errores del Backend

Si el backend no puede normalizar el número, **NO se creará el job**:

```
Log: "Deudor 12345678 sin teléfono válido, saltando job"
```

### Mensajes de Error Recomendados

| Situación | Mensaje para el Usuario |
|-----------|-------------------------|
| Campo vacío | "El número de teléfono es obligatorio" |
| Muy corto | "El número debe tener al menos 8 dígitos" |
| Muy largo | "El número es demasiado largo para Chile" |
| Caracteres inválidos | "Solo se permiten números y símbolos (+, -, espacios)" |
| No es chileno | "Este número no parece ser de Chile" |
| Formato desconocido | "No se pudo identificar el formato. Ejemplo válido: 9 3877 3910" |

### Ejemplo de Validación en Submit

```javascript
const validateBatchBeforeSubmit = (contacts) => {
  const errors = [];
  
  contacts.forEach((contact, index) => {
    const validation = validateChileanPhone(contact.phone);
    
    if (!validation.valid) {
      errors.push({
        row: index + 1,
        name: contact.name,
        phone: contact.phone,
        error: validation.error
      });
    }
  });
  
  if (errors.length > 0) {
    showErrorModal({
      title: 'Números de teléfono inválidos',
      message: `Se encontraron ${errors.length} números inválidos:`,
      errors: errors
    });
    return false;
  }
  
  return true;
};
```

---

## 🧪 Testing

### Casos de Prueba Recomendados

```javascript
// Test suite para validación de teléfonos chilenos
describe('Chilean Phone Validation', () => {
  test('acepta móvil de 9 dígitos', () => {
    expect(validateChileanPhone('938773910').valid).toBe(true);
  });
  
  test('acepta móvil con guiones', () => {
    expect(validateChileanPhone('09-9387-7391').valid).toBe(true);
  });
  
  test('acepta fijo de Santiago', () => {
    expect(validateChileanPhone('228151807').valid).toBe(true);
  });
  
  test('acepta fijo con 02', () => {
    expect(validateChileanPhone('02-815-1807').valid).toBe(true);
  });
  
  test('acepta número con +56', () => {
    expect(validateChileanPhone('+56938773910').valid).toBe(true);
  });
  
  test('normaliza móvil legado de 8 dígitos', () => {
    const result = validateAndPreviewChileanPhone('92125907');
    expect(result.preview).toBe('+56992125907');
  });
  
  test('rechaza número muy corto', () => {
    expect(validateChileanPhone('12345').valid).toBe(false);
  });
  
  test('rechaza número argentino', () => {
    expect(validateChileanPhone('+54911234567').valid).toBe(false);
  });
});
```

### Números de Prueba

```javascript
// Números válidos para testing (Chile)
const validTestNumbers = [
  '938773910',      // Móvil estándar
  '990464905',      // Móvil estándar
  '228151807',      // Fijo Santiago
  '02-815-1807',    // Fijo con 02
  '+56938773910',   // Con código país
  '09-9387-7391',   // Con cero inicial
];

// Números inválidos para testing
const invalidTestNumbers = [
  '12345',          // Muy corto
  'abc123',         // Caracteres inválidos
  '+54911234567',   // Argentina
  '1234567890123',  // Muy largo
  '',               // Vacío
];
```

---

## 🔍 Casos Especiales

### 1. Múltiples Números por Contacto

Si un contacto tiene **varios números**, el sistema actualmente toma **solo el primero**:

```javascript
// Backend: services/batch_creation_service.py
phones = [debtor['to_number']] if debtor['to_number'] else []
```

**Recomendación**: Si el frontend permite múltiples números:
- Solo incluir **un número por fila** en el Excel
- O crear **múltiples jobs** (uno por número)

### 2. Números Internacionales (Fuera de Chile)

⚠️ **Actualmente NO soportado**

Si necesitas llamar a otros países:
1. Backend debe agregar `ArgentinaBatchService` al endpoint
2. Frontend debe agregar selector de país
3. Normalización debe cambiar según país seleccionado

### 3. Números con Extensión

```
Ejemplo: 228151807 ext 123
```

⚠️ **No soportado** - El sistema solo guarda el número base

### 4. Números Bloqueados

El sistema **no valida** si un número está en lista negra. Esto debe manejarse:
- En el Excel (marcar números no llamar)
- O en una feature futura del backend

---

## 📊 Resumen de Responsabilidades

| Aspecto | Frontend | Backend |
|---------|----------|---------|
| **Validación básica** | ✅ Recomendado | ✅ Obligatorio |
| **Normalización** | ⚪ Opcional (preview) | ✅ Automático |
| **Formato E.164** | ⚪ Mostrar preview | ✅ Conversión final |
| **Feedback visual** | ✅ Obligatorio | ❌ N/A |
| **Manejo de errores** | ✅ UX friendly | ✅ Logs |
| **Testing** | ✅ Casos válidos/inválidos | ✅ Normalización |

---

## ✅ Checklist de Implementación Frontend

### Fase 1: Básico (Mínimo Viable)
- [ ] Campo input para número de teléfono
- [ ] Placeholder con ejemplo: "Ej: 9 3877 3910"
- [ ] Validación: mínimo 8 dígitos, máximo 11
- [ ] Mensaje de error si está vacío

### Fase 2: Intermedio (Recomendado)
- [ ] Validación en tiempo real (con debounce)
- [ ] Preview del número normalizado: `+56XXXXXXXXX`
- [ ] Indicador visual de móvil 📱 o fijo 📞
- [ ] Tooltip con ejemplos de formatos aceptados
- [ ] Validación antes de submit

### Fase 3: Avanzado (Opcional)
- [ ] Formateo automático mientras escribe
- [ ] Sugerencias de corrección
- [ ] Detección de país (si se expande a otros países)
- [ ] Validación en Excel antes de upload
- [ ] Resaltado de números inválidos en tabla

---

## 📞 Ejemplos de Código Completo

### React Component Ejemplo

```jsx
import React, { useState, useEffect } from 'react';
import { Input, FormGroup, Label, FormText } from 'reactstrap';

const ChileanPhoneInput = ({ value, onChange, required = true }) => {
  const [phone, setPhone] = useState(value || '');
  const [validation, setValidation] = useState({ valid: true, error: null, preview: null, type: null });

  useEffect(() => {
    if (phone.length > 0) {
      const result = validateAndPreviewChileanPhone(phone);
      setValidation(result);
      
      // Notificar al padre solo si es válido
      if (result.valid && onChange) {
        onChange(result.preview);
      }
    }
  }, [phone]);

  const handleChange = (e) => {
    setPhone(e.target.value);
  };

  return (
    <FormGroup>
      <Label>
        Número de Teléfono {required && <span className="text-danger">*</span>}
      </Label>
      <Input
        type="tel"
        value={phone}
        onChange={handleChange}
        placeholder="Ej: 9 3877 3910 o 02-815-1807"
        className={
          phone.length === 0 ? '' :
          validation.valid ? 'is-valid' : 'is-invalid'
        }
        maxLength={20}
      />
      
      {validation.valid && validation.preview && (
        <FormText color="success">
          {validation.type === 'Móvil' ? '📱' : '📞'} 
          Se enviará como: <strong>{validation.formatted}</strong>
        </FormText>
      )}
      
      {!validation.valid && validation.error && phone.length > 0 && (
        <FormText color="danger">
          ❌ {validation.error}
        </FormText>
      )}
      
      {phone.length === 0 && (
        <FormText color="muted">
          💡 Acepta formatos: 9XXXXXXXX, 02-XXX-XXXX, +56XXXXXXXXX
        </FormText>
      )}
    </FormGroup>
  );
};

export default ChileanPhoneInput;
```

---

## 📝 Notas Finales

### Importante Recordar

1. ✅ El backend **normaliza automáticamente** - el frontend puede ser flexible
2. ✅ La validación del frontend es para **mejorar UX**, no para bloquear
3. ✅ Si un número no se normaliza, **no se creará el job** (se salta en el backend)
4. ✅ Actualmente **solo Chile** está soportado
5. ✅ El formato final **siempre** es E.164: `+56XXXXXXXXX`

### Próximos Pasos

Si necesitas agregar soporte para otros países:
1. Backend debe activar `ArgentinaBatchService` o crear servicios para otros países
2. Frontend debe agregar selector de país (🇨🇱 Chile / 🇦🇷 Argentina / etc.)
3. Validación debe adaptarse según país seleccionado
4. Actualizar esta documentación con los nuevos formatos

---

## 📧 Contacto

Si tienes dudas sobre la implementación, consulta:
- **Documentación adicional**: `docs/`
- **Código backend**: `app/services/chile_batch_service.py`
- **Endpoint**: `POST /api/v1/batches/excel/create`

---

**Documento creado**: 26 de Octubre, 2025  
**Última actualización**: 26 de Octubre, 2025  
**Versión**: 1.0.0
