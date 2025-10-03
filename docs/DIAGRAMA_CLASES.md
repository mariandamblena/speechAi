# 📐 Diagrama de Clases - SpeechAI Backend

```mermaid
classDiagram
    %% ===== DOMAIN LAYER =====
    class JobModel {
        +ObjectId _id
        +str rut
        +str batch_id
        +ContactInfo contact
        +dict payload
        +dict additional_info
        +JobStatus status
        +int attempts
        +datetime created_at
        +datetime reserved_until
        +CallResult call_result
        +bool is_success
        +validate()
        +to_dict()
        +from_dict()
    }

    class ContactInfo {
        +str name
        +str dni/rut
        +List[str] phones
        +int next_phone_index
        +str email
        +str current_phone
        +advance_phone()
        +has_more_phones()
    }

    class BatchModel {
        +ObjectId _id
        +str account_id
        +str batch_id
        +str name
        +str description
        +int priority
        +bool is_active
        +bool is_completed
        +datetime created_at
        +datetime completed_at
        +BatchStats stats
        +update_stats()
        +pause()
        +resume()
    }

    class CallResult {
        +str call_id
        +str call_status
        +int duration_ms
        +dict transcript
        +dict analysis
        +CostInfo call_cost
        +datetime ended_at
        +bool is_successful()
    }

    class CostInfo {
        +float retell_cost
        +float transport_cost
        +float combined_cost
        +str currency
        +calculate_total()
    }

    %% ===== ENUMS =====
    class JobStatus {
        <<enumeration>>
        PENDING
        IN_PROGRESS
        COMPLETED
        DONE
        FAILED
        SUSPENDED
    }

    class CallStatus {
        <<enumeration>>
        REGISTERED
        ONGOING
        ENDED
        ERROR
        TRANSFERRED
        +is_final_status()
    }

    class UseCaseType {
        <<enumeration>>
        DEBT_COLLECTION
        MARKETING
        SURVEY
        REMINDER
        NOTIFICATION
    }

    %% ===== USE CASES =====
    class BaseUseCaseProcessor {
        <<abstract>>
        +str use_case_type
        +extract_variables(dict)
        +validate_row(dict)
        +process_additional_info(dict)
    }

    class DebtCollectionProcessor {
        +extract_variables(dict)
        +validate_debt_amount(float)
        +format_due_date(str)
        +calculate_interest(dict)
    }

    class MarketingProcessor {
        +extract_variables(dict)
        +validate_demographics(dict)
        +segment_customer(dict)
    }

    %% ===== SERVICES =====
    class BatchService {
        -DatabaseManager db_manager
        +create_batch(str, str, str)
        +get_batch(str)
        +update_batch_stats(str)
        +pause_batch(str)
        +resume_batch(str)
        +delete_batch(str, bool)
        +get_batch_summary(str)
    }

    class JobService {
        -DatabaseManager db_manager
        +create_jobs_from_batch(BatchModel, List[dict])
        +claim_pending_job(str)
        +complete_job_successfully(JobModel, str, dict)
        +fail_job(JobModel, str, bool)
        +advance_to_next_phone(JobModel)
        +get_job_by_id(str)
        +retry_job(str)
    }

    class CallOrchestrationService {
        -RetellClient retell_client
        -JobService job_service
        +execute_call_workflow(JobModel)
        +create_call(JobModel)
        +poll_call_status(str)
        +handle_call_completion(str, dict)
    }

    class WorkerCoordinator {
        -JobService job_service
        -CallOrchestrationService call_service
        -WorkerConfig config
        -bool running
        -List[Thread] workers
        +start_workers()
        +shutdown()
        +wait_for_shutdown()
        -worker_loop(str)
        -process_job(str, JobModel)
    }

    %% ===== INFRASTRUCTURE =====
    class DatabaseManager {
        -AsyncIOMotorClient client
        -AsyncIOMotorDatabase database
        +get_collection(str)
        +close()
        +create_indexes()
    }

    class RetellClient {
        -str api_key
        -str base_url
        -httpx.AsyncClient client
        +create_call(dict)
        +get_call_status(str)
        +list_calls()
        +delete_call(str)
    }

    %% ===== CONFIGURATION =====
    class AppSettings {
        +DatabaseConfig database
        +RetellConfig retell
        +WorkerConfig worker
        +CallConfig call
        +LoggingConfig logging
        +validate()
        +load()
    }

    class WorkerConfig {
        +int count
        +int lease_seconds
        +int max_attempts
        +int retry_delay_minutes
    }

    %% ===== UTILITIES =====
    class ExcelProcessor {
        +detect_format(pandas.DataFrame)
        +process_debt_collection(pandas.DataFrame)
        +process_marketing(pandas.DataFrame)
        +process_generic(pandas.DataFrame)
        +validate_required_columns(pandas.DataFrame, List[str])
    }

    class JobsReportGenerator {
        -DatabaseManager db_manager
        +generate_terminal_report()
        +generate_excel_report()
        +generate_markdown_report()
        +get_general_stats()
        +get_attempts_analysis()
        +get_temporal_analysis()
    }

    %% ===== RELATIONSHIPS =====
    JobModel --> ContactInfo : contains
    JobModel --> CallResult : has
    JobModel --> JobStatus : status
    CallResult --> CostInfo : cost_info
    CallResult --> CallStatus : status
    BatchModel --> JobModel : contains many
    
    BaseUseCaseProcessor <|-- DebtCollectionProcessor
    BaseUseCaseProcessor <|-- MarketingProcessor
    BaseUseCaseProcessor --> UseCaseType : implements
    
    BatchService --> DatabaseManager : uses
    JobService --> DatabaseManager : uses
    CallOrchestrationService --> RetellClient : uses
    CallOrchestrationService --> JobService : uses
    WorkerCoordinator --> JobService : uses
    WorkerCoordinator --> CallOrchestrationService : uses
    
    AppSettings --> WorkerConfig : contains
    AppSettings --> DatabaseManager : configures
    AppSettings --> RetellClient : configures
    
    ExcelProcessor --> BaseUseCaseProcessor : uses
    JobsReportGenerator --> DatabaseManager : uses

    %% ===== API LAYER =====
    class FastAPIApp {
        +upload_excel()
        +create_batch()
        +get_batches()
        +pause_batch()
        +resume_batch()
        +get_jobs()
        +retry_job()
        +health_check()
    }

    FastAPIApp --> BatchService : uses
    FastAPIApp --> JobService : uses
    FastAPIApp --> ExcelProcessor : uses
```

