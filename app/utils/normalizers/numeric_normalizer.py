"""
Conversores numéricos para procesamiento de datos
"""

import re
from typing import Any


def to_number_pesos(value: Any) -> float:
    """
    Convierte valor a pesos chilenos/argentinos (no centavos)
    
    Args:
        value: Valor a convertir (int, float, string con formato)
    
    Returns:
        Valor en pesos como float
    
    Examples:
        >>> to_number_pesos('$1.234,56')
        1234.56
        >>> to_number_pesos('1234.56')
        1234.56
        >>> to_number_pesos(1234)
        1234.0
    """
    if value is None or value == '':
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Limpiar string: remover $, espacios, puntos (miles), cambiar coma por punto (decimales)
    value_str = str(value).strip()
    value_str = re.sub(r'[\s$]', '', value_str)  # Remover espacios y $
    value_str = value_str.replace('.', '').replace(',', '.')  # Miles y decimales
    
    try:
        return float(value_str)
    except ValueError:
        return 0.0


def to_int(value: Any, default: int = 0) -> int:
    """
    Convierte valor a entero, limpiando caracteres no numéricos
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si falla la conversión
    
    Returns:
        Entero convertido o default
    
    Examples:
        >>> to_int('123')
        123
        >>> to_int('1,234')
        1234
        >>> to_int('invalid', default=0)
        0
    """
    if value is None or value == '':
        return default
    
    try:
        # Limpiar y convertir
        clean_str = re.sub(r'[^\d\-]', '', str(value))
        return int(clean_str) if clean_str else default
    except ValueError:
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    """
    Convierte valor a float, manejando diferentes formatos
    
    Args:
        value: Valor a convertir
        default: Valor por defecto si falla la conversión
    
    Returns:
        Float convertido o default
    
    Examples:
        >>> to_float('123.45')
        123.45
        >>> to_float('123,45')
        123.45
        >>> to_float('invalid', default=0.0)
        0.0
    """
    if value is None or value == '':
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        # Intentar conversión directa primero
        return float(value)
    except (ValueError, TypeError):
        # Intentar limpiar string
        try:
            clean_str = str(value).strip().replace(',', '.')
            return float(clean_str)
        except (ValueError, TypeError):
            return default
