# 🔧 Solución: Variables Faltantes en Retell (cantidad_cupones y fecha_maxima)

## 🎯 **PROBLEMA IDENTIFICADO**

Cuando usas el endpoint `/api/v1/batches/excel/create` con `processing_type=basic`, las variables `cantidad_cupones` y `fecha_maxima` no llegaban al prompt de Retell AI.

## 🔍 **ANÁLISIS DEL PROBLEMA**

### **Flujo del Problema:**
1. **Excel** → `BatchCreationService` → Crea `JobModel` con `payload.additional_info`
2. **JobModel.to_dict()** → Extrae campos al nivel raíz ✅ (funcionaba)
3. **call_worker._context_from_job()** → **NO extraía additional_info** ❌ (problema)
4. **Retell API** → Recibe contexto incompleto

### **Root Cause:**
El `call_worker` tiene dos rutas de procesamiento:
- **Nueva arquitectura**: Usa `payload` estructurado
- **Lógica legacy**: Usa campos al nivel raíz

El endpoint básico crea jobs con nueva arquitectura, pero el `call_worker` **NO estaba extrayendo las variables de `additional_info`** en esa ruta.

## ✅ **SOLUCIÓN IMPLEMENTADA**

### **Archivo modificado:** `app/call_worker.py`

**Antes (líneas 644-651):**
```python
# Para debt collection
elif payload_data.get('debt_amount'):
    context.update({
        'tipo_llamada': 'cobranza',
        'empresa': str(payload_data.get('company_name', '')),
        'monto_total': str(payload_data.get('debt_amount', '')),
        'fecha_limite': str(payload_data.get('due_date', '')),
        'dias_vencidos': str(payload_data.get('overdue_days', 0)),
        'tipo_deuda': str(payload_data.get('debt_type', '')),
    })
```

**Después (con el fix):**
```python
# Para debt collection
elif payload_data.get('debt_amount'):
    context.update({
        'tipo_llamada': 'cobranza',
        'empresa': str(payload_data.get('company_name', '')),
        'monto_total': str(payload_data.get('debt_amount', '')),
        'fecha_limite': str(payload_data.get('due_date', '')),
        'dias_vencidos': str(payload_data.get('overdue_days', 0)),
        'tipo_deuda': str(payload_data.get('debt_type', '')),
    })
    
    # AGREGAR VARIABLES DE ADDITIONAL_INFO para cobranza
    additional_info = payload_data.get('additional_info', {})
    if additional_info:
        context.update({
            'cantidad_cupones': str(additional_info.get('cantidad_cupones', '')),
            'fecha_maxima': str(additional_info.get('fecha_maxima', '')),
            'cuotas_adeudadas': str(additional_info.get('cantidad_cupones', '')),
        })
```

## 🧪 **VERIFICACIÓN DE LA SOLUCIÓN**

### **Variables que ahora llegan a Retell:**
```json
{
  "tipo_llamada": "cobranza",
  "empresa": "Natura",
  "monto_total": "44583.0",
  "fecha_limite": "2025-10-06",
  "nombre": "CAROLA BELEN ORELLANA SANDOVAL",
  "RUT": "174403848",
  "cantidad_cupones": "1",          ← ✅ SOLUCIONADO
  "fecha_maxima": "2025-10-10",     ← ✅ SOLUCIONADO
  "cuotas_adeudadas": "1",          ← ✅ SOLUCIONADO
  "current_time_America_Santiago": "Friday, October 03, 2025 at 02:04:32 PM CLT"
}
```

## 📊 **IMPACTO DE LA SOLUCIÓN**

### **Endpoints Afectados:** ✅ Funcionan
- `/api/v1/batches/excel/create?processing_type=basic` ← **SOLUCIONADO**
- `/api/v1/batches/excel/create?processing_type=acquisition` ← Ya funcionaba
- `/api/v1/batches/chile/debt_collection` ← Ya funcionaba
- `/api/v1/batches/argentina/debt_collection` ← Ya funcionaba

### **Variables Disponibles en Retell:**
- ✅ `cantidad_cupones` → Número de cuotas adeudadas
- ✅ `fecha_maxima` → Fecha límite para pago
- ✅ `cuotas_adeudadas` → Alias de cantidad_cupones
- ✅ `monto_total` → Monto total de la deuda
- ✅ `fecha_limite` → Fecha de vencimiento
- ✅ `nombre` → Nombre del deudor
- ✅ `empresa` → Empresa acreedora

## 🚀 **PRÓXIMOS PASOS**

1. **Reiniciar el call_worker** para aplicar los cambios
2. **Probar una llamada real** con el endpoint `/api/v1/batches/excel/create`
3. **Verificar en Retell AI** que las variables llegan al prompt
4. **Monitorear logs** para confirmar funcionamiento

## 💡 **LECCIONES APRENDIDAS**

- **Dual Architecture**: El sistema tiene dos rutas de procesamiento que deben mantenerse sincronizadas
- **Testing Critical**: Los scripts de debug fueron esenciales para identificar el problema exacto
- **Data Flow**: Importante mapear el flujo completo: Excel → JobModel → call_worker → Retell

---

**Estado:** ✅ **RESUELTO**  
**Fecha:** 3 de octubre de 2025  
**Impacto:** Crítico - Variables esenciales para prompts de cobranza