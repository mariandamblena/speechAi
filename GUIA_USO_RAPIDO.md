# 🚀 GUÍA RÁPIDA - USO PRÁCTICO CON TU ARCHIVO EXCEL

## 📋 INFORMACIÓN

**Archivo Excel**: `chile_10_usuarios (1).xlsx`  
**Fecha actual**: 2025-10-15  
**Account ID**: strasing

---

## 🎯 ESCENARIOS DE USO PRÁCTICOS

### **ESCENARIO 1: Campaña urgente (30 días de plazo)**

**Situación**: Necesitas iniciar una campaña de cobranza **HOY** y dar 30 días de plazo a todos los deudores.

**Comando**:
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@chile_10_usuarios (1).xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Campaña Urgente - Octubre 2025" \
  -F "processing_type=basic" \
  -F "dias_fecha_limite=30"
```

**Resultado esperado**:
- ✅ Todos los deudores tendrán `fecha_limite = 2025-11-14` (HOY + 30 días)
- ✅ Se ignoran las fechas del Excel
- ✅ Todos tienen el mismo plazo desde HOY

---

### **ESCENARIO 2: Campaña con ventana extendida (60 + 75 días)**

**Situación**: Campaña de recuperación con plazos más largos. Primera notificación a 60 días, límite máximo 75 días.

**Comando**:
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@chile_10_usuarios (1).xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Campaña Recuperación - Q4 2025" \
  -F "processing_type=basic" \
  -F "dias_fecha_limite=60" \
  -F "dias_fecha_maxima=75"
```

**Resultado esperado**:
- ✅ `fecha_limite = 2025-12-14` (HOY + 60 días)
- ✅ `fecha_maxima = 2025-12-29` (HOY + 75 días)
- ✅ Ventana de 15 días entre límite y máxima

---

### **ESCENARIO 3: Procesamiento Acquisition con fechas dinámicas**

**Situación**: Usar lógica avanzada de Chile (agrupación por RUT, normalización) + fechas dinámicas.

**Comando**:
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@chile_10_usuarios (1).xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Adquisición Chile - Octubre" \
  -F "processing_type=acquisition" \
  -F "dias_fecha_limite=45" \
  -F "dias_fecha_maxima=60"
```

**Resultado esperado**:
- ✅ Se agrupan registros por RUT (si hay duplicados)
- ✅ Se normaliza RUT (sin puntos), teléfonos (+56), fechas
- ✅ `fecha_limite = 2025-11-29` (HOY + 45 días)
- ✅ `fecha_maxima = 2025-12-14` (HOY + 60 días)

---

### **ESCENARIO 4: Usar fechas del Excel (sin override)**

**Situación**: El Excel ya tiene fechas correctas y quieres respetarlas.

**Comando**:
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@chile_10_usuarios (1).xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Batch con fechas originales" \
  -F "processing_type=basic"
```

**Resultado esperado**:
- ✅ Se usan las fechas tal cual están en el Excel
- ✅ Comportamiento por defecto (retrocompatible)

---

## 📊 TABLA DE FECHAS CALCULADAS

Si hoy es **2025-10-15**, estas son las fechas resultantes:

| Días | Fecha Límite | Uso Recomendado |
|------|--------------|-----------------|
| 7 | 2025-10-22 | Cobranza muy urgente |
| 15 | 2025-10-30 | Cobranza urgente |
| 30 | 2025-11-14 | Cobranza estándar |
| 45 | 2025-11-29 | Cobranza flexible |
| 60 | 2025-12-14 | Recuperación extendida |
| 90 | 2026-01-13 | Recuperación largo plazo |

---

## 🔍 VERIFICAR RESULTADOS

### **1. Crear el batch**
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" \
  -F "file=@chile_10_usuarios (1).xlsx" \
  -F "account_id=strasing" \
  -F "batch_name=Test Verificación" \
  -F "processing_type=basic" \
  -F "dias_fecha_limite=30" \
  -F "dias_fecha_maxima=45"
