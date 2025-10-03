# 🔍 ANÁLISIS: ENDPOINT MARKETING vs PROMPT DE COBRANZA

## ⚠️ PROBLEMA: INCOMPATIBILIDAD FUNDAMENTAL

El endpoint `POST /api/v1/batches/chile/marketing` **NO ES COMPATIBLE** con el prompt de Retell que analizaste.

---

## 📋 VARIABLES REQUERIDAS POR EL PROMPT (COBRANZA)

```
{{nombre}} - Nombre del cliente
{{empresa}} - Empresa acreedora
{{cuotas_adeudadas}} - Número de cuotas pendientes
{{monto_total}} - Monto total de la deuda
{{fecha_limite}} - Fecha límite de pago sin recargo
{{fecha_maxima}} - Fecha máxima final (con recargo)
{{current_time_America/Santiago}} - Fecha/hora actual
```

---

## 🎯 CONTEXTO GENERADO POR MARKETING

### **Servicio:** MarketingProcessor + MarketingPayload
### **Contexto para Retell:**

```python
def to_retell_context(self) -> Dict[str, str]:
    return {
        'tipo_llamada': 'marketing',                    # ❌ No requerido
        'empresa': self.company_name,                   # ✅ {{empresa}}
        'oferta_descripcion': self.offer_description,   # ❌ Variable inexistente
        'descuento_porcentaje': str(self.discount_percentage), # ❌ Variable inexistente
        'categoria_producto': self.product_category,    # ❌ Variable inexistente
        'segmento_cliente': self.customer_segment,      # ❌ Variable inexistente
        'tipo_campana': self.campaign_type,             # ❌ Variable inexistente
        'llamada_accion': self.call_to_action,          # ❌ Variable inexistente
        'valor_oferta': str(self.debt_amount),          # ❌ No es {{monto_total}}
        'fecha_expiracion': self.due_date,              # ❌ No es {{fecha_limite}}
        'urgencia': 'alta' if self.discount_percentage > 50 else 'media' # ❌ Variable inexistente
    }
```

---

## ❌ VERIFICACIÓN DE COMPATIBILIDAD

| **Variable del Prompt** | **¿Disponible?** | **Campo en Marketing** | **Estado** |
|-------------------------|------------------|----------------------|-----------|
| `{{nombre}}` | ❌ **NO** | No generado | **FALTA** |
| `{{empresa}}` | ✅ **SÍ** | `empresa` | ✅ OK |
| `{{cuotas_adeudadas}}` | ❌ **NO** | No aplica | **FALTA** |
| `{{monto_total}}` | ❌ **NO** | `valor_oferta` (diferente) | **FALTA** |
| `{{fecha_limite}}` | ❌ **NO** | `fecha_expiracion` (diferente) | **FALTA** |
| `{{fecha_maxima}}` | ❌ **NO** | No generado | **FALTA** |
| `{{current_time_America/Santiago}}` | ❌ **NO** | No generado | **FALTA** |

---

## 🚨 RESULTADO DEL ANÁLISIS

### **❌ COMPATIBILIDAD: 14% (1/7 variables)**

El endpoint `POST /api/v1/batches/chile/marketing` **NO FUNCIONA** con el prompt de cobranza porque:

### **Variables faltantes críticas:**
- ❌ `{{nombre}}` - El nombre del cliente no se incluye en el contexto
- ❌ `{{cuotas_adeudadas}}` - Marketing no maneja cuotas de deuda
- ❌ `{{monto_total}}` - Marketing usa `valor_oferta`, no `monto_total`
- ❌ `{{fecha_limite}}` - Marketing usa `fecha_expiracion`, no `fecha_limite`
- ❌ `{{fecha_maxima}}` - No existe en marketing
- ❌ `{{current_time_America/Santiago}}` - No se genera

### **Variables extra no utilizadas:**
- `oferta_descripcion`, `descuento_porcentaje`, `categoria_producto`, etc.

---

## 📞 QUÉ PASARÍA SI USARAS MARKETING CON PROMPT DE COBRANZA

### **Llamada resultante (rota):**
> *"Hola, ¿habla con **{{nombre}}**? Soy Sofía de Je Je Group, cobranzas para **Empresa ABC** en Chile. Le llamo por su deuda con **Empresa ABC**, con **{{cuotas_adeudadas}} cuotas adeudadas**, total **{{monto_total}} pesos**..."*

**Las variables no se reemplazarían y aparecerían literalmente como `{{variable}}`** ❌

---

## 🎯 SOLUCIONES

### **1. Usar endpoint correcto para cobranza:**
```bash
POST /api/v1/batches/chile/debt_collection  # ✅ Compatible 100%
```

### **2. Crear prompt específico para marketing:**
```
Speak Chilean Spanish, clear, cordial, and formal. Always address the client as "usted".

Hi, is this {{nombre}}?
I am calling from {{empresa}} with an exclusive offer for you.

We have {{oferta_descripcion}} with {{descuento_porcentaje}}% discount in {{categoria_producto}}.

This offer is valid until {{fecha_expiracion}}.
Are you interested in learning more?

[... resto del prompt de marketing ...]
```

### **3. Modificar MarketingProcessor para incluir variables faltantes:**
```python
def to_retell_context(self) -> Dict[str, str]:
    return {
        # Variables requeridas para compatibilidad
        'nombre': self.contact_name,  # ← AGREGAR
        'empresa': self.company_name,
        'monto_total': '0',  # Marketing no maneja deuda
        'cuotas_adeudadas': '0',  # Marketing no maneja cuotas
        'fecha_limite': self.due_date,
        'fecha_maxima': self.due_date,
        'current_time_america_santiago': datetime.now().isoformat(),
        
        # Variables específicas de marketing
        'tipo_llamada': 'marketing',
        'oferta_descripcion': self.offer_description,
        # ... resto
    }
```

---

## 💡 RECOMENDACIÓN

### **Para COBRANZA:** 
✅ **Usar:** `POST /api/v1/batches/chile/debt_collection`
✅ **Prompt:** El actual (100% compatible)

### **Para MARKETING:**
❌ **NO usar:** `POST /api/v1/batches/chile/marketing` con prompt de cobranza
✅ **Crear:** Prompt específico para marketing
✅ **Modificar:** MarketingProcessor si necesitas usar el mismo prompt

**El endpoint de marketing necesita su propio prompt especializado** 🎯