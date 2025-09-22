# 📞 Sistema de Seguimiento de Llamadas AI

## 🔄 Cambios Implementados

### ✅ **Lo que hace ahora el sistema:**

1. **No llama dos veces si ya hay resultado exitoso**
2. **Reintenta solo cuando no contesta, con delay por persona**
3. **Guarda TODOS los detalles en MongoDB**
4. **Hace pooling completo como tu workflow n8n**

---

## 📊 Nueva Estructura de Datos MongoDB

Cada job ahora tiene estos campos adicionales:

```javascript
{
  // Campos existentes...
  "_id": ObjectId,
  "rut": "12345678-9",
  "status": "pending|in_progress|done|failed",
  "attempts": 2,
  
  // NUEVOS campos de seguimiento:
  "call_id": "retell_call_abc123",
  "call_started_at": ISODate("2025-09-22T15:30:00Z"),
  "call_ended_at": ISODate("2025-09-22T15:33:45Z"),
  "call_duration_seconds": 225,
  
  "call_result": {
    "success": true,
    "status": "completed",
    "details": {
      // TODO el payload de Retell API
      "call_status": "completed",
      "call_transcript": "...",
      "recording_url": "...",
      "disconnect_reason": "hangup",
      // etc...
    },
    "timestamp": ISODate("2025-09-22T15:33:45Z")
  },
  
  // Control de reintentos POR PERSONA:
  "next_try_at": ISODate("2025-09-22T16:33:45Z"),
  "last_attempt_result": "no_answer"
}
```

---

## 🔍 Consultas Útiles MongoDB

### Ver todos los resultados de llamadas:
```javascript
db.call_jobs.find(
  {"call_result.success": true},
  {
    "rut": 1, 
    "nombre": 1,
    "call_duration_seconds": 1,
    "call_result.status": 1,
    "call_result.timestamp": 1
  }
).sort({"call_result.timestamp": -1})
```

### Ver llamadas fallidas que se reintentarán:
```javascript
db.call_jobs.find(
  {
    "status": "pending",
    "call_result.success": false,
    "next_try_at": {"$exists": true}
  },
  {
    "rut": 1,
    "nombre": 1, 
    "attempts": 1,
    "last_attempt_result": 1,
    "next_try_at": 1
  }
).sort({"next_try_at": 1})
```

### Estadísticas de éxito por día:
```javascript
db.call_jobs.aggregate([
  {
    $match: {
      "call_result": {"$exists": true}
    }
  },
  {
    $group: {
      _id: {
        $dateToString: {
          format: "%Y-%m-%d",
          date: "$call_result.timestamp"
        }
      },
      total_calls: {"$sum": 1},
      successful_calls: {
        "$sum": {
          "$cond": [{"$eq": ["$call_result.success", true]}, 1, 0]
        }
      },
      avg_duration: {
        "$avg": "$call_duration_seconds"
      }
    }
  },
  {
    $addFields: {
      success_rate: {
        "$multiply": [
          {"$divide": ["$successful_calls", "$total_calls"]},
          100
        ]
      }
    }
  },
  {$sort: {"_id": -1}}
])
```

### Ver personas que ya fueron contactadas exitosamente:
```javascript
db.call_jobs.find(
  {"call_result.success": true},
  {
    "rut": 1,
    "nombre": 1,
    "to_number": 1,
    "call_result.status": 1,
    "call_duration_seconds": 1
  }
).sort({"call_result.timestamp": -1})
```

---

## ⚙️ Configuración de Delays

En tu archivo `.env`:

```env
# Tiempo entre consultas de estado (como el Wait de n8n)
CALL_POLLING_INTERVAL=15

# Máximo tiempo esperando que termine una llamada  
CALL_MAX_DURATION_MINUTES=10

# Delay entre reintentos para la misma persona
RETRY_DELAY_MINUTES=30

# Delay específico cuando no contesta
NO_ANSWER_RETRY_MINUTES=60
```

---

## 🎯 Flujo Completo Implementado

1. **Bot toma job** → Verifica que no tenga resultado exitoso
2. **Crea llamada** → Guarda `call_id` inmediatamente
3. **Hace pooling** → Consulta estado cada 15 segundos (configurable)
4. **Detecta fin** → Cuando status = "ended"|"completed"|"error"|etc
5. **Guarda resultado** → TODO el payload de Retell
6. **Decide acción**:
   - ✅ **Si exitoso**: Marca como "done", no llama más
   - ❌ **Si falla**: Programa reintento con delay por persona

---

## 🚫 Lo que YA NO pasa:

- ❌ No llama dos veces a la misma persona si ya contestó
- ❌ No hace pooling infinito (timeout configurable)
- ❌ No pierde el `call_id` ni los detalles
- ❌ No aplica delay por bot (es por persona/RUT)

---

## 📈 Monitoreo desde MongoDB

Puedes crear tus propios dashboards consultando:

- **Jobs pendientes**: `status: "pending"`
- **Llamadas exitosas**: `call_result.success: true`
- **Próximos reintentos**: `next_try_at: {$gte: new Date()}`
- **Duración promedio**: Usar `call_duration_seconds`
- **Costos**: Multiplicar duración × tarifa por minuto

¡Listo! El sistema ahora funciona igual que tu workflow de n8n pero en Python.