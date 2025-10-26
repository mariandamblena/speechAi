"""
Tests para utils.normalizers
Verificar normalización de teléfonos, fechas, RUTs y textos
"""

import unittest
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.normalizers import (
    normalize_phone_cl,
    normalize_phone_ar,
    normalize_date,
    normalize_rut,
    normalize_key,
    split_phone_candidates
)


class TestPhoneNormalizerChile(unittest.TestCase):
    """Tests para normalización de teléfonos chilenos"""
    
    def test_mobile_nine_digits(self):
        """Móvil con 9 dígitos comenzando con 9"""
        assert normalize_phone_cl('992125907', 'mobile') == '+56992125907'
        assert normalize_phone_cl('912345678', 'mobile') == '+56912345678'
    
    def test_mobile_with_trunk_prefix(self):
        """Móvil con prefijo trunk (0)"""
        assert normalize_phone_cl('09-92125907', 'mobile') == '+56992125907'
        assert normalize_phone_cl('092125907', 'mobile') == '+56992125907'
    
    def test_mobile_legacy_8_digits(self):
        """Móvil legado: 8 dígitos empezando con 9 -> agregar 9"""
        assert normalize_phone_cl('92125907', 'mobile') == '+56992125907'
        assert normalize_phone_cl('91234567', 'mobile') == '+56991234567'
    
    def test_landline_santiago(self):
        """Teléfono fijo Santiago (22)"""
        assert normalize_phone_cl('228151807', 'landline') == '+56228151807'
        assert normalize_phone_cl('221234567', 'landline') == '+56221234567'
    
    def test_landline_santiago_legacy(self):
        """Fijo Santiago legado: 2 + 7 dígitos -> agregar otro 2"""
        assert normalize_phone_cl('28151807', 'landline') == '+56228151807'
        assert normalize_phone_cl('2815180', 'landline') == '+56228151807'
    
    def test_landline_with_area_code(self):
        """Fijo con código de área"""
        assert normalize_phone_cl('322345678', 'landline') == '+56322345678'  # Valparaíso
        assert normalize_phone_cl('412345678', 'landline') == '+56412345678'  # Concepción
    
    def test_phone_with_country_code(self):
        """Teléfono que ya incluye +56"""
        assert normalize_phone_cl('56992125907', 'any') == '+56992125907'
        assert normalize_phone_cl('+56992125907', 'any') == '+56992125907'
    
    def test_phone_with_special_chars(self):
        """Teléfono con caracteres especiales"""
        assert normalize_phone_cl('(9) 9212-5907', 'mobile') == '+56992125907'
        assert normalize_phone_cl('9-9212-5907', 'mobile') == '+56992125907'
        assert normalize_phone_cl('+56 9 9212 5907', 'mobile') == '+56992125907'
    
    def test_invalid_phone(self):
        """Teléfonos inválidos"""
        assert normalize_phone_cl('', 'any') is None
        assert normalize_phone_cl(None, 'any') is None
        assert normalize_phone_cl('123', 'any') is None  # Muy corto
        assert normalize_phone_cl('abc', 'any') is None  # No numérico
    
    def test_any_kind_accepts_both(self):
        """kind='any' acepta móvil o fijo"""
        assert normalize_phone_cl('992125907', 'any') == '+56992125907'  # móvil
        assert normalize_phone_cl('228151807', 'any') == '+56228151807'  # fijo


class TestPhoneNormalizerArgentina(unittest.TestCase):
    """Tests para normalización de teléfonos argentinos"""
    
    def test_mobile_buenos_aires(self):
        """Móvil Buenos Aires: 9 11 XXXX XXXX"""
        assert normalize_phone_ar('91123456789', 'mobile') == '+5491123456789'
        assert normalize_phone_ar('911 2345 6789', 'mobile') == '+5491123456789'
    
    def test_landline_buenos_aires(self):
        """Fijo Buenos Aires: 11 XXXX XXXX"""
        assert normalize_phone_ar('1123456789', 'landline') == '+541123456789'
    
    def test_mobile_with_country_code(self):
        """Móvil que ya incluye +54"""
        assert normalize_phone_ar('+5491123456789', 'any') == '+5491123456789'
        assert normalize_phone_ar('5491123456789', 'any') == '+5491123456789'
    
    def test_landline_without_area_code(self):
        """Fijo sin código de área -> asume Buenos Aires (11)"""
        assert normalize_phone_ar('23456789', 'landline') == '+541123456789'
    
    def test_phone_with_trunk_prefix(self):
        """Teléfono con prefijo trunk (0)"""
        assert normalize_phone_ar('091123456789', 'any') == '+5491123456789'
        assert normalize_phone_ar('01123456789', 'any') == '+541123456789'
    
    def test_chile_to_argentina_conversion(self):
        """Conversión de números chilenos a argentinos (para testing)"""
        # +56 9XXXXXXXX -> +54 91 XXXXXXXX
        assert normalize_phone_ar('+56992125907', 'any') == '+54992125907'
        assert normalize_phone_ar('+56912345678', 'any') == '+54912345678'
    
    def test_invalid_phone(self):
        """Teléfonos inválidos"""
        assert normalize_phone_ar('', 'any') is None
        assert normalize_phone_ar(None, 'any') is None
        assert normalize_phone_ar('123', 'any') is None  # Muy corto


