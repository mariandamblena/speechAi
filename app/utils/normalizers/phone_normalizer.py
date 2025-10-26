"""
Normalizadores de teléfonos para Chile y Argentina
"""

import re
from typing import Any, Optional, List


def split_phone_candidates(raw_phone: str) -> List[str]:
    """
    Genera candidatos de número telefónico separando por delimitadores
    
    Args:
        raw_phone: Teléfono crudo
        
    Returns:
        Lista de candidatos posibles
    """
    if not raw_phone:
        return []
    
    phone_str = str(raw_phone).strip()
    
    # Separar por caracteres no dígitos
    parts = re.split(r'\D+', phone_str)
    parts = [p for p in parts if p]  # Filtrar vacíos
    
    # Todos los dígitos juntos
    all_digits = re.sub(r'\D+', '', phone_str)
    
    candidates = set()
    if all_digits:
        candidates.add(all_digits)
    
    for part in parts:
        candidates.add(part)
    
    # Si hay al menos 2 partes y la primera es corta (código área), unir primeras dos
    if len(parts) >= 2 and len(parts[0]) <= 3:
        candidates.add(parts[0] + parts[1])
    
    return list(candidates)


def normalize_phone_cl(raw_phone: Any, kind: str = 'any', default_area_code: str = '2') -> Optional[str]:
    """
    Normaliza teléfonos chilenos a formato E.164 (+56XXXXXXXXX)
    
    Args:
        raw_phone: Número crudo
        kind: 'mobile', 'landline', 'any'
        default_area_code: Código de área por defecto para fijos (default: '2' Santiago)
    
    Returns:
        Número normalizado en formato +56XXXXXXXXX o None
    
    Examples:
        >>> normalize_phone_cl('992125907', 'mobile')
        '+56992125907'
        >>> normalize_phone_cl('228151807', 'landline')
        '+56228151807'
        >>> normalize_phone_cl('09-2125907', 'any')
        '+56992125907'
    """
    if raw_phone is None or raw_phone == '':
        return None
    
    want_mobile = kind == 'mobile'
    want_landline = kind == 'landline'
    want_any = kind == 'any'
    
    candidates = split_phone_candidates(str(raw_phone))
    
    for number in candidates:
        # 1. Remover código país y trunk
        if number.startswith('56'):
            number = number[2:]
        
        # Remover ceros iniciales (trunk)
        number = re.sub(r'^0+', '', number)
        
        # 2. Heurísticas para casos frecuentes
        
        # Móviles que llegan como "5699xxxxxxxx" -> "99xxxxxxxx" (10 dígitos)
        if len(number) == 10 and number.startswith('99'):
            number = number[1:]  # -> "9xxxxxxxx" (9 dígitos)
        
        # Móvil legado: 8 dígitos empezando con 9 -> anteponer 9
        # Ej: "09-2125907" -> "92125907" -> "992125907"
        if len(number) == 8 and number[0] == '9':
            number = '9' + number
        
        # Fijo Santiago legado: "2" + 7 dígitos -> anteponer otro '2'
        # Ej: "02-8151807" -> "28151807" -> "228151807"
        if len(number) == 8 and number[0] == '2' and not number.startswith('22'):
            number = '2' + number
        
        # 3. Normalización por tipo
        if want_mobile and len(number) == 8 and number[0] != '9':
            number = '9' + number
        
        if (want_landline or want_any) and len(number) in [7, 8] and number[0] != '9':
            number = default_area_code + number
        
        # 4. Validación final
        if len(number) != 9:
            continue
        
        is_mobile = number.startswith('9')
        
        if want_mobile and not is_mobile:
            continue
        if want_landline and is_mobile:
            continue
        
        return f'+56{number}'
    
    return None


def normalize_phone_ar(raw_phone: Any, kind: str = 'any') -> Optional[str]:
    """
    Normaliza teléfonos argentinos a formato E.164 (+54XXXXXXXXXX)
    También puede convertir números chilenos para testing
    
    Args:
        raw_phone: Número crudo
        kind: 'mobile', 'landline', 'any'
    
    Returns:
        Número normalizado en formato +54XXXXXXXXXX o None
    
    Examples:
        >>> normalize_phone_ar('91123456789', 'mobile')
        '+5491123456789'
        >>> normalize_phone_ar('1123456789', 'landline')
        '+541123456789'
    """
    if raw_phone is None or raw_phone == '':
        return None
    
    phone_str = str(raw_phone).strip()
    
    # Si ya tiene +54, devolverlo
    if phone_str.startswith('+54'):
        return phone_str
    
    # Si tiene +56 (Chile), convertir a +54 para testing
    if phone_str.startswith('+56'):
        # Extraer el número sin código de país
        clean = phone_str[3:]
        # Para números móviles chilenos 9XXXXXXXX, convertir a argentinos
        if clean.startswith('9') and len(clean) == 9:
            # Convertir +56 9XXXX XXXX a +54 9 11 XXXX XXXX (formato móvil argentino)
            return f"+5491{clean[1:]}"
        # Para números fijos chilenos, convertir a móvil argentino
        elif len(clean) == 8:
            return f"+54911{clean}"
    
    # Limpiar y extraer solo dígitos
    clean = re.sub(r'[^\d]', '', phone_str)
    
    # Remover código país si está presente
    if clean.startswith('54'):
        clean = clean[2:]
    elif clean.startswith('56'):
        # Convertir de chile a argentina para testing
        clean = clean[2:]
        if clean.startswith('9') and len(clean) == 9:
            return f"+5491{clean[1:]}"
        elif len(clean) == 8:
            return f"+54911{clean}"
    
    # Remover ceros iniciales (trunk)
    clean = clean.lstrip('0')
    
    # Validaciones específicas para Argentina
    if len(clean) == 10:
        # Formato: 11XXXXXXXX (Buenos Aires) o 9XXXXXXXXX (móvil)
        if clean.startswith('11') or clean.startswith('9'):
            return f"+54{clean}"
    elif len(clean) == 8:
        # Teléfono fijo sin código de área, agregar 11 (Buenos Aires)
        if not clean.startswith('9'):
            return f"+5411{clean}"
    elif len(clean) == 9:
        # Móvil sin código país
        if clean.startswith('9'):
            return f"+549{clean}"
    
    # Si llegamos aquí, intentar formatear como móvil argentino genérico
    if len(clean) >= 8:
        # Asumir móvil Buenos Aires
        return f"+54911{clean[-8:]}"
    
    return None
