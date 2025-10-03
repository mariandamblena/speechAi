# 🤖 SpeechAI Backend - Sistema de Llamadas### ✅ **Integraciones**
- 🤖 **Retell AI**: Cliente completo para llamadas automatizadas
- 🗄️ **MongoDB**: Base de datos principal con Motor (async)
- 📊 **Excel**: Carga masiva de contactos desde archivos Excel
- 🌐 **FastAPI**: API REST moderna y rápida
- 📈 **Google Sheets**: Integración para reportes (opcional)

---

## 🏗️ Arquitectura

### 🎯 **Clean Architecture + DDD**

```
📂 app/
├── 🏛️ domain/              # Entidades y reglas de negocio
│   ├── models.py           # JobModel, BatchModel, ContactInfo
│   ├── enums.py            # Estados y tipos del sistema
│   └── use_cases/          # Casos de uso específicos
├── 🚀 services/            # Lógica de aplicación
│   ├── batch_service.py    # Gestión de lotes
│   ├── job_service.py      # Gestión de trabajos
│   ├── call_service.py     # Orquestación de llamadas
│   └── worker_service.py   # Coordinación de workers
├── 🏗️ infrastructure/      # Capa de persistencia
│   ├── database_manager.py # MongoDB async
│   └── retell_client.py    # Cliente Retell AI
├── 🌐 api.py              # Controllers REST
└── ⚙️ config/              # Configuración centralizada
    └── settings.py         # Settings del sistema
```

### 🔄 **Flujo de Procesamiento**

```
Excel Upload → Batch Creation → Job Generation → Worker Pool → 
Retell AI Call → Status Polling → Result Storage → Retry Logic
```

### 🎛️ **Estados del Sistema**

| Estado | Descripción | Acción |
|--------|-------------|--------|
| `pending` | Listo para procesar | Worker disponible lo toma |
| `in_progress` | Worker procesando | Esperando resultado |
| `done` | Completado exitosamente | Fin del flujo |
| `failed` | Falló definitivamente | No más reintentos |
| `suspended` | Pausado (sin créditos) | Esperar reactivación |

## 📁 Estructura del Proyecto

```
speechAi_backend/
├── 📱 app/                          # Aplicación principal
│   ├── 🏛️ domain/                   # Capa de Dominio
│   │   ├── models.py                # Entidades de negocio
│   │   ├── enums.py                 # Estados y tipos
│   │   ├── use_case_registry.py     # Registro de casos de uso
│   │   └── use_cases/              # Procesadores específicos
│   │
│   ├── 🚀 services/                 # Lógica de Aplicación
│   │   ├── account_service.py       # Gestión de cuentas
│   │   ├── batch_service.py         # Gestión de lotes
│   │   ├── job_service.py          # Gestión de trabajos
│   │   ├── call_service.py         # Orquestación de llamadas
│   │   └── worker_service.py       # Coordinación de workers
│   │
│   ├── 🏗️ infrastructure/           # Capa de Infraestructura
│   │   ├── database_manager.py      # MongoDB async
│   │   └── retell_client.py        # Cliente Retell AI
│   │
│   ├── 🛠️ utils/                    # Utilidades
│   │   ├── excel_processor.py       # Procesamiento Excel
│   │   ├── jobs_report_generator.py # Generación de reportes
│   │   └── timezone_utils.py       # Manejo de zonas horarias
│   │
│   ├── 📜 scripts/                  # Scripts de desarrollo
│   │   ├── create_indexes.py        # Índices MongoDB
│   │   ├── reset_jobs.py           # Reinicio de trabajos
│   │   └── generate_reports.py     # Reportes rápidos
│   │
│   ├── ⚙️ config/                   # Configuración
│   │   └── settings.py             # Settings centralizados
│   │
│   ├── 🌐 api.py                   # Endpoints REST
│   ├── 🔧 call_worker.py           # Worker de procesamiento
│   ├── 🚀 run_api.py              # Servidor FastAPI
│   └── 📋 requirements.txt         # Dependencias
│
├── 📚 docs/                         # Documentación
│   ├── guides/                     # Guías específicas
│   ├── workflows/                  # Workflows n8n
│   ├── CONFIGURACIONES_Y_CONTROL_SISTEMA.md
│   ├── STRUCTURE.md               # Arquitectura detallada
│   └── PROJECT_ANALYSIS_2025.md   # Análisis del proyecto
│
├── 📊 reportes/                    # Reportes generados
├── 🔧 .env.example                # Variables de entorno
└── 📖 README.md                   # Este archivo
```

