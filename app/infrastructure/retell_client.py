"""
Cliente para la API de Retell AI
Implementa el patrón Repository e Interface Segregation
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional

import requests
from tenacity import retry, wait_exponential_jitter, stop_after_attempt

from config.settings import RetellConfig

logger = logging.getLogger(__name__)


@dataclass
class RetellCallResult:
    """Resultado de operación con Retell API"""
    success: bool
    call_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class IRetellClient(ABC):
    """Interface para clientes de Retell AI (Dependency Inversion Principle)"""
    
    @abstractmethod
    def create_call(
        self,
        to_number: str,
        agent_id: str,
        from_number: Optional[str],
        context: Dict[str, str]
    ) -> RetellCallResult:
        """Crea una nueva llamada"""
        pass
    
    @abstractmethod
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Obtiene el estado actual de una llamada"""
        pass


class RetellApiClient(IRetellClient):
    """
    Implementación concreta del cliente Retell API
    Sigue principios SOLID:
    - Single Responsibility: Solo maneja comunicación con Retell API
    - Open/Closed: Extensible mediante herencia
    - Interface Segregation: Implementa solo métodos necesarios
    """
    
    def __init__(self, config: RetellConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        
        if not config.api_key:
            raise ValueError("Retell API key es requerida")
    
    def _get_headers(self) -> Dict[str, str]:
        """Headers comunes para requests"""
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
    
    @retry(
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(3)
    )
    def create_call(
        self,
        to_number: str,
        agent_id: str,
        from_number: Optional[str],
        context: Dict[str, str]
    ) -> RetellCallResult:
        """
        Crea una llamada usando Retell v2 API
        
        Args:
            to_number: Número de destino
            agent_id: ID del agente de Retell
            from_number: Número desde el cual llamar (opcional)
            context: Variables dinámicas para el LLM
            
        Returns:
            RetellCallResult con el resultado de la operación
        """
        url = f"{self.base_url}/v2/create-phone-call"
        
        payload = {
            "to_number": str(to_number),
            "agent_id": str(agent_id),
            "retell_llm_dynamic_variables": context,
        }
        
        if from_number:
            payload["from_number"] = str(from_number)
        
        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                data=json.dumps(payload),
                timeout=self.config.timeout_seconds
            )
            
            if 200 <= response.status_code < 300:
                data = response.json()
                call_id = self._extract_call_id(data)
                
                if not call_id:
                    logger.error(f"No se encontró call_id en respuesta: {data}")
                    return RetellCallResult(
                        success=False,
                        error=f"Sin call_id en respuesta: {data}",
                        data=data
                    )
                
                logger.info(f"✅ Llamada creada exitosamente: {call_id}")
                return RetellCallResult(
                    success=True,
                    call_id=call_id,
                    data=data
                )
            
            else:
                error_data = self._parse_error_response(response)
                logger.error(f"Error creando llamada: {error_data}")
                return RetellCallResult(
                    success=False,
                    error=str(error_data)
                )
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión con Retell: {e}")
            return RetellCallResult(
                success=False,
                error=f"Error de conexión: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            return RetellCallResult(
                success=False,
                error=f"Error inesperado: {str(e)}"
            )
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado actual de una llamada
        
        Args:
            call_id: ID de la llamada
            
        Returns:
            Diccionario con datos de la llamada o error
        """
        url = f"{self.base_url}/v2/get-call/{call_id}"
        
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.config.timeout_seconds
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = self._parse_error_response(response)
                return {
                    "error": str(error_data),
                    "status_code": response.status_code
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error consultando status de {call_id}: {e}")
            return {
                "error": f"Error de conexión: {str(e)}",
                "call_id": call_id
            }
        except Exception as e:
            logger.error(f"Error inesperado consultando {call_id}: {e}")
            return {
                "error": f"Error inesperado: {str(e)}",
                "call_id": call_id
            }
    
    def _extract_call_id(self, response_data: Dict[str, Any]) -> Optional[str]:
        """Extrae call_id de diferentes formatos de respuesta"""
        # Intentar diferentes ubicaciones donde puede estar el call_id
        possible_locations = [
            response_data.get("call_id"),
            response_data.get("data", {}).get("call_id") if isinstance(response_data.get("data"), dict) else None,
            response_data.get("id"),
        ]
        
        for call_id in possible_locations:
            if call_id:
                return str(call_id)
        
        return None
    
    def _parse_error_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parsea respuesta de error de la API"""
        try:
            return response.json()
        except Exception:
            return {
                "error": "Error de API",
                "status_code": response.status_code,
                "text": response.text
            }


class MockRetellClient(IRetellClient):
    """
    Cliente mock para testing
    Implementa la misma interfaz pero simula respuestas
    """
    
    def __init__(self):
        self.call_counter = 0
    
    def create_call(
        self,
        to_number: str,
        agent_id: str,
        from_number: Optional[str],
        context: Dict[str, str]
    ) -> RetellCallResult:
        """Simula creación de llamada"""
        self.call_counter += 1
        fake_call_id = f"mock_call_{self.call_counter}"
        
        return RetellCallResult(
            success=True,
            call_id=fake_call_id,
            data={"call_id": fake_call_id, "status": "registered"}
        )
    
    def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Simula consulta de estado"""
        return {
            "call_id": call_id,
            "call_status": "ended",
            "duration_ms": 30000,
            "transcript": "Mock transcript"
        }