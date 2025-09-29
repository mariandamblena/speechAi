# 🔧 CÓMO AGREGAR NUEVOS PARÁMETROS AL PROMPT DE RETELL

## 📋 EJEMPLO: Agregar `{{telefono_alternativo}}`

Supongamos que quieres agregar una variable `{{telefono_alternativo}}` al prompt.

---

## 1️⃣ MODIFICAR EL PROMPT DE RETELL

### **Prompt original:**
```
Hi, is this {{nombre}}?
I am Sofía from Je Je Group, collections for {{empresa}} in Chile.
I am calling about your debt with {{empresa}}, with {{cuotas_adeudadas}} pending installments...
```

### **Prompt modificado:**
```
Hi, is this {{nombre}}?
I am Sofía from Je Je Group, collections for {{empresa}} in Chile.
I am calling about your debt with {{empresa}}, with {{cuotas_adeudadas}} pending installments...

If this number doesn't work, we can also try {{telefono_alternativo}}.
```

---

## 2️⃣ MODIFICAR `call_worker.py` - Método `_context_from_job()`

**Archivo:** `app/call_worker.py`

```python
def _context_from_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mapear datos del job a variables dinámicas que espera el agente Retell.
    """
    now_chile = datetime.datetime.now().strftime("%A, %B %d, %Y at %I:%M:%S %p CLT")
    
    ctx = {
        "nombre": str(job.get("nombre", "")),
        "empresa": str(job.get("origen_empresa", "")),
        "cuotas_adeudadas": str(job.get("cantidad_cupones", "")),
        "monto_total": str(job.get("monto_total", "")),
        "fecha_limite": str(job.get("fecha_limite", "")),
        "fecha_maxima": str(job.get("fecha_maxima", "")),
        "current_time_America/Santiago": now_chile,
        
        # ✅ AGREGAR NUEVO PARÁMETRO
        "telefono_alternativo": str(job.get("telefono_alternativo", "")),
    }
    return {k: v for k, v in ctx.items() if v and v != "None"}
```

---

## 3️⃣ MODIFICAR `DebtCollectionProcessor` - Incluir dato en job

**Archivo:** `app/domain/use_cases/debt_collection_processor.py`

### **Método `create_jobs_from_normalized_data()`:**
```python
async def create_jobs_from_normalized_data(
    self,
    normalized_debtors: List[Dict[str, Any]],
    account_id: str,
    batch_id: str,
    config: Dict[str, Any]
) -> List[JobModel]:
    jobs = []
    
    for debtor in normalized_debtors:
        # ... código existente ...
        
        # Extraer teléfono alternativo
        phones = self._extract_phones(debtor)
        telefono_alternativo = phones[1] if len(phones) > 1 else ""
        
        # Crear payload con info adicional
        payload = DebtCollectionPayload(
            # ... campos existentes ...
            additional_info={
                'cantidad_cupones': debtor.get('cantidad_cupones', 1),
                'fecha_maxima': debtor.get('fecha_maxima', ''),
                'rut': debtor.get('rut', ''),
                'batch_origen': batch_id,
                
                # ✅ AGREGAR NUEVO CAMPO
                'telefono_alternativo': telefono_alternativo
            }
        )
        
        # Crear JobModel
        job = JobModel(
            # ... campos existentes ...
            
            # ✅ AGREGAR CAMPO DIRECTO (para call_worker.py)
            telefono_alternativo=telefono_alternativo
        )
```

---

## 4️⃣ MODIFICAR `JobModel` - Agregar campo (si es necesario)

**Archivo:** `app/domain/models.py`

Si quieres que el campo esté disponible directamente en el JobModel:

```python
@dataclass
class JobModel:
    """Modelo principal de un job de llamada"""
    _id: Optional[ObjectId] = None
    job_id: Optional[str] = None
    account_id: str = ""
    batch_id: Optional[str] = None
    status: JobStatus = JobStatus.PENDING
    contact: Optional[ContactInfo] = None
    payload: Optional[CallPayload] = None
    
    # Campos existentes...
    # ...
    
    # ✅ AGREGAR NUEVO CAMPO
    telefono_alternativo: Optional[str] = None
    
    # ... resto de campos
```

---

