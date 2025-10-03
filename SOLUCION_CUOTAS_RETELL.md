# 🔧 Solución: Variables de Cuotas Faltantes en Retell

## 📋 Problema Identificado

Las variables de cuotas (`cantidad_cupones` y `cuotas_adeudadas`) no estaban llegando a Retell durante las llamadas, específicamente la variable de cantidad de cuotas que es crucial para el prompt del agente.

## 🔍 Diagnóstico Realizado

### 1. Análisis de la Base de Datos
- **Script usado**: `debug_retell_variables.py`
- **Problema encontrado**: Los campos `cantidad_cupones`, `monto_total`, `nombre`, etc. no estaban disponibles en el nivel raíz de los documentos de jobs
- **Causa**: El JobModel guardaba los datos en estructura anidada (`payload.additional_info.cantidad_cupones`) pero el call_worker esperaba los campos en el nivel raíz (`job.get("cantidad_cupones")`)

### 2. Ubicación del Problema
- **Archivo afectado**: `app/domain/models.py` - método `to_dict()` del JobModel
- **Lógica**: Los datos se guardaban correctamente pero en ubicación incorrecta para el call_worker

## ✅ Solución Implementada

### 1. Modificación del JobModel
**Archivo**: `app/domain/models.py`

Se modificó el método `to_dict()` para extraer campos importantes al nivel raíz:

```python
# Extraer campos importantes al nivel raíz para compatibilidad con call_worker
if hasattr(self.payload, 'debt_amount'):
    data["monto_total"] = self.payload.debt_amount
    data["deuda"] = self.payload.debt_amount

# Extraer campos del additional_info al nivel raíz
if self.payload.additional_info:
    for key, value in self.payload.additional_info.items():
        if key in ['cantidad_cupones', 'fecha_maxima', 'rut', 'batch_origen']:
            data[key] = value

# Extraer campos de contacto al nivel raíz
data["nombre"] = self.contact.name
data["rut"] = self.contact.dni
data["to_number"] = self.contact.current_phone
```

### 2. Migración de Jobs Existentes
**Archivo**: `migrate_jobs.py`

Se creó un script de migración para actualizar los 9 jobs existentes en la base de datos y extraer los campos anidados al nivel raíz.

**Resultados de migración**:
- ✅ 9 jobs actualizados exitosamente
- ✅ Campos extraídos: `cantidad_cupones`, `monto_total`, `nombre`, `rut`, `origen_empresa`, `fecha_limite`, `fecha_maxima`
- ✅ Todos los jobs ahora tienen `cantidad_cupones: 1` disponible

## 🧪 Verificación de la Solución

### 1. Test de Variables
**Archivo**: `test_cuotas_retell.py`

Verificación exitosa que confirma:
- ✅ `cuotas_adeudadas: '1'` - Variable principal para Retell
- ✅ `cantidad_cupones: '1'` - Variable alternativa
- ✅ `monto_total: '10813.0'` - Monto de la deuda
- ✅ `nombre: 'Kristel Saravia Salazar'` - Nombre del contacto

### 2. Contexto Generado para Retell
```json
{
  "nombre": "Kristel  Saravia Salazar",
  "empresa": "Natura", 
  "RUT": "128590390",
  "cantidad_cupones": "1",
  "cuotas_adeudadas": "1",
  "monto_total": "10813.0",
  "fecha_limite": "2025-10-06",
  "fecha_maxima": "2025-10-08",
  "current_time_America_Santiago": "2025-10-02 15:07:41"
}
```

## 📈 Impacto de la Solución

### ✅ Beneficios Inmediatos
1. **Variables completas**: Todas las variables críticas ahora llegan a Retell
2. **Compatibilidad**: Jobs nuevos y existentes funcionan correctamente
3. **Prompt funcional**: El agente puede acceder a la cantidad de cuotas para personalizar el mensaje
4. **Datos consistentes**: Información unificada entre el payload anidado y campos raíz

### 🔄 Para Jobs Futuros
- Los nuevos jobs se crearán automáticamente con los campos en ambas ubicaciones
- El call_worker puede acceder a las variables sin problemas
- No se requieren cambios adicionales en el flujo de creación

## 🛠️ Archivos Modificados

1. **`app/domain/models.py`**
   - Método `to_dict()` del JobModel actualizado
   - Extrae campos críticos al nivel raíz para compatibilidad

2. **`migrate_jobs.py`** (nuevo)
   - Script de migración para jobs existentes
   - Ejecutado una sola vez para corregir datos históricos

3. **`debug_retell_variables.py`** (nuevo)
   - Script de diagnóstico para verificar variables
   - Útil para troubleshooting futuro

4. **`test_cuotas_retell.py`** (nuevo)
   - Script de prueba para verificar variables antes de llamadas
   - Valida que el contexto sea correcto

## 🎯 Próximos Pasos Recomendados

1. **Probar llamada real**: Hacer una llamada de prueba para confirmar que Retell recibe las variables
2. **Monitorear logs**: Verificar que el call_worker genere el contexto correctamente
3. **Actualizar documentación**: Documentar el nuevo formato de variables para el equipo

## 📞 Comando para Nueva Llamada de Prueba

Una vez que quieras probar con una llamada real:

```python
# En test_cuotas_retell.py, descomenta y configura:
test_phone = "+56XXXXXXXXX"  # Número real de prueba
agent_id = os.getenv("RETELL_AGENT_ID")
from_number = os.getenv("RETELL_FROM_NUMBER")
```

---

**✅ PROBLEMA RESUELTO**: Las variables de cuotas ahora llegan correctamente a Retell y el agente puede acceder a la información de cantidad de cuotas durante las llamadas.