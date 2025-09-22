"""
Utilidades y helpers para la aplicación
"""

import random
import string
from datetime import datetime, timezone
from typing import Dict, Any


def generate_random_id(length: int = 8) -> str:
    """Genera un ID aleatorio para testing"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


def utcnow() -> datetime:
    """Obtiene datetime UTC actual"""
    return datetime.now(timezone.utc)


def format_duration_ms(duration_ms: int) -> str:
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


def safe_get_nested(data: Dict[str, Any], path: str, default=None) -> Any:
    """
    Obtiene valor anidado de un diccionario usando dot notation
    
    Example:
        safe_get_nested({'a': {'b': {'c': 1}}}, 'a.b.c') -> 1
    """
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current