# 📅 CÁLCULO DINÁMICO DE FECHAS - ENDPOINT `/api/v1/batches/excel/create`

## 🎯 OBJETIVO

Permitir que las fechas `fecha_limite` y `fecha_maxima` se calculen **dinámicamente** desde la fecha actual (momento de carga) + N días, en lugar de depender únicamente de las fechas contenidas en el archivo Excel.

---

## 🔧 PARÁMETROS NUEVOS

Se agregaron dos parámetros opcionales al endpoint `POST /api/v1/batches/excel/create`:

| Parámetro | Tipo | Requerido | Descripción | Ejemplo |
|-----------|------|-----------|-------------|---------|
| `dias_fecha_limite` | `int` | Opcional | Días a sumar a la fecha actual para calcular `fecha_limite` | `30` |
| `dias_fecha_maxima` | `int` | Opcional | Días a sumar a la fecha actual para calcular `fecha_maxima` | `45` |

---

## 📊 LÓGICA DE CÁLCULO

### **PRIORIDAD DE FECHAS**

1. **Si se especifica `dias_fecha_limite`**: 
   - Se calcula `fecha_limite = HOY + dias_fecha_limite`
   - Se ignora la fecha del Excel

2. **Si NO se especifica `dias_fecha_limite`**:
   - Se usa la fecha del Excel (columna `fecha_limite` o calculada)

3. **Lo mismo aplica para `fecha_maxima`**

### **FÓRMULA**

```python
fecha_limite = fecha_actual + timedelta(days=dias_fecha_limite)
fecha_maxima = fecha_actual + timedelta(days=dias_fecha_maxima)
```

**Formato de salida**: `YYYY-MM-DD` (ISO 8601)

---

## 🚀 EJEMPLOS DE USO

### **EJEMPLO 1: Usar fechas del Excel (comportamiento por defecto)**

```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@deudores.xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Campaña Octubre" \
  -F "processing_type=basic"
```

**Resultado**: 
- `fecha_limite` = Fecha tomada del Excel (columna `fecha_limite` o `due_date`)
- `fecha_maxima` = Fecha tomada del Excel (columna `fecha_maxima` si existe)

---

### **EJEMPLO 2: Calcular fecha_limite dinámicamente (HOY + 30 días)**

```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@deudores.xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Campaña Octubre" \
  -F "processing_type=basic" \
  -F "dias_fecha_limite=30"
```

**Si hoy es 2025-10-15**:
- `fecha_limite` = `2025-11-14` (HOY + 30 días)
- `fecha_maxima` = Fecha del Excel (si existe)

---

### **EJEMPLO 3: Calcular ambas fechas dinámicamente**

```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@deudores.xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Campaña Octubre" \
  -F "processing_type=acquisition" \
  -F "dias_fecha_limite=30" \
  -F "dias_fecha_maxima=45"
```

**Si hoy es 2025-10-15**:
- `fecha_limite` = `2025-11-14` (HOY + 30 días)
- `fecha_maxima` = `2025-11-29` (HOY + 45 días)

---

### **EJEMPLO 4: Usar con procesamiento "acquisition" (Chile)**

```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@adquisicion_chile.xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Adquisición Noviembre" \
  -F "processing_type=acquisition" \
  -F "dias_fecha_limite=60" \
  -F "dias_fecha_maxima=75"
```

**Resultado**:
- Se aplica lógica de agrupación por RUT (acquisition)
- Se normaliza RUT, teléfonos +56, fechas DD/MM/YYYY
- `fecha_limite` = `2025-12-14` (HOY + 60 días) - **OVERRIDE** del cálculo del Excel
- `fecha_maxima` = `2025-12-29` (HOY + 75 días) - **OVERRIDE** del cálculo del Excel

---

## 🔍 CASOS DE USO

### **CASO 1: Campaña de cobranza con ventana de 30 días**

**Escenario**: Quieres dar 30 días de plazo desde HOY, sin importar las fechas de vencimiento originales en el Excel.

**Solución**:
```bash
-F "dias_fecha_limite=30"
```

**Resultado**:
- Todos los deudores tendrán `fecha_limite = HOY + 30 días`

---

### **CASO 2: Campaña con ventana extendida de 60 días**

**Escenario**: Campaña de recuperación con plazo largo.