## 5️⃣ MODIFICAR `ChileBatchService` - Extraer dato del Excel

**Archivo:** `app/services/chile_batch_service.py`

### **Método que procesa Excel:**
```python
def _process_simple_excel_data(self, df: pd.DataFrame, batch_id: str) -> Dict[str, Any]:
    # ... código existente ...
    
    for i, row in enumerate(df.to_dict('records'), 1):
        # ... campos existentes ...
        
        # ✅ EXTRAER NUEVO CAMPO DEL EXCEL
        telefono2_raw = self._get_field(row, key_index, [
            'Telefono2', 'Teléfono 2', 'Telefono alternativo', 
            'Telefono_alternativo', 'Phone2', 'Alternative phone'
        ])
        
        telefono2 = self._norm_cl_phone(telefono2_raw, 'any')
        
        # Agregar al debtor
        by_rut[rut]['telefono_alternativo'] = telefono2
```

---

## 🎯 PASOS RESUMIDOS

### **Para agregar CUALQUIER parámetro nuevo:**

1. **📝 Actualizar prompt** en Retell con `{{nuevo_parametro}}`

2. **🔧 Modificar `call_worker.py`:**
   ```python
   ctx["nuevo_parametro"] = str(job.get("nuevo_parametro", ""))
   ```

3. **⚙️ Modificar procesador** (`DebtCollectionProcessor`):
   ```python
   # Extraer dato y agregarlo al job
   job.nuevo_parametro = valor_extraido
   ```

4. **📊 Modificar extracción** (`ChileBatchService`):
   ```python
   # Extraer del Excel y agregarlo al normalized debtor
   debtor['nuevo_parametro'] = valor_del_excel
   ```

5. **🗃️ Opcional: Actualizar `JobModel`** si necesitas el campo persistente

---

## 📋 EJEMPLOS DE PARÁMETROS COMUNES

### **Parámetros simples (desde Excel):**
- `{{email}}` - Email del cliente
- `{{direccion}}` - Dirección física  
- `{{telefono_trabajo}}` - Teléfono laboral
- `{{referencia_externa}}` - ID externo
- `{{observaciones}}` - Notas especiales

### **Parámetros calculados:**
- `{{dias_desde_vencimiento}}` - Calculado automáticamente
- `{{monto_en_palabras}}` - "ciento cincuenta mil pesos"
- `{{proximo_vencimiento}}` - Próxima fecha importante
- `{{categoria_cliente}}` - "premium", "standard", "moroso"

### **Parámetros de configuración:**
- `{{sucursal}}` - Sucursal responsable
- `{{ejecutivo_asignado}}` - Nombre del ejecutivo
- `{{horario_contacto}}` - "9:00 AM - 6:00 PM"

---

## 🚀 FLUJO COMPLETO DE UN NUEVO PARÁMETRO

### **Ejemplo: `{{email}}`**

1. **Excel:** Columna "Email" con valor `juan@ejemplo.com`
2. **ChileBatchService:** Extrae email del Excel
3. **DebtCollectionProcessor:** Agrega email al job
4. **MongoDB:** Job almacenado con `{"email": "juan@ejemplo.com"}`
5. **call_worker.py:** Extrae email del job
6. **Retell AI:** Recibe `{"email": "juan@ejemplo.com"}`
7. **Prompt:** `{{email}}` se reemplaza por `juan@ejemplo.com`
8. **Llamada:** "Si necesita confirmación, puede escribirnos a juan@ejemplo.com"

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### **Tipos de datos:**
- ✅ **Strings:** Funcionan directamente
- ✅ **Números:** Convertir a string `str(valor)`
- ✅ **Fechas:** Formatear `fecha.strftime("%d/%m/%Y")`
- ✅ **Booleanos:** Convertir `"Sí" if valor else "No"`

### **Validaciones:**
- ✅ Manejar valores vacíos o `None`
- ✅ Validar formato de datos (teléfonos, emails, etc.)
- ✅ Limitar longitud de strings largos

### **Performance:**
- ✅ No agregar parámetros innecesarios
- ✅ Calcular valores complejos solo una vez
- ✅ Usar índices en MongoDB si filtras por el nuevo campo

**¡Con estos pasos puedes agregar cualquier parámetro que necesites!** 🎯✨