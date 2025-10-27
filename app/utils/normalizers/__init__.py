"""
Módulo centralizado de normalizadores
"""

from .phone_normalizer import normalize_phone_cl, normalize_phone_ar, split_phone_candidates
from .date_normalizer import normalize_date, add_days_iso
from .text_normalizer import normalize_rut, format_rut, normalize_key
from .numeric_normalizer import to_number_pesos, to_int, to_float

__all__ = [
    # Phone normalizers
    'normalize_phone_cl',
    'normalize_phone_ar',
    'split_phone_candidates',
    # Date normalizers
    'normalize_date',
    'add_days_iso',
    # Text normalizers
    'normalize_rut',
    'format_rut',
    'normalize_key',
    # Numeric normalizers
    'to_number_pesos',
    'to_int',
    'to_float',
]
