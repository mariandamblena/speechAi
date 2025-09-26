"""
Enumeraciones para los diferentes casos de uso
"""

from enum import Enum


class UseCaseType(Enum):
    """Tipos de casos de uso soportados"""
    DEBT_COLLECTION = "debt_collection"
    USER_EXPERIENCE = "user_experience"
    SURVEY = "survey"
    REMINDER = "reminder"
    NOTIFICATION = "notification"


class ProcessingStrategy(Enum):
    """Estrategias de procesamiento disponibles"""
    SEQUENTIAL = "sequential"
    BATCH = "batch"
    PRIORITY = "priority"
    SCHEDULED = "scheduled"


class DataSourceType(Enum):
    """Tipos de fuente de datos soportados"""
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    API = "api"
    MANUAL = "manual"