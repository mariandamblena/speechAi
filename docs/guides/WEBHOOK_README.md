# Sistema de Webhooks para Retell AI

Este sistema captura los eventos de llamadas de Retell AI en tiempo real y los almacena en MongoDB para análisis posterior.

## 🏗️ Arquitectura

```
Retell AI → Webhook Server (FastAPI) → MongoDB
     ↓            ↓                      ↓
Call Events → Event Processing → call_results collection
                 ↓                      ↓
              Job Updates → call_jobs collection (updated)
```

## 📋 Características

- ✅ **Eventos soportados**: `call_started`, `call_ended`, `call_analyzed`
- ✅ **Verificación de firma**: Valida webhooks usando `X-Retell-Signature`
- ✅ **Base de datos**: Almacena transcripciones, análisis y metadatos
- ✅ **Integración**: Actualiza jobs existentes con resultados de llamadas
- ✅ **Logging**: Registro detallado de eventos y errores
- ✅ **Health check**: Endpoint para monitoreo de estado

## 🚀 Configuración Rápida

### 1. Instalar dependencias

```powershell
# Activar virtual environment
.venv\Scripts\activate

# Instalar con el script automático
.\setup_webhook.ps1

# O manualmente
pip install -r requirements.txt
python setup_webhook_db.py
```

### 2. Configurar variables de entorno

Copiar `.env.webhook.example` a `.env` y configurar:

```env
# Webhook Configuration
WEBHOOK_ENABLED=true
WEBHOOK_HOST=localhost
WEBHOOK_PORT=8000

# Retell AI
RETELL_API_KEY=tu_api_key_aqui
RETELL_AGENT_ID=tu_agent_id_aqui

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=Debtors
```

### 3. Ejecutar el sistema

```powershell
# Opción 1: Ejecutar todo integrado (recomendado)
python call_worker.py

# Opción 2: Solo el webhook server
python -m uvicorn webhook_server:app --reload

# Opción 3: Solo el webhook server independiente
python webhook_server.py
```

### 4. Configurar URL pública (para producción)

```bash
# Instalar ngrok
ngrok http 8000

# Copiar la URL HTTPS generada
# Ejemplo: https://abc123.ngrok.io

# Configurar en Retell Dashboard:
# Webhook URL: https://abc123.ngrok.io/webhook
```

## 🧪 Testing

```powershell
# Test completo del webhook
python test_webhook.py

# Health check manual
curl http://localhost:8000/health

# Test con Postman/curl
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Retell-Signature: test_signature" \
  -d '{"event":"call_started","call":{"call_id":"test123"}}'
```

## 📊 Estructura de Base de Datos

### Colección `call_results`

```javascript
{
  "_id": ObjectId("..."),
  "call_id": "Jabr9TXYYJHfvl6Syypi88rdAHYHmcq6",
  "agent_id": "oBeDLoLOeuAbiuaMFXRtDOLriTJ5tSxD",
  "from_number": "+12137771234",
  "to_number": "+12137771235",
  "direction": "outbound",
  "call_type": "phone_call",
  "status": "ended", // started, ended, analyzed
  "start_timestamp": 1714608475945,
  "end_timestamp": 1714608491736,
  "disconnection_reason": "user_hangup",
  "transcript": "Transcripción completa...",
  "transcript_object": [...],
  "call_analysis": {
    "call_summary": "Resumen del análisis",
    "sentiment": "positive",
    "call_successful": true
  },
  "retell_llm_dynamic_variables": {
    "nombre": "Juan Pérez",
    "empresa": "Ejemplo SA"
  },
  "created_at": ISODate("2024-12-21T10:00:00Z"),
  "updated_at": ISODate("2024-12-21T10:05:00Z")
}
```

### Actualización en `call_jobs`

Los jobs existentes se actualizan con:

```javascript
{
  // ... campos existentes del job
  "call_id": "Jabr9TXYYJHfvl6Syypi88rdAHYHmcq6",
  "status": "completed", // cuando call_ended
  "last_call_event": "call_ended",
  "last_call_timestamp": ISODate("2024-12-21T10:05:00Z"),
  "disconnection_reason": "user_hangup",
  "call_duration": 30 // segundos
}
```

## 🔍 Monitoreo y Logs

### Logs del sistema

```powershell
# Ver logs en tiempo real
python call_worker.py

# Buscar eventos específicos
# Los logs incluyen:
# - Webhooks recibidos
# - Verificación de firmas
# - Actualizaciones de base de datos
# - Errores de procesamiento
```

### Consultas MongoDB útiles

```javascript
// Llamadas completadas hoy
db.call_results.find({
  "status": "ended",
  "created_at": { $gte: new Date("2024-12-21T00:00:00Z") }
})

// Llamadas por razón de desconexión
db.call_results.aggregate([
  { $group: { _id: "$disconnection_reason", count: { $sum: 1 } } }
])

// Jobs actualizados con call_id
db.call_jobs.find({ "call_id": { $exists: true } })

// Transcripciones que contienen texto específico
db.call_results.find({ "transcript": /deuda/i })
```

## 🔧 Troubleshooting

### ❌ Error: "Import fastapi could not be resolved"

```powershell
pip install fastapi uvicorn retell-sdk
```

### ❌ Error: "Invalid signature"

- Verificar que `RETELL_API_KEY` esté correctamente configurado
- En desarrollo, puedes desactivar la verificación temporalmente
- Verificar que la IP de Retell esté en whitelist: `100.20.5.228`

### ❌ Webhook no recibe eventos

1. Verificar que el servidor esté ejecutándose:
   ```powershell
   curl http://localhost:8000/health
   ```

2. Verificar URL pública con ngrok:
   ```powershell
   curl https://tu-url.ngrok.io/health
   ```

3. Verificar configuración en Retell Dashboard:
   - URL correcta: `https://tu-url.ngrok.io/webhook`
   - Eventos habilitados: `call_started`, `call_ended`, `call_analyzed`

### ❌ Base de datos no se actualiza

1. Verificar conexión MongoDB:
   ```powershell
   python -c "from pymongo import MongoClient; print(MongoClient('mongodb://localhost:27017').admin.command('ping'))"
   ```

2. Verificar índices:
   ```powershell
   python setup_webhook_db.py
   ```

3. Revisar logs de errores en la consola

## 📈 Próximas mejoras

- [ ] Dashboard web para visualizar llamadas
- [ ] Alertas automáticas por email/Slack
- [ ] Métricas y KPIs en tiempo real
- [ ] Integración con sistemas CRM
- [ ] Análisis de sentimientos avanzado
- [ ] Reportes automatizados

## 🔒 Seguridad

- ✅ Verificación de firma webhook
- ✅ Validación de IP origen (Retell: `100.20.5.228`)
- ✅ Variables de entorno para credenciales
- ✅ Logs sin información sensible
- ⚠️ **Importante**: Usar HTTPS en producción

## 📞 Soporte

Para problemas o preguntas:

1. Revisar logs del sistema
2. Ejecutar `python test_webhook.py`
3. Verificar configuración en `.env`
4. Consultar documentación de Retell AI: https://docs.retellai.com/features/webhook