## ⚡ Instalación y Configuración

### 🔧 **Prerrequisitos**

- 🐍 **Python 3.11+**
- 🗄️ **MongoDB 6.0+**
- 🔑 **Cuenta Retell AI** con API key
- 📞 **Número de teléfono** configurado en Retell

### 📥 **Instalación**

```bash
# 1. Clonar repositorio
git clone https://github.com/mariandamblena/speechAi.git
cd speechAi_backend

# 2. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate     # Windows

# 3. Instalar dependencias
pip install -r app/requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales
```

### ⚙️ **Configuración Básica (.env)**

```bash
# 🗄️ MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=speechai_db

# 🤖 Retell AI
RETELL_API_KEY=your_retell_api_key_here
RETELL_AGENT_ID=your_agent_id_here
RETELL_FROM_NUMBER=+1234567890

# 👷 Workers
WORKER_COUNT=6
MAX_ATTEMPTS=3
RETRY_DELAY_MINUTES=30

# 📊 Logs
LOG_LEVEL=INFO
```

### 🚀 **Inicio Rápido**

```bash
# 1. Inicializar base de datos
python app/scripts/create_indexes.py

# 2. Iniciar API
python app/run_api.py

# 3. Iniciar workers (nueva terminal)
python app/call_worker.py

# 4. Verificar estado
curl http://localhost:8000/health
```

## 💻 Uso del Sistema

### 📊 **Endpoints API Principales**

```bash
# 🏥 Health check
GET /health

# 📊 Carga de Excel
POST /api/upload/excel
Content-Type: multipart/form-data
Body: file=archivo.xlsx

# 🎯 Gestión de Batches
GET    /api/batches              # Listar batches
POST   /api/batches              # Crear batch
GET    /api/batches/{id}         # Ver batch específico
POST   /api/batches/{id}/pause   # Pausar batch
POST   /api/batches/{id}/resume  # Reanudar batch

# 📋 Gestión de Jobs
GET    /api/jobs                 # Listar jobs
GET    /api/jobs/{id}            # Ver job específico
POST   /api/jobs/{id}/retry      # Reintentar job

# 📈 Reportes
GET    /api/reports/jobs         # Reporte general
GET    /api/reports/excel        # Exportar a Excel
```

### 📤 **Carga de Datos desde Excel**

El sistema soporta 3 formatos de Excel diferentes:

#### **1. Formato Debt Collection**
```excel
RUT       | NOMBRE    | TELEFONO    | MONTO  | FECHA_VENC
12345678  | Juan P.   | +56911111   | 50000  | 2025-12-31
```

#### **2. Formato Marketing**
```excel
nombre    | telefono   | email          | edad | ciudad
María G.  | +56922222  | maria@test.cl  | 35   | Santiago
```

#### **3. Formato Genérico**
```excel
name      | phone      | var1 | var2
Carlos R. | +56933333  | A    | B
```

### 🔧 **Comandos de Administración**

```bash
# 📊 Ver estado del sistema
python app/scripts/generate_reports.py --format terminal

# 🔄 Reiniciar jobs fallidos
python app/scripts/reset_jobs.py --status failed --max-age-hours 24

# 📈 Generar reporte Excel
python app/scripts/generate_reports.py --format excel

# 🧹 Limpiar jobs antiguos
python app/scripts/reset_jobs.py --cleanup --older-than-days 30
```

