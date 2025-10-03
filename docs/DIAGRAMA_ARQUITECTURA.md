# 📐 Diagrama de Arquitectura del Sistema - SpeechAI Backend

```mermaid
C4Context
    title Diagrama de Contexto - SpeechAI Backend

    Person(admin, "Administrador", "Gestiona el sistema y configura parámetros")
    Person(operator, "Operador", "Carga datos y supervisa llamadas")
    Person(customer, "Cliente/Deudor", "Recibe llamadas automáticas")

    System(speechai, "SpeechAI Backend", "Sistema de llamadas automatizadas")
    
    System_Ext(retell, "Retell AI", "Plataforma de llamadas con IA")
    System_Ext(mongo, "MongoDB", "Base de datos principal")
    System_Ext(excel, "Archivos Excel", "Fuente de datos de contactos")

    Rel(admin, speechai, "Configura y administra")
    Rel(operator, speechai, "Carga datos y monitorea")
    Rel(speechai, customer, "Realiza llamadas automáticas")
    Rel(speechai, retell, "API calls para gestión de llamadas")
    Rel(speechai, mongo, "Persiste jobs, batches y resultados")
    Rel(speechai, excel, "Procesa archivos de contactos")
```

```mermaid
C4Container
    title Diagrama de Contenedores - SpeechAI Backend

    Person(users, "Usuarios", "Administradores y Operadores")
    Person(customers, "Clientes", "Receptores de llamadas")

    Container_Boundary(speechai, "SpeechAI Backend") {
        Container(api, "FastAPI Server", "Python, FastAPI", "API REST para gestión del sistema")
        Container(workers, "Call Workers", "Python, Threading", "Procesadores de llamadas en paralelo")
        Container(config, "Configuration", "Python, Pydantic", "Gestión centralizada de configuración")
    }

    ContainerDb(mongodb, "MongoDB", "NoSQL Database", "Almacena jobs, batches, resultados y logs")
    System_Ext(retell, "Retell AI", "Plataforma de IA conversacional")

    Rel(users, api, "HTTPS")
    Rel(api, workers, "Shared memory, queues")
    Rel(workers, retell, "HTTPS API")
    Rel(api, mongodb, "MongoDB Protocol")
    Rel(workers, mongodb, "MongoDB Protocol")
    Rel(workers, customers, "Phone calls via Retell")
    Rel(config, api, "Settings")
    Rel(config, workers, "Settings")
```

```mermaid
C4Component
    title Diagrama de Componentes - Capa de Aplicación

    Container_Boundary(api, "FastAPI Application") {
        Component(endpoints, "API Endpoints", "FastAPI Controllers", "Expone funcionalidades vía REST")
        Component(middleware, "Middleware", "FastAPI Middleware", "Logging, CORS, validación")
    }

    Container_Boundary(services, "Service Layer") {
        Component(batch_service, "Batch Service", "Python Class", "Gestión de lotes de llamadas")
        Component(job_service, "Job Service", "Python Class", "CRUD y lógica de jobs")
        Component(call_service, "Call Service", "Python Class", "Orquestación de llamadas")
        Component(worker_service, "Worker Service", "Python Class", "Coordinación de workers")
    }

    Container_Boundary(domain, "Domain Layer") {
        Component(models, "Domain Models", "Pydantic Models", "JobModel, BatchModel, ContactInfo")
        Component(enums, "Enumerations", "Python Enums", "Estados y tipos del sistema")
        Component(use_cases, "Use Case Processors", "Python Classes", "Lógica específica por caso de uso")
    }

    Container_Boundary(infrastructure, "Infrastructure Layer") {
        Component(db_manager, "Database Manager", "Motor AsyncIO", "Abstracción de MongoDB")
        Component(retell_client, "Retell Client", "httpx AsyncClient", "Cliente HTTP para Retell AI")
    }

    Container_Boundary(utils, "Utilities") {
        Component(excel_processor, "Excel Processor", "pandas, openpyxl", "Procesamiento de archivos Excel")
        Component(report_generator, "Report Generator", "pandas, openpyxl", "Generación de reportes")
        Component(timezone_utils, "Timezone Utils", "pytz", "Manejo de zonas horarias")
    }

    ContainerDb(mongodb, "MongoDB", "NoSQL Database")
    System_Ext(retell_api, "Retell AI API", "External API")

    Rel(endpoints, batch_service, "uses")
    Rel(endpoints, job_service, "uses")
    Rel(endpoints, excel_processor, "uses")
    
    Rel(batch_service, db_manager, "uses")
    Rel(job_service, db_manager, "uses")
    Rel(call_service, retell_client, "uses")
    Rel(worker_service, job_service, "uses")
    Rel(worker_service, call_service, "uses")
    
    Rel(batch_service, models, "uses")
    Rel(job_service, models, "uses")
    Rel(call_service, models, "uses")
    
    Rel(excel_processor, use_cases, "uses")
    Rel(use_cases, models, "creates")
    
    Rel(db_manager, mongodb, "MongoDB Protocol")
    Rel(retell_client, retell_api, "HTTPS")
    
    Rel(report_generator, db_manager, "queries")
    Rel(timezone_utils, models, "assists")
```

