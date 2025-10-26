"""
Servicio de coordinación de workers
Maneja el ciclo de vida de workers y procesamiento de jobs
"""

import logging
import signal
import threading
import time
import random
from typing import List, Callable

from services.job_service import JobService
from services.call_service import CallOrchestrationService
from config.settings import WorkerConfig

logger = logging.getLogger(__name__)


class WorkerCoordinator:
    """
    Coordinador de workers para procesamiento de jobs
    
    Responsabilidades:
    - Crear y gestionar threads de workers
    - Graceful shutdown
    - Distribución de carga con jitter
    - Manejo de errores y recuperación
    
    Sigue principios SOLID:
    - Single Responsibility: Solo coordina workers
    - Open/Closed: Extensible para diferentes tipos de workers
    """
    
    def __init__(
        self,
        job_service: JobService,
        call_service: CallOrchestrationService,
        config: WorkerConfig
    ):
        self.job_service = job_service
        self.call_service = call_service
        self.config = config
        
        # Control de workers
        self.running = True
        self.workers: List[threading.Thread] = []
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
    
    def start_workers(self) -> None:
        """
        Inicia todos los workers especificados en la configuración
        """
        logger.info(f"Iniciando {self.config.count} workers...")
        
        for i in range(self.config.count):
            worker_name = f"worker-{i+1}"
            worker_thread = threading.Thread(
                target=self._worker_loop,
                args=(worker_name,),
                daemon=True,
                name=worker_name
            )
            
            self.workers.append(worker_thread)
            worker_thread.start()
        
        logger.info(f"✅ {self.config.count} workers iniciados correctamente")
    
    def wait_for_shutdown(self) -> None:
        """
        Espera hasta que se reciba señal de shutdown
        """
        try:
            while self.running:
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Ctrl+C detectado, iniciando shutdown...")
            self.shutdown()
    
    def shutdown(self) -> None:
        """
        Para todos los workers de forma ordenada
        """
        logger.info("🛑 Iniciando shutdown de workers...")
        self.running = False
        
        # Esperar que terminen los workers (con timeout)
        for worker in self.workers:
            worker.join(timeout=10.0)
            if worker.is_alive():
                logger.warning(f"Worker {worker.name} no terminó en tiempo esperado")
        
        logger.info("✅ Shutdown completado")
    
    def _worker_loop(self, worker_name: str) -> None:
        """
        Loop principal de un worker individual
        
        Args:
            worker_name: Nombre identificador del worker
        """
        # Jitter inicial para evitar "thundering herd"
        worker_num = int(worker_name.split('-')[1])
        initial_delay = (worker_num - 1) * 0.5 + random.uniform(0, 0.5)
        
        logger.info(f"[{worker_name}] Iniciando en {initial_delay:.2f}s...")
        time.sleep(initial_delay)
        
        consecutive_empty_polls = 0
        processed_jobs = 0
        
        while self.running:
            try:
                # 1. Intentar obtener un job
                job = self.job_service.claim_pending_job(worker_name)
                
                if not job:
                    # No hay jobs disponibles
                    consecutive_empty_polls += 1
                    delay = self._calculate_backoff_delay(consecutive_empty_polls)
                    time.sleep(delay)
                    continue
                
                # Reset contador de polls vacíos
                consecutive_empty_polls = 0
                processed_jobs += 1
                
                logger.info(
                    f"[{worker_name}] 🚀 Procesando job #{processed_jobs}: "
                    f"{job.contact.dni if job.contact else 'unknown'}"
                )
                
                # 2. Procesar el job
                self._process_job(worker_name, job)
                
            except Exception as e:
                logger.exception(f"[{worker_name}] Error en worker loop: {e}")
                time.sleep(2.0 * self._random_jitter())
        
        logger.info(f"[{worker_name}] Worker terminado ({processed_jobs} jobs procesados)")
    
    def _process_job(self, worker_name: str, job) -> None:
        """
        Procesa un job individual
        
        Args:
            worker_name: Nombre del worker
            job: Job a procesar
        """
        try:
            # Ejecutar workflow de llamada
            result = self.call_service.execute_call_workflow(job)
            
            if result['success']:
                # Llamada exitosa
                call_data = result['data']
                call_id = result['call_id']
                
                success = self.job_service.complete_job_successfully(
                    job=job,
                    call_id=call_id,
                    call_data=call_data
                )
                
                if success:
                    logger.info(
                        f"[{worker_name}] ✅ Job completado: "
                        f"{job.contact.dni if job.contact else 'unknown'} "
                        f"-> {call_data.get('call_status', 'unknown')}"
                    )
                else:
                    logger.error(f"[{worker_name}] Error guardando resultado del job")
            
            else:
                # Llamada falló
                error = result['error']
                call_id = result.get('call_id')
                
                # Determinar si debemos reintentar
                should_retry = self._should_retry_job(job, error)
                
                # Si es un problema de teléfono específico, intentar con el siguiente
                if call_id and self.job_service.should_retry_with_different_phone(job, error):
                    if self.job_service.advance_to_next_phone(job):
                        logger.info(
                            f"[{worker_name}] 📞 Reintentando con siguiente teléfono: "
                            f"{job.contact.current_phone}"
                        )
                        return  # El job fue puesto de vuelta en pending
                
                # Fallar el job (con o sin retry según corresponda)
                self.job_service.fail_job(
                    job=job,
                    error_message=error,
                    should_retry=should_retry
                )
                
                logger.warning(
                    f"[{worker_name}] ⚠️ Job falló: "
                    f"{job.contact.dni if job.contact else 'unknown'} - {error}"
                )
        
        except Exception as e:
            logger.exception(f"[{worker_name}] Error procesando job: {e}")
            
            # Fallar el job por error inesperado
            self.job_service.fail_job(
                job=job,
                error_message=f"Error inesperado: {str(e)}",
                should_retry=True  # Permitir retry en errores inesperados
            )
    
    def _should_retry_job(self, job, error: str) -> bool:
        """
        Determina si un job debería reintentarse basado en el error
        
        Args:
            job: Job que falló
            error: Mensaje de error
            
        Returns:
            True si se debe reintentar
        """
        # Errores que no deberían reintentarse
        permanent_failures = [
            "invalid_number",
            "blacklisted",
            "do_not_call",
            "invalid_agent",
            "insufficient_credits"
        ]
        
        error_lower = error.lower()
        for failure_type in permanent_failures:
            if failure_type in error_lower:
                return False
        
        return True
    
    def _calculate_backoff_delay(self, consecutive_empty_polls: int) -> float:
        """
        Calcula delay con backoff exponencial cuando no hay jobs
        
        Args:
            consecutive_empty_polls: Número de polls consecutivos vacíos
            
        Returns:
            Segundos a esperar antes del próximo poll
        """
        # Backoff exponencial: 1s, 2s, 4s, 8s, hasta máximo 30s
        base_delay = min(30.0, 1.0 + (consecutive_empty_polls * 0.5))
        
        # Agregar jitter para evitar sincronización
        jitter = self._random_jitter(0.8, 1.2)
        
        return base_delay * jitter
    
    def _random_jitter(self, min_factor: float = 0.9, max_factor: float = 1.1) -> float:
        """Genera jitter aleatorio para evitar sincronización de workers"""
        return random.uniform(min_factor, max_factor)
    
    def _setup_signal_handlers(self) -> None:
        """Configura handlers para shutdown ordenado"""
        def signal_handler(signum, frame):
            logger.info(f"Señal {signum} recibida, iniciando shutdown...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def get_status(self) -> dict:
        """
        Obtiene estado actual de los workers
        
        Returns:
            Diccionario con información de estado
        """
        alive_workers = sum(1 for w in self.workers if w.is_alive())
        
        return {
            'running': self.running,
            'total_workers': len(self.workers),
            'alive_workers': alive_workers,
            'worker_names': [w.name for w in self.workers if w.is_alive()]
        }