"""
Servicio de orquestación de llamadas
Implementa el patrón n8n de polling para seguimiento de llamadas
"""

import logging
import time
from typing import Optional, Dict, Any

from config.settings import CallConfig, RetellConfig
from domain.models import JobModel
from domain.enums import CallStatus
from infrastructure.retell_client import IRetellClient, RetellCallResult

logger = logging.getLogger(__name__)


class CallOrchestrationService:
    """
    Servicio para orquestación completa de llamadas
    
    Responsabilidades:
    - Crear llamadas en Retell
    - Polling de estado hasta completar
    - Mapeo de contexto de job a variables Retell
    
    Implementa el patrón como en n8n:
    1. Crear llamada -> obtener call_id
    2. Polling con GET hasta estado final
    3. Retornar resultado completo
    
    Sigue principios SOLID:
    - Single Responsibility: Solo orquesta llamadas
    - Dependency Inversion: Usa interfaces para Retell client
    """
    
    def __init__(
        self,
        retell_client: IRetellClient,
        call_config: CallConfig,
        retell_config: RetellConfig
    ):
        self.retell_client = retell_client
        self.call_config = call_config
        self.retell_config = retell_config
    
    def execute_call_workflow(self, job: JobModel) -> Dict[str, Any]:
        """
        Ejecuta el workflow completo de llamada (patrón n8n)
        
        Args:
            job: Job con información para la llamada
            
        Returns:
            Diccionario con resultado completo de la llamada
            Incluye 'success': bool y 'data' o 'error'
        """
        if not self._validate_job(job):
            return {
                'success': False,
                'error': 'Job inválido: falta información requerida',
                'call_id': None
            }
        
        # 1. Crear llamada
        logger.info(
            f"📞 Iniciando llamada para {job.contact.dni} "
            f"-> {job.contact.current_phone}"
        )
        
        create_result = self._create_call(job)
        if not create_result.success:
            return {
                'success': False,
                'error': create_result.error,
                'call_id': None
            }
        
        call_id = create_result.call_id
        logger.info(f"📱 Llamada creada: {call_id}")
        
        # 2. Polling hasta completar (como en n8n)
        final_result = self._poll_until_completion(call_id)
        
        if final_result:
            logger.info(
                f"✅ Llamada {call_id} completada: "
                f"{final_result.get('call_status', 'unknown')}"
            )
            return {
                'success': True,
                'data': final_result,
                'call_id': call_id
            }
        else:
            logger.warning(f"⏰ Timeout polling llamada {call_id}")
            return {
                'success': False,
                'error': 'Timeout esperando resultado de llamada',
                'call_id': call_id,
                'data': None
            }
    
    def _validate_job(self, job: JobModel) -> bool:
        """Valida que el job tenga la información necesaria"""
        if not job.contact:
            logger.error("Job sin información de contacto")
            return False
        
        if not job.contact.current_phone:
            logger.error(f"No hay teléfono disponible para {job.contact.dni}")
            return False
        
        if not job.payload:
            logger.error(f"Job sin payload para {job.contact.dni}")
            return False
        
        return True
    
    def _create_call(self, job: JobModel) -> RetellCallResult:
        """
        Crea la llamada usando Retell API
        
        Args:
            job: Job con información para la llamada
            
        Returns:
            RetellCallResult con resultado de la creación
        """
        context = job.get_context_for_retell()
        
        return self.retell_client.create_call(
            to_number=job.contact.current_phone,
            agent_id=self.retell_config.agent_id,
            from_number=self.retell_config.from_number,
            context=context
        )
    
    def _poll_until_completion(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Polling del estado de llamada hasta completar (patrón n8n)
        
        Args:
            call_id: ID de la llamada a seguir
            
        Returns:
            Datos finales de la llamada o None si timeout
        """
        start_time = time.time()
        poll_count = 0
        
        while (time.time() - start_time) < self.call_config.timeout_seconds:
            poll_count += 1
            
            try:
                status_data = self.retell_client.get_call_status(call_id)
                
                # Verificar si hay error en la consulta
                if "error" in status_data:
                    logger.error(
                        f"Error consultando status {call_id} (poll #{poll_count}): "
                        f"{status_data['error']}"
                    )
                    time.sleep(self.call_config.polling_interval_seconds)
                    continue
                
                call_status = status_data.get("call_status", "")
                
                logger.debug(
                    f"📊 Call {call_id} status: {call_status} "
                    f"(poll #{poll_count})"
                )
                
                # Verificar si es estado final
                if CallStatus.is_final_status(call_status):
                    logger.info(
                        f"🏁 Call {call_id} finalizó: {call_status} "
                        f"(después de {poll_count} polls)"
                    )
                    return status_data
                
                # Continuar polling
                time.sleep(self.call_config.polling_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error en polling #{poll_count} para {call_id}: {e}")
                time.sleep(self.call_config.polling_interval_seconds)
        
        logger.warning(
            f"⏰ Timeout polling {call_id} después de {poll_count} intentos "
            f"({self.call_config.timeout_seconds}s)"
        )
        return None
    
    def get_call_summary(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae información resumida de los datos de llamada
        
        Args:
            call_data: Datos completos de Retell
            
        Returns:
            Diccionario con información resumida
        """
        return {
            'call_status': call_data.get('call_status', 'unknown'),
            'duration_ms': call_data.get('duration_ms', 0),
            'duration_readable': self._format_duration(call_data.get('duration_ms', 0)),
            'end_reason': call_data.get('end_reason', ''),
            'transcript_available': bool(call_data.get('transcript')),
            'recording_available': bool(call_data.get('recording_url')),
            'successful': call_data.get('call_status') == CallStatus.ENDED.value,
        }
    
    def _format_duration(self, duration_ms: int) -> str:
        """Formatea duración en milisegundos a texto legible"""
        if duration_ms <= 0:
            return "0s"
        
        total_seconds = duration_ms // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        if minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"