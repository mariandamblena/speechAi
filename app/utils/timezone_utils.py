"""
Utilidades para manejo estandarizado de zonas horarias en SpeechAI Backend
"""
from datetime import datetime, timezone
import pytz

# Timezone de Chile (para mostrar fechas al usuario final)
CHILE_TZ = pytz.timezone('America/Santiago')

def utc_now() -> datetime:
    """
    Retorna el timestamp actual en UTC.
    USAR ESTA FUNCIÓN en lugar de datetime.now() o datetime.utcnow()
    """
    return datetime.now(timezone.utc)

def to_chile_time(utc_dt: datetime) -> datetime:
    """
    Convierte un datetime UTC a hora de Chile
    Uso: Para mostrar fechas al usuario final
    """
    if utc_dt.tzinfo is None:
        # Asumir UTC si no tiene timezone info
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    return utc_dt.astimezone(CHILE_TZ)

def chile_time_display(utc_dt: datetime = None) -> str:
    """
    Retorna una fecha formateada en hora de Chile para mostrar al usuario
    Si no se proporciona fecha, usa el momento actual
    """
    if utc_dt is None:
        utc_dt = utc_now()
    
    chile_dt = to_chile_time(utc_dt)
    return chile_dt.strftime("%A, %B %d, %Y at %I:%M:%S %p CLT")

def batch_id_timestamp() -> str:
    """
    Genera un timestamp estandarizado para batch IDs
    Siempre en UTC para consistencia
    """
    return utc_now().strftime("%Y%m%d-%H%M%S")

def job_id_timestamp() -> str:
    """
    Genera un timestamp estandarizado para job IDs
    Siempre en UTC para consistencia
    """
    return utc_now().strftime("%Y%m%d_%H%M%S")

def display_batch_name() -> str:
    """
    Genera un nombre de batch con timestamp para mostrar al usuario
    Usa UTC internamente pero puede mostrarse en hora local si es necesario
    """
    return utc_now().strftime("%Y-%m-%d %H:%M")

def format_date_for_retell(iso_date: str, include_time: bool = False) -> str:
    """
    Convierte fecha ISO a formato legible en español chileno para Retell AI
    
    Args:
        iso_date: Fecha en formato ISO (2025-09-28 o 2025-09-28T15:30:00Z)
        include_time: Si incluir hora en formato legible
    
    Returns:
        Fecha legible como "28 de septiembre de 2025" o con hora "28 de septiembre de 2025 a las 3:30 PM"
    """
    if not iso_date:
        return ""
    
    try:
        # Parsear fecha ISO
        if isinstance(iso_date, str):
            if 'T' in iso_date:
                # Es datetime completo
                if iso_date.endswith('Z'):
                    # UTC timestamp
                    dt = datetime.fromisoformat(iso_date.replace('Z', '+00:00'))
                    # Convertir a hora chilena si include_time es True
                    if include_time:
                        dt = to_chile_time(dt)
                else:
                    dt = datetime.fromisoformat(iso_date)
            else:
                # Solo fecha
                dt = datetime.fromisoformat(iso_date)
        else:
            dt = iso_date
        
        # Mapeo de meses en español
        meses = [
            '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ]
        
        dia = dt.day
        mes = meses[dt.month]
        año = dt.year
        
        fecha_texto = f"{dia} de {mes} de {año}"
        
        if include_time:
            hora = dt.strftime("%I:%M %p").replace("AM", "AM").replace("PM", "PM")
            fecha_texto += f" a las {hora}"
        
        return fecha_texto
    except (ValueError, IndexError, AttributeError):
        return str(iso_date)  # Fallback: retornar fecha original

# Ejemplos de uso:
# created_at=timezone_utils.utc_now()  # En lugar de datetime.now() o datetime.utcnow()
# batch_id = f"batch-{timezone_utils.batch_id_timestamp()}"
# display_time = timezone_utils.chile_time_display(job.created_at)
# fecha_retell = timezone_utils.format_date_for_retell("2025-09-28")  # "28 de septiembre de 2025"