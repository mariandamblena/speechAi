# 🌎 Soporte Multi-País - Guía para Frontend

## 📋 Resumen de Cambios

El backend ahora soporta **múltiples países** para normalización de teléfonos y datos. Cada cuenta tiene un campo `country` que determina cómo se procesan los números telefónicos en los batches.

### Países Soportados
- 🇨🇱 **Chile (CL)**: Teléfonos formato `+56XXXXXXXXX` (9 dígitos)
- 🇦🇷 **Argentina (AR)**: Teléfonos formato `+54XXXXXXXXXXX` (10-11 dígitos)

---

## 🔧 Cambios Requeridos en Frontend

### 1. **Formulario de Creación de Cuenta**

Agregar 2 campos nuevos al formulario:

```typescript
interface CreateAccountForm {
  account_name: string;
  contact_name: string;
  contact_email: string;
  contact_phone?: string;
  plan_type: "credit_based" | "minutes_based";
  initial_credits?: number;
  initial_minutes?: number;
  max_concurrent_calls?: number; // Nuevo campo
  
  // 🆕 CAMPOS NUEVOS
  country: "CL" | "AR";  // ⚠️ REQUERIDO
  timezone?: string;      // Opcional, se puede inferir del country
}
```

#### Ejemplo de UI:

```tsx
<FormField>
  <Label>País / Country</Label>
  <Select value={formData.country} onChange={handleCountryChange}>
    <option value="CL">🇨🇱 Chile</option>
    <option value="AR">🇦🇷 Argentina</option>
  </Select>
</FormField>

<FormField>
  <Label>Zona Horaria</Label>
  <Select value={formData.timezone} onChange={handleTimezoneChange}>
    {/* Auto-populate basado en country */}
    {formData.country === "CL" && (
      <option value="America/Santiago">Santiago (GMT-3)</option>
    )}
    {formData.country === "AR" && (
      <>
        <option value="America/Argentina/Buenos_Aires">Buenos Aires (GMT-3)</option>
        <option value="America/Argentina/Cordoba">Córdoba (GMT-3)</option>
        <option value="America/Argentina/Mendoza">Mendoza (GMT-3)</option>
      </>
    )}
  </Select>
</FormField>
```

---

### 2. **Request al Backend**

El endpoint **NO cambia**, solo agrega los campos nuevos:

```typescript
POST /api/v1/accounts

{
  "account_name": "Mi Empresa",
  "contact_name": "Juan Pérez",
  "contact_email": "juan@empresa.com",
  "contact_phone": "+56912345678",
  "plan_type": "credit_based",
  "initial_credits": 1000,
  "max_concurrent_calls": 5,
  
  // 🆕 Campos nuevos
  "country": "AR",  // "CL" o "AR"
  "timezone": "America/Argentina/Buenos_Aires"
}
```

---

### 3. **Upload de Excel (¡No Requiere Cambios!)**

El endpoint de upload **permanece igual**:

```typescript
POST /api/v1/batches/excel/create
Content-Type: multipart/form-data

{
  file: [Excel File],
  account_id: "acc-df40bf180310",
  batch_name: "Campaña Octubre",
  batch_description: "Cobranza mensual",
  allow_duplicates: false,
  call_settings_json: {...}  // Opcional
}
```

**El backend automáticamente:**
1. Lee el `country` de la cuenta
2. Usa el normalizador correcto (`normalize_phone_cl` o `normalize_phone_ar`)
3. Procesa los teléfonos en el formato correcto

---

## 🔍 Cómo Funciona Internamente

### Flujo Completo

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Frontend: Crear Cuenta                                  │
│    POST /api/v1/accounts                                    │
│    { country: "AR", timezone: "America/Argentina/..." }    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Backend: Guardar Cuenta en MongoDB                      │
│    accounts.insert_one({                                    │
│      account_id: "acc-xxx",                                 │
│      country: "AR",  ← Guardado                            │
│      timezone: "America/Argentina/Buenos_Aires"            │
│    })                                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Frontend: Subir Excel con Teléfonos Argentinos          │
│    POST /api/v1/batches/excel/create                        │
│    file: "clientes_argentina.xlsx"                          │
│    Teléfonos en Excel: 1123456789, 91123456789             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend: Detectar País de la Cuenta                     │
│    account = get_account("acc-xxx")                         │
│    country = account.country  # "AR"                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Backend: Crear Procesador con País                      │
│    processor = ExcelDebtorProcessor(country="AR")           │
│    processor.normalize_phone = normalize_phone_ar           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Backend: Normalizar Teléfonos                           │
│    Input:  1123456789                                       │
│    Output: +541123456789  ✅                                │
│                                                             │
│    Input:  91123456789                                      │
│    Output: +5491123456789  ✅                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Backend: Crear Jobs con Teléfonos E.164                 │
│    12 deudores → 12 jobs creados  ✅                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🐛 Problema Anterior vs Solución

### ❌ ANTES (Problema)

```
Usuario sube Excel con teléfonos argentinos (54113650246)
                    ↓
Backend usa SIEMPRE normalize_phone_cl()
                    ↓
Teléfono 54113650246 rechazado (no es válido para Chile)
                    ↓
❌ 0 jobs creados - ERROR
```

### ✅ AHORA (Solución)

```
Usuario sube Excel con teléfonos argentinos (54113650246)
                    ↓
Backend detecta country="AR" de la cuenta
                    ↓
Usa normalize_phone_ar() automáticamente
                    ↓
Teléfono 54113650246 → +5491123650246 ✅
                    ↓
✅ 12 jobs creados exitosamente
```