## 📊 Monitoreo y Reportes

### 📈 **Sistema de Reportes Integrado**

```bash
# Reporte en terminal (tiempo real)
python app/scripts/generate_reports.py --format terminal

# Reporte en Excel (análisis detallado)
python app/scripts/generate_reports.py --format excel

# Reporte en Markdown (documentación)
python app/scripts/generate_reports.py --format markdown
```

### 📋 **Métricas Disponibles**

- **Estados de Jobs**: pending, in_progress, completed, failed
- **Análisis Temporal**: Distribución por hora/día
- **Tasas de Éxito**: Por batch, por tipo de llamada
- **Costos**: Desglose detallado por llamada
- **Teléfonos**: Uso de números principales vs alternativos
- **Reintentos**: Distribución de intentos por job

## 🔍 Troubleshooting

### ❌ **Problemas Comunes**

| Problema | Síntoma | Solución |
|----------|---------|----------|
| Jobs no se procesan | `pending` jobs no avanzan | Verificar workers: `ps aux \| grep call_worker` |
| Llamadas fallan | Alta tasa de `failed` | Revisar configuración Retell AI |
| Variables no llegan | Prompts sin datos | Verificar `call_worker.py` líneas 644-658 |
| Alto costo | Facturas elevadas | Revisar `CALL_MAX_DURATION_MINUTES` |
| Jobs colgados | `in_progress` > 5 min | Liberar: `python app/scripts/reset_jobs.py` |

### 🔧 **Comandos de Diagnóstico**

```bash
# Verificar conexión MongoDB
python -c "from pymongo import MongoClient; print(MongoClient().admin.command('ping'))"

# Verificar API Retell
curl -H "Authorization: Bearer $RETELL_API_KEY" https://api.retellai.com/agent

# Ver logs en tiempo real
tail -f logs/speechai.log

# Estado de workers
ps aux | grep -E "(call_worker|run_api)"
```

## 📚 Documentación

### 📖 **Documentos Clave**

- 📋 **[CONFIGURACIONES_Y_CONTROL_SISTEMA.md](docs/CONFIGURACIONES_Y_CONTROL_SISTEMA.md)**: Configuración completa y control del sistema
- 🏗️ **[STRUCTURE.md](docs/STRUCTURE.md)**: Arquitectura detallada del proyecto
- 🔧 **[SOLUCION_VARIABLES_RETELL.md](SOLUCION_VARIABLES_RETELL.md)**: Fix del bug de variables
- 📊 **[PROJECT_ANALYSIS_2025.md](docs/PROJECT_ANALYSIS_2025.md)**: Análisis completo del proyecto

### 🎯 **Guías Específicas**

- 💰 **[COST_GUIDE.md](docs/guides/COST_GUIDE.md)**: Guía de control de costos
- 🧪 **[TESTING_GUIDE.md](docs/guides/TESTING_GUIDE.md)**: Guía completa de testing
- 🔗 **[WEBHOOK_README.md](docs/guides/WEBHOOK_README.md)**: Configuración de webhooks

### 🌐 **API Documentation**

Una vez iniciado el servidor, la documentación interactiva está disponible en:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contribución

### 📝 **Workflow de Desarrollo**

1. **Fork** del repositorio
2. **Crear branch**: `git checkout -b feature/nueva-funcionalidad`
3. **Commits** descriptivos: `git commit -m "feat: add new feature"`
4. **Push**: `git push origin feature/nueva-funcionalidad`
5. **Pull Request** con descripción detallada

### 📏 **Estándares de Código**

- **Arquitectura**: Clean Architecture + DDD
- **Formato**: Black + isort
- **Linting**: flake8 + mypy
- **Testing**: pytest + coverage >= 80%
- **Documentación**: Docstrings + type hints