```

**Response esperado**:
```json
{
  "success": true,
  "batch_id": "batch-20251015-143022-123456",
  "batch_name": "Test Verificación",
  "processing_type": "basic",
  "stats": {
    "total_debtors": 10,
    "total_jobs": 10
  }
}
```

### **2. Obtener jobs del batch**
```bash
# Copiar el batch_id del paso anterior
curl "http://localhost:8000/api/v1/batches/batch-20251015-143022-123456/jobs"
```

### **3. Verificar las fechas**
En el response, busca:
```json
{
  "job_id": "...",
  "payload": {
    "due_date": "2025-11-14",  // ← debe ser HOY + 30 días
    "additional_info": {
      "fecha_maxima": "2025-11-29"  // ← debe ser HOY + 45 días
    }
  }
}
```

---

## 📱 DESDE PYTHON

```python
import requests
from datetime import datetime, timedelta

# Configuración
API_URL = "http://localhost:8000/api/v1/batches/excel/create"
EXCEL_FILE = "chile_10_usuarios (1).xlsx"

# Crear batch con fechas dinámicas
with open(EXCEL_FILE, 'rb') as f:
    response = requests.post(
        API_URL,
        files={'file': f},
        data={
            'account_id': 'strasing',
            'batch_name': 'Test desde Python',
            'processing_type': 'basic',
            'dias_fecha_limite': 30,
            'dias_fecha_maxima': 45
        }
    )

result = response.json()
print(f"Batch creado: {result['batch_id']}")
print(f"Jobs: {result['stats']['total_jobs']}")

# Calcular fechas esperadas
hoy = datetime.now()
fecha_limite_esperada = (hoy + timedelta(days=30)).strftime('%Y-%m-%d')
fecha_maxima_esperada = (hoy + timedelta(days=45)).strftime('%Y-%m-%d')

print(f"\nFechas esperadas:")
print(f"  fecha_limite: {fecha_limite_esperada}")
print(f"  fecha_maxima: {fecha_maxima_esperada}")
```

---

## 🎨 COMPARACIÓN VISUAL

### **SIN fechas dinámicas** (antes)
```
Excel:
  Deudor 1: fecha_limite = 2025-09-15
  Deudor 2: fecha_limite = 2025-10-01
  Deudor 3: fecha_limite = 2025-08-20

Jobs creados:
  Job 1: due_date = 2025-09-15
  Job 2: due_date = 2025-10-01
  Job 3: due_date = 2025-08-20
  
❌ Fechas inconsistentes
❌ Algunas ya vencidas
```

### **CON fechas dinámicas** (ahora)
```
Request:
  dias_fecha_limite = 30
  
Jobs creados (HOY = 2025-10-15):
  Job 1: due_date = 2025-11-14
  Job 2: due_date = 2025-11-14
  Job 3: due_date = 2025-11-14
  
✅ Todas las fechas iguales
✅ Todas calculadas desde HOY
✅ 30 días de plazo para todos
```

---

## ⚡ COMANDOS RÁPIDOS PARA COPIAR

### Campaña estándar (30 días)
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" -F "file=@chile_10_usuarios (1).xlsx" -F "account_id=strasing" -F "batch_name=Campaña 30 días" -F "processing_type=basic" -F "dias_fecha_limite=30"
```

### Campaña extendida (60 + 75 días)
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" -F "file=@chile_10_usuarios (1).xlsx" -F "account_id=strasing" -F "batch_name=Campaña Extendida" -F "processing_type=basic" -F "dias_fecha_limite=60" -F "dias_fecha_maxima=75"
```

### Acquisition con fechas dinámicas
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create" -F "file=@chile_10_usuarios (1).xlsx" -F "account_id=strasing" -F "batch_name=Acquisition" -F "processing_type=acquisition" -F "dias_fecha_limite=45" -F "dias_fecha_maxima=60"
```

---

## ✅ CHECKLIST PRE-CARGA

Antes de crear el batch, verifica:

- [ ] El servidor está corriendo (`http://localhost:8000`)
- [ ] La cuenta existe (`strasing`)
- [ ] El Excel está en la ruta correcta
- [ ] Has decidido los días de plazo
- [ ] Has elegido el tipo de procesamiento (`basic` o `acquisition`)

---

## 🎉 ¡LISTO PARA USAR!

Ahora puedes crear batches con fechas calculadas dinámicamente desde HOY + N días. 

**Ventajas**:
- ✅ Control total sobre plazos
- ✅ Sin depender de fechas del Excel
- ✅ Consistencia en toda la campaña
- ✅ Fácil de usar

**¿Preguntas?** Consulta la documentación completa en:
- `docs/CALCULO_FECHAS_DINAMICO.md`
- `CAMBIOS_FECHAS_DINAMICAS.md`