---

## 🏗️ Arquitectura de Despliegue

```mermaid
deployment
    title Diagrama de Despliegue - SpeechAI Backend

    node "Production Server" as prod_server {
        node "Docker Container: speechai-api" as api_container {
            artifact "FastAPI Application" as api_app
            artifact "Configuration Files" as config_files
        }
        
        node "Docker Container: speechai-workers" as worker_container {
            artifact "Call Workers" as workers
            artifact "Worker Coordinator" as coordinator
        }
        
        node "Docker Container: mongodb" as mongo_container {
            database "MongoDB Database" as mongodb
            artifact "Data Volumes" as data_volumes
        }
    }

    node "External Services" as external {
        cloud "Retell AI Platform" as retell_cloud
        cloud "Monitoring Service" as monitoring
        cloud "Log Aggregation" as logs
    }

    node "Development Environment" as dev_env {
        artifact "Local MongoDB" as local_mongo
        artifact "Development Server" as dev_server
        artifact "Test Scripts" as test_scripts
    }

    node "Client Access" as clients {
        artifact "Web Browser" as browser
        artifact "API Clients" as api_clients
        artifact "Admin Tools" as admin_tools
    }

    api_container --> mongo_container : "Database connections"
    worker_container --> mongo_container : "Database connections"
    worker_container --> retell_cloud : "API calls"
    
    api_container --> monitoring : "Health metrics"
    worker_container --> monitoring : "Performance metrics"
    
    api_container --> logs : "Application logs"
    worker_container --> logs : "Worker logs"
    
    clients --> api_container : "HTTPS requests"
    
    dev_env --> external : "Testing connections"
```

---

## 🔄 Flujo de Datos

```mermaid
graph LR
    %% ===== FUENTES DE DATOS =====
    subgraph "📊 Data Sources"
        Excel[📁 Excel Files]
        Config[⚙️ Configuration]
        RetellAPI[🤖 Retell AI API]
    end

    %% ===== PROCESAMIENTO =====
    subgraph "🔄 Processing Layer"
        ExcelProc[📊 Excel Processor]
        JobGen[📋 Job Generator]
        CallOrch[📞 Call Orchestrator]
        Workers[👷 Workers Pool]
    end

    %% ===== ALMACENAMIENTO =====
    subgraph "💾 Data Storage"
        MongoDB[(🗄️ MongoDB)]
        Logs[📝 Log Files]
        Reports[📈 Generated Reports]
    end

    %% ===== SALIDAS =====
    subgraph "📤 Outputs"
        Dashboard[🎛️ Dashboard]
        ExcelReports[📊 Excel Reports]
        RealTimeMetrics[📈 Real-time Metrics]
        Notifications[📧 Notifications]
    end

    %% ===== FLUJO DE DATOS =====
    Excel --> ExcelProc
    Config --> ExcelProc
    ExcelProc --> JobGen
    JobGen --> MongoDB
    
    MongoDB --> Workers
    Workers --> CallOrch
    CallOrch --> RetellAPI
    RetellAPI --> CallOrch
    CallOrch --> MongoDB
    
    Workers --> Logs
    MongoDB --> Reports
    
    MongoDB --> Dashboard
    Reports --> ExcelReports
    MongoDB --> RealTimeMetrics
    Logs --> Notifications
    
    %% ===== TRANSFORMACIONES =====
    ExcelProc -.-> |"Validate & Transform"| JobGen
    JobGen -.-> |"Batch Creation"| MongoDB
    Workers -.-> |"Status Updates"| MongoDB
    CallOrch -.-> |"Call Results"| MongoDB
    MongoDB -.-> |"Aggregation"| Reports

    %% ===== ESTILOS =====
    classDef source fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef process fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef storage fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef output fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    
    class Excel,Config,RetellAPI source
    class ExcelProc,JobGen,CallOrch,Workers process
    class MongoDB,Logs,Reports storage
    class Dashboard,ExcelReports,RealTimeMetrics,Notifications output
```