class TestDateNormalizer(unittest.TestCase):
    """Tests para normalización de fechas"""
    
    def test_date_dd_mm_yyyy_slash(self):
        """Formato DD/MM/YYYY"""
        assert normalize_date('25/12/2024') == '2024-12-25'
        assert normalize_date('01/01/2025') == '2025-01-01'
        assert normalize_date('15/06/2023') == '2023-06-15'
    
    def test_date_dd_mm_yyyy_dash(self):
        """Formato DD-MM-YYYY"""
        assert normalize_date('25-12-2024') == '2024-12-25'
        assert normalize_date('01-01-2025') == '2025-01-01'
    
    def test_date_dd_mm_yy(self):
        """Formato DD/MM/YY (año corto)"""
        assert normalize_date('25/12/24') == '2024-12-25'
        assert normalize_date('01/01/25') == '2025-01-01'
    
    def test_date_single_digits(self):
        """Fechas con dígitos simples"""
        assert normalize_date('5/3/2024') == '2024-03-05'
        assert normalize_date('1/1/24') == '2024-01-01'
    
    def test_date_iso_format(self):
        """Formato ISO YYYY-MM-DD"""
        assert normalize_date('2024-12-25') == '2024-12-25'
        assert normalize_date('2025-01-01') == '2025-01-01'
    
    def test_date_excel_serial(self):
        """Excel serial number"""
        # 44927 = 2022-12-25
        assert normalize_date(44927) == '2022-12-25'
        assert normalize_date(45000) == '2023-03-08'
    
    def test_date_with_timezone(self):
        """Fecha con timezone"""
        assert normalize_date('2024-12-25T00:00:00Z') == '2024-12-25'
        assert normalize_date('2024-12-25T15:30:00+00:00') == '2024-12-25'
    
    def test_invalid_date(self):
        """Fechas inválidas"""
        assert normalize_date('') is None
        assert normalize_date(None) is None
        assert normalize_date('invalid') is None
        assert normalize_date('99/99/9999') is None  # Fecha imposible


class TestTextNormalizer(unittest.TestCase):
    """Tests para normalización de textos"""
    
    def test_normalize_rut_with_dots_and_dash(self):
        """RUT con puntos y guión"""
        assert normalize_rut('12.345.678-9') == '123456789'
        assert normalize_rut('1.234.567-K') == '1234567K'
    
    def test_normalize_rut_without_format(self):
        """RUT sin formato"""
        assert normalize_rut('123456789') == '123456789'
        assert normalize_rut('1234567K') == '1234567K'
    
    def test_normalize_rut_with_dash_only(self):
        """RUT solo con guión"""
        assert normalize_rut('12345678-9') == '123456789'
        assert normalize_rut('1234567-K') == '1234567K'
    
    def test_normalize_rut_lowercase_k(self):
        """RUT con K minúscula -> mayúscula"""
        assert normalize_rut('12345678-k') == '12345678K'
        assert normalize_rut('1234567k') == '1234567K'
    
    def test_normalize_rut_invalid(self):
        """RUTs inválidos"""
        assert normalize_rut('') is None
        assert normalize_rut(None) is None
        assert normalize_rut('   ') is None
    
    def test_normalize_key_lowercase(self):
        """Normalización de claves: lowercase"""
        assert normalize_key('NOMBRE') == 'nombre'
        assert normalize_key('Teléfono') == 'telefono'
    
    def test_normalize_key_remove_accents(self):
        """Normalización de claves: remover acentos"""
        assert normalize_key('Teléfono Móvil') == 'telefonomovil'
        assert normalize_key('Dirección') == 'direccion'
        assert normalize_key('Número') == 'numero'
    
    def test_normalize_key_remove_spaces(self):
        """Normalización de claves: remover espacios"""
        assert normalize_key('Nombre Completo') == 'nombrecompleto'
        assert normalize_key('Fecha de Vencimiento') == 'fechadevencimiento'
    
    def test_normalize_key_remove_special_chars(self):
        """Normalización de claves: remover caracteres especiales"""
        assert normalize_key('Teléfono_Móvil') == 'telefonomovil'
        assert normalize_key('Nombre-Completo') == 'nombrecompleto'
        assert normalize_key('RUT/DNI') == 'rutdni'


class TestSplitPhoneCandidates(unittest.TestCase):
    """Tests para split_phone_candidates"""
    
    def test_split_with_dashes(self):
        """Separar teléfono con guiones"""
        candidates = split_phone_candidates('9-9212-5907')
        assert '992125907' in candidates
        assert '9' in candidates
        assert '9212' in candidates
        assert '5907' in candidates
    
    def test_split_with_spaces(self):
        """Separar teléfono con espacios"""
        candidates = split_phone_candidates('+56 9 9212 5907')
        assert '56992125907' in candidates
    
    def test_split_with_parentheses(self):
        """Separar teléfono con paréntesis"""
        candidates = split_phone_candidates('(9) 9212-5907')
        assert '992125907' in candidates
    
    def test_all_digits_together(self):
        """Todos los dígitos juntos"""
        candidates = split_phone_candidates('9-9212-5907')
        assert '992125907' in candidates
    
    def test_join_area_code(self):
        """Une código de área corto con siguiente parte"""
        candidates = split_phone_candidates('56 9 92125907')
        assert '569' in candidates  # código país + primer dígito


if __name__ == '__main__':
    unittest.main(verbosity=2)