**Solución**:
```bash
-F "dias_fecha_limite=60" \
-F "dias_fecha_maxima=75"
```

**Resultado**:
- `fecha_limite = HOY + 60 días`
- `fecha_maxima = HOY + 75 días`

---

### **CASO 3: Respetar fechas del Excel (sin override)**

**Escenario**: El Excel ya tiene fechas calculadas correctamente y quieres usarlas.

**Solución**:
```bash
# NO especificar dias_fecha_limite ni dias_fecha_maxima
```

**Resultado**:
- Se usan las fechas del Excel tal cual

---

## 📝 CAMPOS AFECTADOS EN LOS MODELOS

### **DebtorModel**
```python
debtor = DebtorModel(
    ...
    fecha_limite=fecha_limite_calculada,  # ← Fecha dinámica o del Excel
    fecha_maxima=fecha_maxima_calculada,  # ← Fecha dinámica o del Excel
    ...
)
```

### **CallPayload (JobModel)**
```python
call_payload = CallPayload(
    ...
    due_date=fecha_limite_final,  # ← Fecha dinámica o del Excel
    additional_info={
        ...
        "fecha_maxima": fecha_maxima_final,  # ← Fecha dinámica o del Excel
    }
)
```

---

## 🎯 VENTAJAS

1. ✅ **Flexibilidad**: Puedes calcular fechas dinámicamente o usar las del Excel
2. ✅ **Control total**: Defines el plazo en días desde HOY
3. ✅ **Sin dependencia del Excel**: No necesitas fechas en el Excel si usas cálculo dinámico
4. ✅ **Retrocompatibilidad**: Si no especificas los parámetros, todo funciona como antes
5. ✅ **Funciona con ambos tipos de procesamiento**: `basic` y `acquisition`

---

## ⚙️ IMPLEMENTACIÓN TÉCNICA

### **Archivos Modificados**

1. **`app/api.py`**:
   - Agregados parámetros `dias_fecha_limite` y `dias_fecha_maxima` al endpoint
   - Pasados a los servicios correspondientes

2. **`app/services/batch_creation_service.py`**:
   - Método `create_batch_from_excel()` acepta nuevos parámetros
   - Método `_create_jobs_from_debtors()` calcula fechas dinámicamente si se especifican

3. **`app/services/chile_batch_service.py`**:
   - Método `create_batch_from_excel_acquisition()` acepta nuevos parámetros
   - Lógica de creación de jobs usa fechas dinámicas cuando se especifican

---

## 🧪 TESTING

### **Test 1: Sin parámetros (comportamiento por defecto)**
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@test.xlsx" \
  -F "account_id=strasing" \
  -F "processing_type=basic"
```

**Verificar**: `fecha_limite` debe ser la del Excel

---

### **Test 2: Con dias_fecha_limite=30**
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@test.xlsx" \
  -F "account_id=strasing" \
  -F "processing_type=basic" \
  -F "dias_fecha_limite=30"
```

**Verificar**: `fecha_limite` debe ser HOY + 30 días en formato `YYYY-MM-DD`

---

### **Test 3: Con ambos parámetros**
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@test.xlsx" \
  -F "account_id=strasing" \
  -F "processing_type=acquisition" \
  -F "dias_fecha_limite=30" \
  -F "dias_fecha_maxima=45"
```

**Verificar**: 
- `fecha_limite` = HOY + 30 días
- `fecha_maxima` = HOY + 45 días

---

## 📊 RESPUESTA DEL ENDPOINT

```json
{
  "success": true,
  "message": "Batch 'Campaña Octubre' creado exitosamente con procesamiento basic",
  "batch_id": "batch-20251015-143022-123456",
  "batch_name": "Campaña Octubre",
  "processing_type": "basic",
  "stats": {
    "total_debtors": 150,
    "total_jobs": 150,
    "estimated_cost": 4500.0,
    "duplicates_found": 5
  }
}
```

---

## 🎉 RESUMEN

Con esta implementación, ahora tienes **3 formas de manejar fechas**:

1. **Usar fechas del Excel** (default): No especifiques parámetros
2. **Calcular solo fecha_limite**: Especifica `dias_fecha_limite`
3. **Calcular ambas fechas**: Especifica `dias_fecha_limite` y `dias_fecha_maxima`

**¡Totalmente flexible y retrocompatible!** 🚀
