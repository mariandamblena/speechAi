"""
Configuración centralizada del sistema. Desde aca defino todas las variables 
Siguiendo el principio de configuración única (Single Source of Truth)
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()


@dataclass(frozen=True) #frozen para que sea inmutable
class DatabaseConfig:
    """Configuración de base de datos MongoDB"""
    uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    database: str = os.getenv("MONGO_DB", "speechai_db")
    jobs_collection: str = os.getenv("MONGO_COLL_JOBS", "jobs")
    results_collection: str = os.getenv("MONGO_COLL_RESULTS", "call_results")
    logs_collection: str = os.getenv("MONGO_COLL_LOGS", "call_logs")
    accounts_collection: str = os.getenv("MONGO_COLL_ACCOUNTS", "accounts")
    batches_collection: str = os.getenv("MONGO_COLL_BATCHES", "batches")
    max_pool_size: int = int(os.getenv("MONGO_MAX_POOL_SIZE", "50"))


@dataclass(frozen=True)
class RetellConfig:
    """Configuración de Retell AI"""
    api_key: str = os.getenv("RETELL_API_KEY", "")
    base_url: str = os.getenv("RETELL_BASE_URL", "https://api.retellai.com")
    agent_id: str = os.getenv("RETELL_AGENT_ID", "")
    from_number: str = os.getenv("RETELL_FROM_NUMBER", "")
    timeout_seconds: int = int(os.getenv("RETELL_TIMEOUT_SECONDS", "30"))


@dataclass(frozen=True)
class WorkerConfig:
    """Configuración de workers"""
    count: int = int(os.getenv("WORKER_COUNT", "3"))
    lease_seconds: int = int(os.getenv("LEASE_SECONDS", "120"))
    max_attempts: int = int(os.getenv("MAX_ATTEMPTS", "3"))
    retry_delay_minutes: int = int(os.getenv("RETRY_DELAY_MINUTES", "30"))
    
    
@dataclass(frozen=True)
class CallConfig:
    """Configuración de llamadas y polling"""
    polling_interval_seconds: int = int(os.getenv("CALL_POLLING_INTERVAL", "10"))
    timeout_seconds: int = int(os.getenv("POLL_TIMEOUT_SECONDS", "300"))  # 5 minutos
    max_duration_minutes: int = int(os.getenv("CALL_MAX_DURATION_MINUTES", "10"))
    no_answer_retry_minutes: int = int(os.getenv("NO_ANSWER_RETRY_MINUTES", "60"))


@dataclass(frozen=True)
class LoggingConfig:
    """Configuración de logging"""
    level: str = os.getenv("LOG_LEVEL", "INFO")
    format: str = "%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s"


@dataclass(frozen=True)
class AppSettings:
    """Configuración principal de la aplicación"""
    database: DatabaseConfig
    retell: RetellConfig
    worker: WorkerConfig
    call: CallConfig
    logging: LoggingConfig
    
    @classmethod
    def load(cls) -> 'AppSettings':
        """Factory method para cargar configuración"""
        return cls(
            database=DatabaseConfig(),
            retell=RetellConfig(),
            worker=WorkerConfig(),
            call=CallConfig(),
            logging=LoggingConfig()
        )
    

    """'AppSettings' significa que este método devuelve un objeto de tipo AppSettings.Como la clase AppSettings aún no está completamente definida en el momento de escribir la función, se pone entre comillas ('AppSettings') → esto se llama forward reference.
"""

    def validate(self) -> None:
        """Valida que la configuración sea correcta"""
        errors = []
        
        if not self.retell.api_key:
            errors.append("RETELL_API_KEY es requerida")
            
        if not self.retell.agent_id:
            errors.append("RETELL_AGENT_ID es requerido")
            
        if self.worker.count <= 0:
            errors.append("WORKER_COUNT debe ser mayor a 0")
            
        if self.worker.lease_seconds <= 0:
            errors.append("LEASE_SECONDS debe ser mayor a 0")
            
        if errors:
            raise ValueError(f"Errores de configuración: {'; '.join(errors)}")


# Instancia global de configuración (Singleton)
settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """
    Obtiene la instancia de configuración (Singleton pattern)
    """
    global settings
    if settings is None:
        settings = AppSettings.load()
        settings.validate()
    return settings

""""
# en cualquier módulo de tu app
from config import get_settings

conf = get_settings()
print(conf.database.uri)       # Accede a la URI de MongoDB
print(conf.retell.api_key)     # Accede a la API key de Retell

osea en cualquier parte del codigo llamo a get_settings() y me devuelve la configuración validada
"""