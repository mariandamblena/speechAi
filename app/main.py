"""
Punto de entrada principal de la aplicación
Implementa Dependency Injection y composición de servicios
"""

import logging
import sys
from typing import Optional

from config.settings import get_settings, AppSettings
from infrastructure.database import DatabaseService
from infrastructure.retell_client import RetellApiClient, IRetellClient
from services.job_service import JobService
from services.call_service import CallOrchestrationService
from services.worker_service import WorkerCoordinator


class Application:
    """
    Clase principal de la aplicación
    
    Implementa:
    - Dependency Injection pattern
    - Service composition
    - Application lifecycle management
    
    Sigue principios SOLID:
    - Single Responsibility: Solo inicializa y coordina la app
    - Dependency Inversion: Usa interfaces, inyecta dependencias
    """
    
    def __init__(self):
        self.settings: Optional[AppSettings] = None
        self.database: Optional[DatabaseService] = None
        self.retell_client: Optional[IRetellClient] = None
        self.job_service: Optional[JobService] = None
        self.call_service: Optional[CallOrchestrationService] = None
        self.worker_coordinator: Optional[WorkerCoordinator] = None
    
    def initialize(self) -> bool:
        """
        Inicializa todos los componentes de la aplicación
        
        Returns:
            True si la inicialización fue exitosa
        """
        try:
            # 1. Cargar configuración
            self.settings = get_settings()
            self._setup_logging()
            
            logger = logging.getLogger(__name__)
            logger.info("🚀 Iniciando Speech AI Call Worker")
            logger.info(f"Configuración: {self.settings.worker.count} workers, "
                       f"polling cada {self.settings.call.polling_interval_seconds}s")
            
            # 2. Inicializar infraestructura
            if not self._initialize_infrastructure():
                return False
            
            # 3. Crear servicios de aplicación
            if not self._initialize_services():
                return False
            
            # 4. Verificar conectividad
            if not self._health_check():
                return False
            
            logger.info("✅ Aplicación inicializada correctamente")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error inicializando aplicación: {e}")
            return False
    
    def run(self) -> int:
        """
        Ejecuta la aplicación principal
        
        Returns:
            Código de salida (0 = éxito, 1 = error)
        """
        logger = logging.getLogger(__name__)
        
        try:
            if not self.initialize():
                logger.error("Falló la inicialización")
                return 1
            
            logger.info("🏃 Iniciando workers...")
            
            # Iniciar coordinador de workers
            self.worker_coordinator.start_workers()
            
            # Esperar hasta recibir señal de shutdown
            logger.info("✅ Sistema activo. Presiona Ctrl+C para detener...")
            self.worker_coordinator.wait_for_shutdown()
            
            return 0
            
        except KeyboardInterrupt:
            logger.info("👋 Shutdown por Ctrl+C")
            return 0
            
        except Exception as e:
            logger.exception(f"💥 Error fatal: {e}")
            return 1
            
        finally:
            self.cleanup()
    
    def cleanup(self) -> None:
        """Limpieza de recursos al cerrar"""
        logger = logging.getLogger(__name__)
        logger.info("🧹 Limpiando recursos...")
        
        if self.worker_coordinator:
            self.worker_coordinator.shutdown()
        
        if self.database:
            self.database.close()
        
        logger.info("✅ Limpieza completada")
    
    def _setup_logging(self) -> None:
        """Configura el sistema de logging"""
        logging.basicConfig(
            level=getattr(logging, self.settings.logging.level.upper()),
            format=self.settings.logging.format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                # logging.FileHandler('call_worker.log'),  # Opcional
            ]
        )
        
        # Configurar niveles específicos
        logging.getLogger('pymongo').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    def _initialize_infrastructure(self) -> bool:
        """Inicializa componentes de infraestructura"""
        logger = logging.getLogger(__name__)
        
        try:
            # Base de datos
            logger.info("📊 Conectando a MongoDB...")
            self.database = DatabaseService(self.settings.database)
            
            # Cliente Retell
            logger.info("🤖 Inicializando cliente Retell...")
            self.retell_client = RetellApiClient(self.settings.retell)
            
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando infraestructura: {e}")
            return False
    
    def _initialize_services(self) -> bool:
        """Inicializa servicios de aplicación"""
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("⚙️ Inicializando servicios...")
            
            # Servicio de jobs
            self.job_service = JobService(
                job_repo=self.database.jobs,
                call_result_repo=self.database.call_results,
                config=self.settings.worker
            )
            
            # Servicio de llamadas
            self.call_service = CallOrchestrationService(
                retell_client=self.retell_client,
                call_config=self.settings.call,
                retell_config=self.settings.retell
            )
            
            # Coordinador de workers
            self.worker_coordinator = WorkerCoordinator(
                job_service=self.job_service,
                call_service=self.call_service,
                config=self.settings.worker
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando servicios: {e}")
            return False
    
    def _health_check(self) -> bool:
        """Verifica que todos los componentes estén funcionando"""
        logger = logging.getLogger(__name__)
        
        # Verificar base de datos
        if not self.database.health_check():
            logger.error("❌ Health check de base de datos falló")
            return False
        
        # Verificar configuraciones críticas
        if not self.settings.retell.agent_id:
            logger.error("❌ RETELL_AGENT_ID no configurado")
            return False
        
        logger.info("✅ Health check exitoso")
        return True
    
    def get_status(self) -> dict:
        """Obtiene estado actual de la aplicación"""
        status = {
            'initialized': self.settings is not None,
            'database_connected': self.database and self.database.health_check(),
        }
        
        if self.worker_coordinator:
            status.update(self.worker_coordinator.get_status())
        
        return status


def main() -> int:
    """
    Función principal
    
    Returns:
        Código de salida
    """
    app = Application()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())