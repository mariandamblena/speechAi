"""
Normalizadores de texto (RUT, claves, etc)
"""

import re
import unicodedata
from typing import Any, Optional


def normalize_rut(rut_raw: Any) -> Optional[str]:
    """
    Normaliza RUT chileno removiendo puntos y guiones
    
    Args:
        rut_raw: RUT crudo
    
    Returns:
        RUT normalizado (sin puntos ni guiones, mayúsculas) o None
    
    Examples:
        >>> normalize_rut('12.345.678-9')
        '123456789'
        >>> normalize_rut('12345678-K')
        '12345678K'
    """
    if rut_raw is None or rut_raw == '':
        return None
    
    # Quitar puntos y guion, mantener mayúsculas
    rut_clean = str(rut_raw).replace('.', '').replace('-', '').strip().upper()
    return rut_clean if rut_clean else None


def normalize_key(key: str) -> str:
    """
    Normaliza claves de columnas para búsqueda flexible
    - Lowercase
    - Sin acentos
    - Sin espacios/guiones/underscores
    
    Args:
        key: Clave a normalizar
    
    Returns:
        Clave normalizada
    
    Examples:
        >>> normalize_key('Nombre Completo')
        'nombrecompleto'
        >>> normalize_key('Teléfono_Móvil')
        'telefonomovil'
        >>> normalize_key('DIRECCIÓN')
        'direccion'
    """
    # Lowercase
    key_lower = key.lower()
    
    # Remover acentos
    key_no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', key_lower)
        if unicodedata.category(c) != 'Mn'
    )
    
    # Remover espacios, guiones, underscores
    key_clean = re.sub(r'[\s\-_]+', '', key_no_accents)
    
    return key_clean
