# 🏗️ Estructura del Proyecto SpeechAI Backend

## 📁 Organización de Directorios

```
speechAi_backend/
├── 📱 app/                          # Aplicación principal
│   ├── 🏛️ domain/                   # Capa de Dominio (Clean Architecture)
│   │   ├── models.py                # Entidades y modelos de dominio
│   │   └── enums.py                 # Enumeraciones del dominio
│   │
│   ├── 🚀 services/                 # Capa de Aplicación (Casos de uso)
│   │   ├── account_service.py       # Gestión de cuentas
│   │   ├── batch_service.py         # Gestión de batches
│   │   ├── batch_creation_service.py # Creación de batches desde Excel
│   │   └── job_service_api.py       # Gestión de jobs para API
│   │
│   ├── 🏗️ infrastructure/           # Capa de Infraestructura
│   │   └── database_manager.py      # Manager para MongoDB con Motor
│   │
│   ├── 🌐 api.py                    # Capa de Interface (API REST)
│   ├── ⚙️ config/                   # Configuración
│   │   └── settings.py              # Settings de la aplicación
│   │
│   ├── 🛠️ utils/                    # Utilidades
│   │   ├── excel_processor.py       # Procesamiento de archivos Excel
│   │   └── legacy_adapter.py        # Adaptador para sistemas legacy
│   │
│   ├── 🧪 tests/                    # Tests unitarios e integración
│   │   ├── test_excel_batch.py      # Tests de creación de batches
│   │   └── test_structure.py        # Tests de estructura
│   │
│   ├── 📜 scripts/                  # Scripts de desarrollo
│   │   ├── create_indexes.py        # Creación de índices MongoDB
│   │   ├── init_data.py             # Inicialización de datos
│   │   └── reset_job.py             # Reinicio de jobs
│   │
│   ├── 🚀 run_api.py               # Punto de entrada de la API
│   ├── 🔧 call_worker.py           # Worker para procesamiento de llamadas
│   ├── 📋 requirements.txt          # Dependencias Python
│   └── 🧪 test_api.py              # Tests de API
│
├── 📜 scripts/                      # Scripts de utilidad del proyecto
│   ├── check_db.py                  # Verificación de base de datos
│   ├── test_job_creation.py         # Test de creación de jobs
│   └── analyze_batch_discrepancies.py # Análisis de discrepancias
│
├── 📚 docs/                         # Documentación
│   ├── 📁 guides/                   # Guías y documentación detallada
│   │   ├── COST_GUIDE.md           # Guía de costos
│   │   ├── TESTING_GUIDE.md        # Guía de testing
│   │   └── WEBHOOK_README.md       # Documentación de webhooks
│   │
│   └── 📁 workflows/               # Workflows y diagramas
│       ├── Adquisicion_v3.json     # Workflow principal
│       ├── Llamada_v3.json         # Workflow de llamadas
│       └── ...                     # Otros workflows
│
├── 📊 sql/                          # Scripts SQL y esquemas
│   ├── catalogos.sql               # Catálogos de base de datos
│   ├── nucleoOperativo.sql         # Núcleo operativo
│   └── operacion.sql               # Operaciones
│
├── 🖼️ *.png                        # Diagramas de base de datos
├── 📝 README.md                    # Documentación principal
└── 📋 STRUCTURE_NEW.md             # Estructura actualizada

```

## 🏛️ Arquitectura Clean Architecture + DDD

### **Capas Implementadas:**

1. **🏛️ Domain Layer** (`app/domain/`)
   - **Entidades Puras**: `JobModel`, `BatchModel`, `AccountModel`
   - **Value Objects**: `ContactInfo`, `CallPayload`
   - **Enums**: `JobStatus`, `CallMode`, `PlanType`

2. **🚀 Application Layer** (`app/services/`)
   - **Casos de Uso**: Creación de batches, gestión de jobs
   - **Servicios de Aplicación**: Lógica de negocio
   - **Anti-corrupción**: Procesamiento de Excel con validaciones

3. **🏗️ Infrastructure Layer** (`app/infrastructure/`)
   - **Persistencia**: `DatabaseManager` con Motor (MongoDB async)
   - **APIs Externas**: Integraciones con servicios externos

4. **🌐 Interface Layer** (`app/api.py`)
   - **Controllers REST**: Endpoints FastAPI
   - **DTOs**: Serialización JSON
   - **Dependency Injection**: Inyección de dependencias

## 📊 Principios SOLID Implementados

- **S** - Single Responsibility: Cada clase tiene una responsabilidad
- **O** - Open/Closed: Extensible via interfaces
- **L** - Liskov Substitution: Implementaciones intercambiables
- **I** - Interface Segregation: Interfaces pequeñas y específicas  
- **D** - Dependency Inversion: Depende de abstracciones

## 🔧 Scripts de Utilidad

| Script | Ubicación | Propósito |
|--------|-----------|-----------|
| `check_db.py` | `scripts/` | Verificar estado de la base de datos |
| `test_job_creation.py` | `scripts/` | Probar creación de jobs desde Excel |
| `analyze_batch_discrepancies.py` | `scripts/` | Analizar diferencias deudores vs jobs |
| `create_indexes.py` | `app/scripts/` | Crear índices de MongoDB |
| `init_data.py` | `app/scripts/` | Inicializar datos de prueba |

## 📚 Documentación

| Archivo | Ubicación | Contenido |
|---------|-----------|-----------|
| `README.md` | Raíz | Documentación principal del proyecto |
| `COST_GUIDE.md` | `docs/guides/` | Guía de cálculo de costos |
| `TESTING_GUIDE.md` | `docs/guides/` | Guía de testing y pruebas |
| `WEBHOOK_README.md` | `docs/guides/` | Documentación de webhooks |

## 🚀 Puntos de Entrada

- **API REST**: `python app/run_api.py`
- **Worker de Llamadas**: `python app/call_worker.py`
- **Tests**: `pytest app/tests/`
- **Scripts**: `python scripts/<script_name>.py`

## 🔍 Análisis de Discrepancias Deudores vs Jobs

### **Causas Comunes de Diferencias:**

#### **🚫 MENOS Jobs que Deudores:**
1. **Deudores sin teléfono válido** - Se saltan durante la creación
2. **RUTs inválidos o malformados** - No pasan validación
3. **Datos corruptos en Excel** - Errores de procesamiento
4. **Límites de memoria** - Para archivos muy grandes

#### **📈 MÁS Jobs que Deudores:**
1. **Claves de deduplicación duplicadas** - Error en lógica anti-duplicación
2. **Múltiples ejecuciones** - Mismo batch procesado varias veces
3. **Reintentos automáticos** - Jobs adicionales por errores
4. **Timing issues** - Requests simultáneas

### **🛠️ Herramientas de Diagnóstico:**
```bash
# Analizar discrepancias en batch específico
python scripts/analyze_batch_discrepancies.py BATCH_ID

# Analizar batch más reciente
python scripts/analyze_batch_discrepancies.py

# Verificar estado general de la DB
python scripts/check_db.py
```