---

## 🔐 Diagrama de Seguridad

```mermaid
graph TD
    %% ===== CAPAS DE SEGURIDAD =====
    subgraph "🔒 Security Layers"
        API_Gateway[🌐 API Gateway / Load Balancer]
        Auth[🔐 Authentication Layer]
        Validation[✅ Input Validation]
        RateLimit[⏱️ Rate Limiting]
    end

    %% ===== CONFIGURACIÓN SEGURA =====
    subgraph "⚙️ Secure Configuration"
        EnvVars[🔑 Environment Variables]
        Secrets[🗝️ Secrets Management]
        TLS[🔒 TLS/HTTPS]
        Networks[🌐 Network Isolation]
    end

    %% ===== MONITOREO =====
    subgraph "👁️ Security Monitoring"
        Logging[📝 Security Logging]
        Monitoring[📊 Security Monitoring]
        Alerts[🚨 Security Alerts]
        Audit[📋 Audit Trail]
    end

    %% ===== DATOS SENSIBLES =====
    subgraph "🗄️ Data Protection"
        Encryption[🔐 Data Encryption]
        Backup[💾 Secure Backups]
        DataMask[🎭 Data Masking]
        Retention[🗓️ Data Retention]
    end

    %% ===== FLUJO DE SEGURIDAD =====
    Client[👤 Client] --> API_Gateway
    API_Gateway --> Auth
    Auth --> Validation
    Validation --> RateLimit
    RateLimit --> Application[🚀 Application]
    
    Application --> EnvVars
    Application --> Secrets
    Application --> TLS
    
    Application --> Logging
    Logging --> Monitoring
    Monitoring --> Alerts
    
    Application --> Encryption
    Encryption --> Backup
    
    %% ===== PROTECCIONES ESPECÍFICAS =====
    Validation -.-> SQLInjection[🛡️ SQL Injection Protection]
    Validation -.-> XSS[🛡️ XSS Protection]
    RateLimit -.-> DDoS[🛡️ DDoS Protection]
    Auth -.-> JWT[🎫 JWT Tokens]
    
    %% ===== CUMPLIMIENTO =====
    Audit --> Compliance[📋 Compliance Reporting]
    DataMask --> Privacy[👤 Privacy Protection]
    Retention --> GDPR[📄 GDPR Compliance]

    %% ===== ESTILOS =====
    classDef security fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef config fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef monitor fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef data fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef protection fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    
    class API_Gateway,Auth,Validation,RateLimit security
    class EnvVars,Secrets,TLS,Networks config
    class Logging,Monitoring,Alerts,Audit monitor
    class Encryption,Backup,DataMask,Retention data
    class SQLInjection,XSS,DDoS,JWT,Compliance,Privacy,GDPR protection
```

---

## 📊 Diagrama de Escalabilidad