---

## 📊 Formatos de Teléfono por País

### Chile (CL)
| Input Excel | Output E.164 | Tipo |
|-------------|--------------|------|
| `938773910` | `+56938773910` | Móvil (9 dígitos) |
| `990464905` | `+56990464905` | Móvil |
| `222345678` | `+56222345678` | Fijo Santiago (2 + 8 dígitos) |
| `56938773910` | `+56938773910` | Ya con código país |

### Argentina (AR)
| Input Excel | Output E.164 | Tipo |
|-------------|--------------|------|
| `1123456789` | `+541123456789` | Fijo Buenos Aires (11 + 8 dígitos) |
| `91123456789` | `+5491123456789` | Móvil Buenos Aires (9 + 11 + 8) |
| `54113650246` | `+54113650246` | Ya con código país |

---

## 🧪 Testing Sugerido

### Test 1: Crear Cuenta Argentina

```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "Test Argentina",
    "contact_name": "Test User",
    "contact_email": "test@argentina.com",
    "plan_type": "credit_based",
    "initial_credits": 1000,
    "country": "AR",
    "timezone": "America/Argentina/Buenos_Aires"
  }'
```

### Test 2: Subir Excel con Teléfonos Argentinos

```bash
curl -X POST http://localhost:8000/api/v1/batches/excel/create \
  -F "file=@clientes_argentina.xlsx" \
  -F "account_id=acc-xxxxx" \
  -F "batch_name=Test Batch AR" \
  -F "allow_duplicates=true"
```

**Resultado esperado:**
- ✅ Todos los teléfonos normalizados a formato `+54XXXXXXXXXXX`
- ✅ Jobs creados exitosamente
- ✅ Logs muestran: `"Procesando archivo Excel para cuenta acc-xxx (País: AR)"`

---

## 🔧 Actualizar Cuentas Existentes

Las cuentas creadas antes de este cambio tienen `country=null` en la base de datos. Para actualizarlas:

### Opción A: Script de Migración (Backend)

El backend puede ejecutar:

```python
# Script para actualizar cuentas existentes
await db.accounts.update_many(
    {"country": {"$exists": False}},
    {"$set": {"country": "CL", "timezone": "America/Santiago"}}
)
```

### Opción B: Actualización Manual (Frontend)

Frontend puede agregar un modal para que el usuario actualice su cuenta:

```typescript
PATCH /api/v1/accounts/{account_id}

{
  "country": "AR",
  "timezone": "America/Argentina/Buenos_Aires"
}
```

---

## ⚠️ Notas Importantes

### 1. **Retrocompatibilidad**
- Cuentas sin `country` defaultean a `"CL"` (Chile)
- No rompe funcionalidad existente

### 2. **Validación de Teléfonos**
- Backend valida formato E.164 automáticamente
- Si un teléfono no es válido para el país, se muestra WARNING en logs y se salta el job

### 3. **Logs Mejorados**
```
INFO: Procesando archivo Excel para cuenta acc-xxx (País: AR)
WARNING: Deudor 12345678 sin teléfono válido, saltando job
```

### 4. **No Afecta Workers**
- `call_worker.py` sigue funcionando igual
- Solo recibe teléfonos ya normalizados en formato E.164

---

## 📚 Referencias

- **Normalizers Module**: `app/utils/normalizers/`
  - `phone_normalizer.py`: Funciones `normalize_phone_cl()` y `normalize_phone_ar()`
  - `date_normalizer.py`: `normalize_date()`, `add_days_iso()`
  - `text_normalizer.py`: `normalize_rut()`, `format_rut()`
  
- **Models**: `app/domain/models.py`
  - `AccountModel`: Incluye campos `country` y `timezone`

- **Services**: `app/services/batch_creation_service.py`
  - Auto-detección de país y creación dinámica de procesador

---

## 🚀 Checklist de Implementación

### Frontend
- [ ] Agregar campo `country` al formulario de crear cuenta
- [ ] Agregar campo `timezone` (opcional, puede inferirse)
- [ ] Agregar campo `max_concurrent_calls` al formulario
- [ ] Actualizar tipo TypeScript de `CreateAccountRequest`
- [ ] Testear creación de cuenta con `country="AR"`
- [ ] Testear upload de Excel con teléfonos argentinos

### Backend
- [x] Agregar campo `country` a `AccountModel`
- [x] Actualizar `ExcelDebtorProcessor` para multi-país
- [x] Modificar `BatchCreationService` para auto-detectar país
- [x] Crear funciones `format_rut()` y `add_days_iso()`
- [x] Actualizar endpoint `/api/v1/accounts`
- [x] Tests de normalización por país

---

## 💡 Próximas Mejoras

1. **Más países**: Agregar soporte para:
   - 🇵🇪 Perú (PE): `+51XXXXXXXXX`
   - 🇨🇴 Colombia (CO): `+57XXXXXXXXXX`
   - 🇲🇽 México (MX): `+52XXXXXXXXXX`

2. **Validación de RUT/DNI por país**:
   - Chile: RUT con dígito verificador
   - Argentina: DNI/CUIL sin dígito verificador

3. **UI de selección de país con flags**:
   ```tsx
   <CountrySelector countries={["CL", "AR", "PE", "CO"]} />
   ```

---

## 📞 Contacto

Si tienes dudas sobre la implementación, revisa:
- Logs del backend: Buscar `"Procesando archivo Excel para cuenta X (País: Y)"`
- Tests unitarios: `tests/test_normalizers.py`
- Documentación de normalizers: `app/utils/normalizers/`
