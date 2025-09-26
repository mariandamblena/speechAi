# Sistema de Creación de Batches desde Excel

Esta implementación reemplaza el workflow n8n `Adquisicion_v3` con una solución nativa en Python que mantiene toda la lógica original de procesamiento de deudores chilenos.

## Características Implementadas

### 🔄 Lógica del Workflow Original (Adquisicion_v3)

- **Normalización de RUT**: Limpia formatos, quita puntos y guiones
- **Normalización de Teléfonos**: 
  - Convierte a formato E.164 (+56XXXXXXXXX)
  - Maneja casos específicos chilenos (móviles legados, fijos Santiago)
  - Detecta y corrige errores comunes
- **Procesamiento de Fechas**:
  - Prioriza formato chileno (DD/MM/YYYY)
  - Maneja fechas seriales de Excel
  - Cálculo automático de fechas límite según reglas específicas
- **Agrupación por RUT**:
  - Consolida múltiples deudas por persona
  - Acumula montos totales y cantidad de cuotas
  - Selecciona mejor teléfono disponible

### 🛡️ Sistema Anti-Duplicación

- **Clave de Deduplicación**: `account_id::rut::batch_id`
- **Detección Multi-Nivel**:
  - Duplicados dentro del mismo archivo Excel
  - Duplicados entre batches existentes
  - Duplicados en jobs ya creados
- **Índices Únicos** en MongoDB para garantizar integridad

### 📊 Gestión de Costos y Balance

- **Estimación Automática** de costos por batch
- **Verificación de Saldo** antes de crear jobs
- **Reserva de Fondos** para llamadas pendientes
- **Compatible** con todos los tipos de plan (minutos, créditos, ilimitado)

## API Endpoints

### Vista Previa de Excel
```http
POST /api/v1/batches/excel/preview
Content-Type: multipart/form-data

file: archivo.xlsx
account_id: string
```

**Respuesta**:
```json
{
    "success": true,
    "filename": "deudores.xlsx",
    "preview": {
        "total_rows": 150,
        "valid_debtors": 142,
        "with_valid_phone": 138,
        "without_phone": 4,
        "total_debt_amount": 45750000.0,
        "duplicates_found": 8,
        "duplicates_preview": [...],
        "sample_debtors": [...]
    }
}
```

### Crear Batch desde Excel
```http
POST /api/v1/batches/excel/create
Content-Type: multipart/form-data

file: archivo.xlsx
account_id: string
batch_name?: string
batch_description?: string
allow_duplicates?: boolean (default: false)
```

**Respuesta**:
```json
{
    "success": true,
    "message": "Batch 'Cobranza Marzo 2024' creado exitosamente",
    "batch_id": "batch-2024-03-15",
    "batch_name": "Cobranza Marzo 2024",
    "stats": {
        "total_debtors": 142,
        "total_jobs": 142,
        "estimated_cost": 426.0,
        "duplicates_found": 0
    },
    "created_at": "2024-03-15T10:30:00.000Z"
}
```

### Estado Detallado del Batch
```http
GET /api/v1/batches/{batch_id}/status?account_id=string
```

## Formato de Excel Esperado

El sistema es **flexible** con los nombres de columnas y busca automáticamente por variaciones comunes:

### Columnas Requeridas:
- **RUT**: `RUT`, `RUTS`, `Rut`
- **Nombre**: `Nombre`, `nombre`
- **Saldo**: `Saldo actualizado`, `Saldo Actualizado`, `saldo`
- **Fecha Vencimiento**: `FechaVencimiento`, `Fecha Vencimiento`, `Vencimiento`
- **Días Retraso**: `diasRetraso`, `Días de retraso`, `Dias retraso`

### Columnas Opcionales:
- **Empresa**: `Origen Empresa`, `OrigenEmpresa`, `Empresa`
- **Teléfono Móvil**: `Teléfono móvil`, `Telefono movil`, `Celular`
- **Teléfono Fijo**: `Teléfono Residencial`, `Telefono residencial`, `Teléfono fijo`