## 📝 Descripción de Componentes Principales

### 🏛️ **Domain Layer**
- **JobModel**: Entidad principal que representa un trabajo de llamada
- **ContactInfo**: Información de contacto con gestión de múltiples teléfonos
- **BatchModel**: Agrupación de jobs con control de estado
- **CallResult**: Resultado completo de una llamada con costos y transcripción

### 🚀 **Services Layer**
- **BatchService**: Gestión completa de lotes de trabajo
- **JobService**: CRUD y lógica de negocio de jobs individuales
- **CallOrchestrationService**: Orquestación del flujo completo de llamadas
- **WorkerCoordinator**: Coordinación de workers paralelos

### 🏗️ **Infrastructure Layer**
- **DatabaseManager**: Abstracción de MongoDB con conexiones async
- **RetellClient**: Cliente HTTP para interactuar con Retell AI API

### 🛠️ **Utilities**
- **ExcelProcessor**: Procesamiento inteligente de archivos Excel
- **JobsReportGenerator**: Generación de reportes en múltiples formatos

### ⚙️ **Configuration**
- **AppSettings**: Configuración centralizada con validación
- **WorkerConfig**: Configuración específica de workers

---

## 🔗 Patrones de Diseño Implementados

1. **Repository Pattern**: DatabaseManager abstrae el acceso a datos
2. **Factory Pattern**: BaseUseCaseProcessor para diferentes tipos de casos
3. **Strategy Pattern**: Múltiples procesadores de Excel según formato
4. **Observer Pattern**: Polling system para estado de llamadas
5. **Command Pattern**: Jobs como comandos ejecutables
6. **Singleton Pattern**: AppSettings como configuración única
7. **Builder Pattern**: JobModel construction con validaciones