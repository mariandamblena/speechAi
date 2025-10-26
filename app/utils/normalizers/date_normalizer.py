"""
Normalizador de fechas
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


def normalize_date(value: Any) -> Optional[str]:
    """
    Convierte fecha a formato ISO (YYYY-MM-DD)
    Soporta formatos chilenos y argentinos (DD/MM/YYYY), Excel serials, ISO
    
    Args:
        value: Valor a convertir (string, int, float, datetime)
    
    Returns:
        Fecha en formato ISO (YYYY-MM-DD) o None si no se puede parsear
    
    Examples:
        >>> normalize_date('25/12/2024')
        '2024-12-25'
        >>> normalize_date(44927)  # Excel serial
        '2022-12-25'
        >>> normalize_date('2024-12-25')
        '2024-12-25'
    """
    if value is None or value == '':
        return None
    
    # 1. Si es número (Excel serial)
    if isinstance(value, (int, float)):
        try:
            base_date = datetime(1899, 12, 30, tzinfo=timezone.utc)
            target_date = base_date + timedelta(days=int(value))
            return target_date.date().isoformat()
        except (ValueError, OverflowError):
            return None
    
    value_str = str(value).strip()
    
    # 2. Formato latinoamericano: DD/MM/YYYY o DD-MM-YYYY
    latam_pattern = r'^(\d{1,2})[\\/\-](\d{1,2})[\\/\-](\d{2,4})$'
    match = re.match(latam_pattern, value_str)
    if match:
        day, month, year = match.groups()
        
        # Expandir año de 2 dígitos
        if len(year) == 2:
            year = '20' + year
        
        try:
            year_int, month_int, day_int = int(year), int(month), int(day)
            if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                date_obj = datetime(year_int, month_int, day_int, tzinfo=timezone.utc)
                return date_obj.date().isoformat()
        except ValueError:
            pass
    
    # 3. Formato ISO u otros formatos estándar
    try:
        parsed_date = datetime.fromisoformat(value_str.replace('Z', '+00:00'))
        return parsed_date.date().isoformat()
    except ValueError:
        pass
    
    # 4. Intento genérico YYYY-MM-DD
    try:
        parsed_date = datetime.strptime(value_str, '%Y-%m-%d')
        return parsed_date.date().isoformat()
    except ValueError:
        pass
    
    return None