### Ejemplo de Datos:
```
RUT           | Nombre              | Saldo actualizado | FechaVencimiento | diasRetraso | Teléfono móvil
12.345.678-9  | Juan Pérez Silva    | 1.250.000        | 15/03/2024       | 45          | +56 9 8765 4321
98.765.432-1  | María González      | 750,500          | 20/02/2024       | 60          | 09-1234-5678
```

## Lógica de Fechas (Igual que Workflow Original)

### Fecha Límite:
```
fecha_limite = fecha_vencimiento_MÁS_GRANDE + dias_retraso_de_esa_fila + 3_días
```

### Fecha Máxima:
```
fecha_maxima = fecha_vencimiento_MÁS_CHICA + dias_retraso_de_esa_fila + 7_días
```

## Instalación y Configuración

### 1. Instalar Dependencias
```bash
pip install pandas openpyxl pytz
```

### 2. Crear Índices Únicos
```bash
python create_indexes.py
```

### 3. Probar Funcionalidad
```bash
python test_excel_batch.py
```

## Estructura de Datos Generada

### DebtorModel (Colección: `Debtors`)
```python
{
    "batch_id": "batch-2024-03-15",
    "rut": "123456789",
    "rut_fmt": "12.345.678-9",
    "nombre": "Juan Pérez Silva",
    "origen_empresa": "BANCO CHILE",
    "phones": {
        "raw_mobile": "+56 9 8765 4321",
        "raw_landline": "02-234-5678",
        "mobile_e164": "+56987654321",
        "landline_e164": "+56223456787",
        "best_e164": "+56987654321"
    },
    "cantidad_cupones": 2,
    "monto_total": 2000000.0,
    "fecha_limite": "2024-04-17",
    "fecha_maxima": "2024-04-25",
    "to_number": "+56987654321",
    "key": "batch-2024-03-15::123456789",
    "created_at": "2024-03-15T10:30:00.000Z"
}
```

### JobModel (Colección: `call_jobs`)
```python
{
    "account_id": "empresa_123",
    "batch_id": "batch-2024-03-15",
    "deduplication_key": "empresa_123::123456789::batch-2024-03-15",
    "status": "pending",
    "contact": {
        "name": "Juan Pérez Silva",
        "dni": "123456789",
        "phones": ["+56987654321"],
        "next_phone_index": 0
    },
    "payload": {
        "debt_amount": 2000000.0,
        "due_date": "2024-04-17",
        "company_name": "BANCO CHILE",
        "additional_info": {
            "cantidad_cupones": 2,
            "fecha_maxima": "2024-04-25",
            "current_time_America_Santiago": "Friday, March 15, 2024 at 10:30:00 AM CLT"
        }
    },
    "created_at": "2024-03-15T10:30:00.000Z"
}
```

## Compatibilidad con Workflow Original

✅ **Mantiene 100% compatibilidad** con el workflow n8n existente:
- Misma estructura de datos en MongoDB
- Mismas colecciones (`Debtors`, `call_jobs`)
- Misma lógica de normalización
- Mismas reglas de fechas y cálculos

✅ **Mejoras adicionales**:
- Sistema robusto de anti-duplicación
- Validación de balance antes de crear jobs
- API REST completa para integración
- Manejo de errores mejorado
- Logging detallado

## Monitoreo y Debugging

### Logs de Procesamiento
- Información detallada de cada paso
- Estadísticas de duplicados encontrados
- Errores de validación por fila
- Tiempos de procesamiento

### Vista Previa Obligatoria
- Siempre revisar preview antes de crear batch
- Identifica problemas antes de procesar
- Muestra estadísticas completas
- Lista duplicados encontrados

¡El sistema está listo para reemplazar completamente el workflow n8n manteniendo toda la funcionalidad original!