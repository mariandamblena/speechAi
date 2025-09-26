# Servicios de Carga de Batches - Guía de Uso

## Tipos de Procesamiento Disponibles

El sistema ahora permite elegir entre **dos tipos de procesamiento** al cargar batches desde Excel:

### 1. Procesamiento Básico (`basic`) - **POR DEFECTO**
- Procesamiento simple y directo
- Mantiene los datos tal como vienen en el Excel
- Normalización básica de teléfonos y datos
- Un job por fila del Excel

### 2. Procesamiento de Adquisición (`acquisition`) - **NUEVO**
- Lógica avanzada basada en el workflow N8N de adquisición
- **Agrupación inteligente por RUT** (múltiples filas → 1 deudor)
- Normalización chilena especializada
- Cálculo automático de fechas límite según reglas de negocio
- Suma de montos y conteo de cupones por RUT

## Cómo Usar

### Endpoint Único con Selección de Tipo
```http
POST /api/v1/batches/excel/create
```

### Parámetros

| Parámetro | Tipo | Obligatorio | Descripción |
|-----------|------|-------------|-------------|
| `file` | File | ✅ | Archivo Excel (.xlsx, .xls) |
| `account_id` | String | ✅ | ID de la cuenta |
| `processing_type` | String | ❌ | `"basic"` (default) o `"acquisition"` |
| `batch_name` | String | ❌ | Nombre personalizado del batch |
| `batch_description` | String | ❌ | Descripción del batch |
| `allow_duplicates` | Boolean | ❌ | Permitir duplicados (default: false) |

## Ejemplos de Uso

### 1. Procesamiento Básico (Default)
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create?account_id=strasing&allow_duplicates=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@chile_usuarios.xlsx"
```

**Resultado**: 2015 jobs individuales (uno por fila)

### 2. Procesamiento de Adquisición
```bash
curl -X POST "http://localhost:8000/api/v1/batches/excel/create?account_id=strasing&processing_type=acquisition&allow_duplicates=true" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@chile_usuarios.xlsx"
```

**Resultado**: ~1924 jobs agrupados (uno por RUT único)

## Ventajas del Procesamiento de Adquisición

### 🎯 **Agrupación Inteligente por RUT**
- Múltiples filas del mismo RUT → 1 job consolidado
- Suma automática de montos de deuda
- Conteo de cupones/cuotas por deudor

### 📞 **Normalización Avanzada de Teléfonos Chilenos**
- Formato E.164 correcto (+56XXXXXXXXX)
- Manejo de códigos de área legados
- Detección inteligente móvil/fijo
- Ejemplos:
  - `"09-2125907"` → `"+56992125907"`
  - `"02-8151807"` → `"+56228151807"`
  - `"569978445371"` → `"+56978445371"`

### 🗓️ **Cálculo Automático de Fechas Límite**
- `fecha_limite` = (FechaVencimiento MÁS GRANDE del RUT) + diasRetraso + 3 días
- `fecha_maxima` = (FechaVencimiento MÁS CHICA del RUT) + diasRetraso + 7 días
- Manejo inteligente de fechas chilenas (DD/MM/YYYY)

### 💰 **Normalización Financiera**
- Montos en pesos (no centavos)
- Suma consolidada por RUT
- Manejo de formatos chilenos ($1.234.567,89)

## Respuesta del API

### Estructura de Respuesta
```json
{
  "success": true,
  "message": "Batch 'Acquisition Batch 2025-09-26 15:30' creado exitosamente con procesamiento acquisition",
  "batch_id": "672548a1b2c3d4e5f6789abc",
  "batch_name": "Acquisition Batch 2025-09-26 15:30",
  "processing_type": "acquisition",
  "stats": {
    "total_rows_processed": 2015,
    "unique_debtors_found": 1924,
    "valid_debtors": 1924,
    "duplicates_filtered": 0,
    "existing_duplicates": 91,
    "jobs_created": 1924,
    "debtors_created": 1924
  }
}
```

### Campos de Estadísticas (Acquisition)

| Campo | Descripción |
|-------|-------------|
| `total_rows_processed` | Filas totales del Excel |
| `unique_debtors_found` | RUTs únicos encontrados |
| `valid_debtors` | Deudores válidos procesados |
| `duplicates_filtered` | Duplicados filtrados por anti-duplicación |
| `existing_duplicates` | RUTs que ya existían en la DB |
| `jobs_created` | Jobs de llamada creados |
| `debtors_created` | Registros de deudores creados |

## Casos de Uso Recomendados

### Usar Procesamiento Básico cuando:
- ✅ Cada fila representa un job independiente
- ✅ No hay agrupación por RUT necesaria  
- ✅ Datos ya están normalizados
- ✅ Migración o importación directa

### Usar Procesamiento de Adquisición cuando:
- ✅ **Datos chilenos de cobranza/deuda** 
- ✅ Múltiples filas por RUT (cupones, cuotas)
- ✅ Necesitas agrupación y suma por deudor
- ✅ Fechas de vencimiento múltiples por RUT
- ✅ Teléfonos en formatos legados chilenos
- ✅ **Casos de uso de cobranza automatizada**

## Migración de Workflow N8N

Este procesamiento de adquisición **reproduce exactamente** la lógica del workflow `Adquisicion_v3.json`:

- ✅ Normalización de RUTs chilenos
- ✅ Normalización de teléfonos E.164
- ✅ Agrupación por RUT con acumulación
- ✅ Cálculo de fechas según reglas específicas
- ✅ Manejo de datos financieros chilenos
- ✅ Creación de jobs para cola de llamadas

**Resultado**: Puedes migrar completamente del workflow N8N → API REST manteniendo la misma lógica de negocio.