## 👥 Equipo

- **Desarrollo**: [mariandamblena](https://github.com/mariandamblena)
- **Arquitectura**: Clean Architecture + Domain Driven Design
- **Stack**: Python + FastAPI + MongoDB + Retell AI

## 🆘 Soporte

¿Necesitas ayuda? 

1. 📖 Revisa la [documentación completa](docs/)
2. 🔍 Busca en [issues existentes](https://github.com/mariandamblena/speechAi/issues)
3. 🆕 Crea un [nuevo issue](https://github.com/mariandamblena/speechAi/issues/new)
4. 📧 Contacta al equipo de desarrollo

---

**⭐ Si este proyecto te resulta útil, ¡no olvides darle una estrella!**tizadas

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-darkgreen.svg)](https://mongodb.com)
[![Retell AI](https://img.shields.io/badge/Retell%20AI-Integration-purple.svg)](https://retellai.com)

Sistema distribuido de procesamiento de llamadas automatizadas que replica workflows de n8n en Python, utilizando **Retell AI** para gestión completa del ciclo de vida de llamadas de cobranza y marketing.

## � Tabla de Contenidos

- [🚀 Características Principales](#-características-principales)
- [🏗️ Arquitectura](#️-arquitectura)
- [📁 Estructura del Proyecto](#-estructura-del-proyecto)
- [⚡ Instalación y Configuración](#-instalación-y-configuración)
- [🔧 Configuración Avanzada](#-configuración-avanzada)
- [💻 Uso del Sistema](#-uso-del-sistema)
- [📊 Monitoreo y Reportes](#-monitoreo-y-reportes)
- [🛠️ Desarrollo](#️-desarrollo)
- [� Troubleshooting](#-troubleshooting)
- [📚 Documentación](#-documentación)

---

## 🚀 Características Principales

### ✅ **Core Features**
- 🎯 **Llamadas Automáticas**: Integración completa con Retell AI
- 📊 **Seguimiento en Tiempo Real**: Polling system para estado de llamadas
- 🔄 **Sistema de Reintentos**: Lógica inteligente con delays configurables
- 📞 **Gestión de Teléfonos**: Rotación automática entre números disponibles
- 💰 **Control de Costos**: Registro detallado de costos por llamada
- 📈 **Reportes Avanzados**: Análisis completo en Excel/markdown/terminal
- 🏭 **Procesamiento Masivo**: Workers distribuidos para alta concurrencia
- 🛡️ **Manejo de Errores**: Recuperación automática y logging detallado

### ✅ **Casos de Uso Soportados**
- 💳 **Cobranza de Deudas**: Recordatorios automáticos con variables dinámicas
- 📢 **Marketing**: Campañas promocionales personalizadas  
- 📋 **Encuestas**: Recolección automatizada de datos
- ⏰ **Recordatorios**: Notificaciones de citas y pagos
- 📧 **Notificaciones**: Alertas importantes automatizadas

### ✅ **Integraciones**
- **MongoDB** - Base de datos principal para jobs y resultados
- **Retell AI** - API para llamadas de voz automatizadas
- **Python 3.12+** - Runtime principal
- **Docker Ready** - Containerización lista para producción

## � Requisitos del Sistema

### Dependencias
```
Python 3.12+
MongoDB 4.4+
Retell AI API Key
```

### Paquetes Python
```
pymongo>=4.8
python-dotenv>=1.0
requests>=2.32
tenacity>=9.0
```

## 🛠️ Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/mariandamblena/speechAi.git
cd speechAi/app
```

### 2. Crear entorno virtual
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus valores
```

### Variables de Entorno Requeridas

```bash
# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017
MONGO_DB=Debtors
MONGO_COLL_JOBS=call_jobs
MONGO_COLL_LOGS=call_logs

# Retell AI Configuration
RETELL_API_KEY=key_your_api_key_here
RETELL_BASE_URL=https://api.retellai.com
RETELL_AGENT_ID=agent_your_agent_id_here
RETELL_FROM_NUMBER=+1234567890

# Worker Configuration
WORKER_COUNT=3
LEASE_SECONDS=120
MAX_TRIES=3

# Call Tracking Configuration
CALL_POLLING_INTERVAL=15
CALL_MAX_DURATION_MINUTES=10
RETRY_DELAY_MINUTES=30
NO_ANSWER_RETRY_MINUTES=60
```

## 🚀 Uso

### Ejecutar el worker
```bash
python call_worker.py
```

### Reiniciar un job específico (para testing)
```bash
python reset_job.py <job_id>
```

### Ejemplo de output
```
=== INICIANDO CALL WORKER ===
MONGO_URI: mongodb://localhost:27017
MONGO_DB: Debtors
RETELL_API_KEY: ***7f60
WORKER_COUNT: 3
==============================

2025-09-22 13:34:57,943 | INFO | MainThread | Inicializando índices…
[DEBUG] [bot-1] ✅ Job encontrado: 68d1713d30b0c91f2f9b5a38
[DEBUG] [68d1713d30b0c91f2f9b5a38] ✅ Llamada creada exitosamente
[DEBUG] [68d1713d30b0c91f2f9b5a38] ✅ Estado final detectado: ended
```

## 🧩 Componentes del Sistema

### 1. JobStore - Gestión de Jobs 📝

**Responsabilidades:**
- Reclamar jobs de la cola con sistema de reservas (locking)
- Guardar call_id inmediatamente tras crear la llamada
- Almacenar resultados completos con análisis y costos
- Programar reintentos con delays inteligentes por persona
- Manejar estados del lifecycle completo

**Algoritmo de Reserva:**
```python
# Usa findOneAndUpdate para evitar race conditions
doc = self.coll.find_one_and_update(
    filter={"status": "pending"},
    update={
        "$set": {
            "status": "in_progress",
            "reserved_until": now + timedelta(hours=2),
            "worker_id": "bot-1"
        }
    }
)
```

### 2. RetellClient - API Integration 📞

**Funcionalidades:**
- Crear llamadas usando `/v2/create-phone-call`
- Consultar estado usando `/v2/get-call/{call_id}`
- Manejo de errores con retry automático
- Parsing robusto de respuestas API

**Variables Dinámicas Enviadas:**
```python
{
    "nombre": "RICHARD RENE RAMOS PEREZ",
    "empresa": "Natura", 
    "cuotas_adeudadas": "1",
    "monto_total": "104050",
    "fecha_limite": "2025-09-01",
    "fecha_maxima": "2025-09-05",
    "RUT": "27327203-8"
}
```

### 3. CallOrchestrator - Lógica de Negocio 🎭

**Procesos:**
- Selección de teléfonos (to_number → try_phones array)
- Mapeo de contexto desde job a variables Retell
- Ejecución de llamadas con manejo de errores
- Polling continuo hasta completar la llamada
- Clasificación de resultados (éxito vs. reintento)

## 🔄 Flujo de Procesamiento

### Etapa 1: Adquisición de Job
```
1. Worker busca jobs "pending" sin lease activo
2. Reserva job con findOneAndUpdate atómico
3. Incrementa counter de "attempts"
4. Asigna worker_id y timestamps
```

### Etapa 2: Preparación de Llamada
```
1. Selecciona próximo teléfono disponible
2. Mapea datos del job a variables Retell
3. Genera timestamp Chile actual
4. Valida configuración (API key, agent_id)
```

### Etapa 3: Ejecución de Llamada
```
1. POST /v2/create-phone-call a Retell
2. Guarda call_id inmediatamente en MongoDB
3. Inicia polling cada 15 segundos
4. Extiende lease periódicamente
```

### Etapa 4: Seguimiento (Polling)
```
1. GET /v2/get-call/{call_id} cada 15s
2. Evalúa status: ongoing → ended/error
3. Timeout máximo: 10 minutos
4. Logs detallados de cada consulta
```

### Etapa 5: Finalización
```
1. Extrae datos completos del resultado
2. Actualiza variables dinámicas capturadas
3. Calcula duración y costos
4. Programa reintento o marca como done
```

## 💾 Estructura de Datos MongoDB

### Estado Inicial del Job:
```json
{
  "_id": ObjectId("..."),
  "status": "pending",
  "rut": "273272038",
  "nombre": "RICHARD RENE RAMOS PEREZ",
  "to_number": "+5491136530246",
  "try_phones": ["+5491136530246"],
  "attempts": 0,
  "max_attempts": 3
}
```

### Durante Procesamiento:
```json
{
  "status": "in_progress",
  "worker_id": "bot-1",
  "call_id": "call_28ce0b42c2f20878076b6bc9cb0",
  "call_started_at": "2025-09-22T16:34:59.072Z",
  "reserved_until": "2025-09-22T18:34:58.080Z",
  "is_calling": true
}
```

### Resultado Final:
```json
{
  "status": "done",
  "call_duration_seconds": 97,
  "fecha_pago_cliente": "2025-09-01",
  "monto_pago_cliente": 104050,
  "call_result": {
    "success": true,
    "summary": {
      "call_cost": {"combined_cost": 1797},
      "call_analysis": {"call_successful": true, "user_sentiment": "Positive"},
      "recording_url": "https://...",
      "transcript": "Agent: Hola...",
      "disconnection_reason": "agent_hangup"
    }
  }
}
```

## 🔄 Sistema de Reintentos

### Lógica de Delays:
- **Llamadas exitosas:** `status = "done"`
- **No answer/busy:** 60 minutos de delay
- **Otros fallos:** 30 minutos de delay  
- **Sin teléfonos:** `status = "failed"` (terminal)

### Control de Teléfonos:
```python
1. Intenta to_number principal
2. Si falla, usa try_phones[0], try_phones[1], etc.
3. Marca last_phone_tried para seguimiento
4. Cuando se agotan, marca como failed
```

## 📊 Datos Capturados

El sistema captura y almacena los siguientes datos de cada llamada:

### Información Básica
- **Call ID** y timestamps de inicio/fin
- **Duración** en segundos y milisegundos
- **Status final** (ended, error, not_connected, etc.)
- **Razón de desconexión** (agent_hangup, user_hangup, etc.)

### Análisis de Llamada
- **Resumen de la conversación**
- **Sentiment del usuario** (Positive, Negative, Neutral)
- **Éxito de la llamada** (booleano)
- **Detección de buzón de voz**

### Costos
- **Costo total** en centavos USD
- **Duración facturable** en segundos
- **Desglose por producto** (TTS, LLM, etc.)

### Grabaciones y Transcripciones
- **URL de grabación** mono y multicanal
- **Transcripción completa** con timestamps
- **URLs de logs públicos** para debugging

### Variables Dinámicas Capturadas
- **Fecha de pago comprometida** (formato YYYY-MM-DD)
- **Monto de pago** comprometido (solo números)

## 🔧 Utilidades Incluidas

### reset_job.py
Permite reiniciar un job específico para testing:
```bash
python reset_job.py 68d1713d30b0c91f2f9b5a38
```

## 🎯 Próximos Pasos Recomendados

### 1. Monitoreo y Observabilidad 📈
- Dashboard de métricas (llamadas/hora, tasa de éxito, costos)
- Alertas para fallos críticos o costos excesivos
- Logs estructurados con timestamps y correlación IDs

### 2. Optimizaciones ⚡
- Connection pooling para MongoDB
- Rate limiting inteligente para Retell API
- Batch processing para jobs múltiples
- Caching de configuraciones del agente

### 3. Funcionalidades Adicionales 🔧
- API REST para gestión manual de jobs
- Webhooks para notificaciones en tiempo real
- Backup/Export de resultados históricos
- A/B testing de diferentes prompts

### 4. Operaciones 🔧
- Docker containers para deployment
- Health checks y métricas de sistema
- Automated deployment con CI/CD
- Disaster recovery procedures

### 5. Análisis de Datos 📊
- Reports de efectividad por horario/región
- ML models para optimizar timing de llamadas
- Sentiment analysis de transcripciones
- Cost optimization basado en patrones históricos

## 🐛 Debugging

### Logs Principales
```bash
# Logs básicos del sistema
2025-09-22 13:34:57,943 | INFO | MainThread | Inicializando índices…

# Logs de debug detallado
[DEBUG] [bot-1] ✅ Job encontrado: 68d1713d30b0c91f2f9b5a38
[DEBUG] [68d1713d30b0c91f2f9b5a38] Context enviado a Retell: {...}
[DEBUG] [68d1713d30b0c91f2f9b5a38] ✅ Llamada creada exitosamente
```

### Estados de Job
- `pending` - Job listo para procesamiento
- `in_progress` - Job siendo procesado por un worker
- `done` - Job completado exitosamente
- `failed` - Job falló después de máximos reintentos

## 📄 Licencia

Este proyecto es propiedad de Je Je Group - Todos los derechos reservados.

## 👥 Contribución

Para contribuir al proyecto:
1. Fork el repositorio
2. Crea una branch de feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. Push a la branch (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📞 Soporte

Para soporte técnico, contacta al equipo de desarrollo a través de los canales internos de Je Je Group.

---

**Desarrollado por** Je Je Group - Speech AI Team  
**Versión:** 1.0.0  
**Última actualización:** Septiembre 2025

## 📌 Requerimientos de Usuario Originales
- Contactar automáticamente a un grupo de 60 deudores por día en tandas (9:00, 12:00, 15:00).
- No llamar más de 3 veces por día a la misma persona.
- Si se han hecho llamadas en 3 días diferentes sin respuesta, excluir de la lista.
- Permitir reagendado cuando el deudor lo solicite.
- Ejecutar un flujo de negociación según tipo de mora.
- Guardar historial de llamadas y resultado.
- Integrarse con sistemas MCP/Webhook para disparar acciones externas (ej: enviar link de pago por WhatsApp).
- Recuperarse automáticamente ante fallos o reinicios del servidor.
- Panel de control para ver estado y métricas.

---

## 🎯 Requerimientos de Diseño
- Arquitectura modular basada en N8N + Base de Datos SQL/Supabase.
- Separación de capas:  
  1. **Catálogos** (parámetros, reglas y configuraciones).  
  2. **Núcleo Operativo** (lógica de contacto, manejo de estados y timers).  
  3. **Operación** (registro de llamadas, reintentos y resultados).
- Resiliencia ante caídas del sistema (retomar proceso en el último punto).
- Escalabilidad para aumentar volumen de llamadas.
- Seguridad: acceso a la base con credenciales y cifrado en tránsito.
- Uso de variables dinámicas para personalizar el diálogo del agente.

---

## 🗄 Diagramas Entidad-Relación

### DER – Catálogos
![DER Catálogos](./catalogosDer.png)

### DER – Núcleo Operativo
![DER Núcleo Operativo](./nucleoOperativoDer.png)

### DER – Operación
![DER Operación](./operacionDer.png)

---

## 🔄 Diagrama de Flujo Temporal (Ejemplo)
*(Aquí iría otro diagrama UML o de flujo mostrando el proceso de llamadas, reintentos y exclusiones)*

---
# Desde el directorio principal
cd C:\Users\maria\OneDrive\Documents\proyectos\speechAi_backend
.\.venv\Scripts\python.exe app\call_worker.py

## 📂 Estructura de Archivos