```mermaid
graph TB
    %% ===== ESCALABILIDAD HORIZONTAL =====
    subgraph "📈 Horizontal Scaling"
        LB[⚖️ Load Balancer]
        API1[🌐 API Instance 1]
        API2[🌐 API Instance 2]
        API3[🌐 API Instance N]
        
        Workers1[👷 Worker Pool 1]
        Workers2[👷 Worker Pool 2]
        Workers3[👷 Worker Pool N]
    end

    %% ===== ESCALABILIDAD DE DATOS =====
    subgraph "🗄️ Data Scaling"
        MongoCluster[🗄️ MongoDB Cluster]
        Primary[(🗄️ Primary)]
        Secondary1[(🗄️ Secondary 1)]
        Secondary2[(🗄️ Secondary 2)]
        
        Sharding[🔀 Sharding Strategy]
        Indexing[📑 Advanced Indexing]
    end

    %% ===== CACHE Y PERFORMANCE =====
    subgraph "⚡ Performance Layer"
        Redis[🔄 Redis Cache]
        CDN[🌐 CDN]
        Queue[📬 Job Queue]
        Metrics[📊 Metrics Collection]
    end

    %% ===== MONITOREO DE ESCALABILIDAD =====
    subgraph "📊 Scaling Monitoring"
        AutoScale[🔄 Auto Scaling]
        HealthCheck[💚 Health Checks]
        ResourceMonitor[📈 Resource Monitoring]
        AlertManager[🚨 Alert Manager]
    end

    %% ===== CONEXIONES =====
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> Workers1
    API2 --> Workers2
    API3 --> Workers3
    
    Workers1 --> Queue
    Workers2 --> Queue
    Workers3 --> Queue
    
    API1 --> MongoCluster
    API2 --> MongoCluster
    API3 --> MongoCluster
    
    MongoCluster --> Primary
    Primary --> Secondary1
    Primary --> Secondary2
    
    API1 --> Redis
    API2 --> Redis
    API3 --> Redis
    
    AutoScale --> LB
    HealthCheck --> API1
    HealthCheck --> API2
    HealthCheck --> API3
    
    ResourceMonitor --> AlertManager
    Metrics --> ResourceMonitor

    %% ===== ESTRATEGIAS DE ESCALADO =====
    AutoScale -.-> CPUScaling[📊 CPU-based Scaling]
    AutoScale -.-> QueueScaling[📬 Queue-based Scaling]
    AutoScale -.-> TimeScaling[⏰ Time-based Scaling]
    
    Sharding -.-> DateSharding[📅 Date-based Sharding]
    Sharding -.-> BatchSharding[📦 Batch-based Sharding]
    
    %% ===== ESTILOS =====
    classDef scaling fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef data fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef performance fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef monitoring fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef strategy fill:#ffebee,stroke:#c62828,stroke-width:2px
    
    class LB,API1,API2,API3,Workers1,Workers2,Workers3 scaling
    class MongoCluster,Primary,Secondary1,Secondary2,Sharding,Indexing data
    class Redis,CDN,Queue,Metrics performance
    class AutoScale,HealthCheck,ResourceMonitor,AlertManager monitoring
    class CPUScaling,QueueScaling,TimeScaling,DateSharding,BatchSharding strategy
```

---

## 📝 Resumen de Documentación de Arquitectura

### 📐 **Diagramas Creados**

1. **🏗️ Diagrama de Contexto (C4)**: Vista general del sistema y actores externos
2. **📦 Diagrama de Contenedores**: Distribución de componentes principales
3. **🔧 Diagrama de Componentes**: Estructura interna detallada
4. **🚀 Diagrama de Despliegue**: Arquitectura de infraestructura
5. **🔄 Flujo de Datos**: Transformación y movimiento de información
6. **🔐 Diagrama de Seguridad**: Capas de protección y controles
7. **📈 Diagrama de Escalabilidad**: Estrategias de crecimiento

### 🎯 **Principios Arquitectónicos**

- **🏛️ Clean Architecture**: Separación clara de responsabilidades
- **🔄 Domain Driven Design**: Modelado centrado en el dominio de negocio
- **📦 Microservicios Modulares**: Componentes débilmente acoplados
- **⚡ Asíncrono por Defecto**: Operaciones no bloqueantes
- **🔒 Seguridad por Capas**: Múltiples niveles de protección
- **📊 Observabilidad**: Monitoreo y métricas integradas
- **🚀 Escalabilidad Horizontal**: Crecimiento distribuido

### 📊 **Métricas de Arquitectura**

- **Disponibilidad**: 99.5% uptime objetivo
- **Latencia**: < 2s para operaciones críticas  
- **Throughput**: 10 jobs/minuto por worker
- **Escalabilidad**: Lineal con número de workers
- **Recuperación**: < 30s para fallos temporales