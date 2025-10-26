"""
Test completo del soporte multi-país
Verifica que el sistema procese correctamente teléfonos de Chile y Argentina
"""

import unittest
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from utils.excel_processor import ExcelDebtorProcessor
from utils.normalizers import (
    normalize_phone_cl,
    normalize_phone_ar,
    format_rut,
    add_days_iso,
    normalize_rut,
    normalize_key
)


class TestMultiCountrySupport(unittest.TestCase):
    """Tests de soporte multi-país"""
    
    def test_excel_processor_chile(self):
        """Test procesador de Excel para Chile"""
        processor = ExcelDebtorProcessor(country="CL")
        
        # Verificar que usa el normalizador correcto
        self.assertEqual(processor.country, "CL")
        self.assertEqual(processor.normalize_phone, normalize_phone_cl)
        
    def test_excel_processor_argentina(self):
        """Test procesador de Excel para Argentina"""
        processor = ExcelDebtorProcessor(country="AR")
        
        # Verificar que usa el normalizador correcto
        self.assertEqual(processor.country, "AR")
        self.assertEqual(processor.normalize_phone, normalize_phone_ar)
    
    def test_excel_processor_default_chile(self):
        """Test que el default sea Chile"""
        processor = ExcelDebtorProcessor()
        self.assertEqual(processor.country, "CL")
        self.assertEqual(processor.normalize_phone, normalize_phone_cl)


class TestChilePhoneNormalization(unittest.TestCase):
    """Tests de normalización de teléfonos chilenos"""
    
    def test_mobile_9_digits(self):
        """Móviles chilenos de 9 dígitos"""
        self.assertEqual(normalize_phone_cl('938773910', 'mobile'), '+56938773910')
        self.assertEqual(normalize_phone_cl('990464905', 'mobile'), '+56990464905')
        self.assertEqual(normalize_phone_cl('965896993', 'mobile'), '+56965896993')
    
    def test_mobile_with_country_code(self):
        """Móviles que ya tienen código de país"""
        self.assertEqual(normalize_phone_cl('56938773910', 'mobile'), '+56938773910')
        self.assertEqual(normalize_phone_cl('+56938773910', 'mobile'), '+56938773910')
    
    def test_landline_santiago(self):
        """Teléfonos fijos de Santiago"""
        self.assertEqual(normalize_phone_cl('222345678', 'landline'), '+56222345678')
        self.assertEqual(normalize_phone_cl('223456789', 'any'), '+56223456789')
    
    def test_invalid_chile_phones(self):
        """Teléfonos inválidos para Chile"""
        # Muy corto
        self.assertIsNone(normalize_phone_cl('12345', 'any'))
        # Muy largo
        self.assertIsNone(normalize_phone_cl('123456789012', 'any'))
        # Número argentino
        self.assertIsNone(normalize_phone_cl('1123456789', 'any'))


class TestArgentinaPhoneNormalization(unittest.TestCase):
    """Tests de normalización de teléfonos argentinos"""
    
    def test_mobile_buenos_aires(self):
        """Móviles de Buenos Aires"""
        self.assertEqual(normalize_phone_ar('91123456789', 'mobile'), '+5491123456789')
        self.assertEqual(normalize_phone_ar('911 2345 6789', 'mobile'), '+5491123456789')
    
    def test_landline_buenos_aires(self):
        """Fijos de Buenos Aires"""
        self.assertEqual(normalize_phone_ar('1123456789', 'landline'), '+541123456789')
        self.assertEqual(normalize_phone_ar('11 2345 6789', 'landline'), '+541123456789')
    
    def test_argentina_with_country_code(self):
        """Números con código de país"""
        self.assertEqual(normalize_phone_ar('5491123456789', 'any'), '+5491123456789')
        self.assertEqual(normalize_phone_ar('+5491123456789', 'any'), '+5491123456789')
    
    def test_trunk_prefix_removal(self):
        """Remover prefijo de trunk (0)"""
        self.assertEqual(normalize_phone_ar('091123456789', 'any'), '+5491123456789')
        self.assertEqual(normalize_phone_ar('01123456789', 'any'), '+541123456789')
    
    def test_invalid_argentina_phones(self):
        """Teléfonos inválidos para Argentina"""
        self.assertIsNone(normalize_phone_ar('', 'any'))
        self.assertIsNone(normalize_phone_ar(None, 'any'))
        self.assertIsNone(normalize_phone_ar('123', 'any'))


class TestRealWorldScenario(unittest.TestCase):
    """Tests de escenarios reales del problema reportado"""
    
    def test_original_problem_phone(self):
        """
        Test del problema original:
        Teléfono argentino 54113650246 era rechazado por normalize_phone_cl
        """
        # En Chile (antes del fix): rechazado
        result_cl = normalize_phone_cl('54113650246', 'any')
        self.assertIsNone(result_cl, "Chile correctamente rechaza teléfono argentino")
        
        # En Argentina (después del fix): aceptado y normalizado
        # El normalizador detecta que es un móvil de Buenos Aires y agrega el 9
        result_ar = normalize_phone_ar('54113650246', 'any')
        self.assertEqual(result_ar, '+5491113650246', 
                        "Argentina acepta y normaliza correctamente (agrega 9 móvil)")
    
    def test_batch_with_12_argentina_phones(self):
        """
        Simula el batch que falló con 12 teléfonos argentinos
        """
        argentina_phones = [
            '54113650246',  # El teléfono del problema original
            '91123456789',
            '1145678901',
            '91145678901',
            '1167890123',
            '91167890123',
            '1189012345',
            '91189012345',
            '1123456789',
            '91123456789',
            '1134567890',
            '91134567890',
        ]
        
        # Procesador Argentina
        processor_ar = ExcelDebtorProcessor(country="AR")
        
        normalized_count = 0
        for phone in argentina_phones:
            result = processor_ar.normalize_phone(phone, 'any')
            if result:
                normalized_count += 1
                self.assertTrue(result.startswith('+54'), 
                              f"Teléfono {phone} debe empezar con +54")
        
        # Todos los 12 teléfonos deben normalizarse
        self.assertEqual(normalized_count, 12, 
                        "Los 12 teléfonos argentinos deben normalizarse correctamente")
    
    def test_batch_with_chile_phones_using_chile_processor(self):
        """
        Batch chileno con procesador chileno (debe funcionar)
        """
        chile_phones = [
            '938773910',
            '990464905',
            '965896993',
            '912345678',
            '987654321',
            '945678901',
            '223456789',  # Fijo Santiago
            '322345678',  # Fijo Valparaíso (3 + 8)
            '222345678',
            '933445566',
            '977889900',
            '911223344',
        ]
        
        processor_cl = ExcelDebtorProcessor(country="CL")
        
        normalized_count = 0
        for phone in chile_phones:
            result = processor_cl.normalize_phone(phone, 'any')
            if result:
                normalized_count += 1
                self.assertTrue(result.startswith('+56'),
                              f"Teléfono {phone} debe empezar con +56")
        
        # Todos los 12 teléfonos deben normalizarse
        self.assertEqual(normalized_count, 12,
                        "Los 12 teléfonos chilenos deben normalizarse correctamente")


class TestHelperFunctions(unittest.TestCase):
    """Tests de funciones auxiliares agregadas"""
    
    def test_format_rut(self):
        """Test formateo de RUT"""
        self.assertEqual(format_rut('123456789'), '12.345.678-9')
        self.assertEqual(format_rut('12345678K'), '12.345.678-K')
        self.assertEqual(format_rut('987654'), '98.765-4')
    
    def test_normalize_rut(self):
        """Test normalización de RUT"""
        self.assertEqual(normalize_rut('12.345.678-9'), '123456789')
        self.assertEqual(normalize_rut('12345678-K'), '12345678K')
        self.assertEqual(normalize_rut('12.345.678-k'), '12345678K')
    
    def test_add_days_iso(self):
        """Test suma de días a fecha ISO"""
        self.assertEqual(add_days_iso('2025-10-26', 7), '2025-11-02')
        self.assertEqual(add_days_iso('2025-10-26', -5), '2025-10-21')
        self.assertEqual(add_days_iso('2025-12-25', 7), '2026-01-01')
    
    def test_normalize_key(self):
        """Test normalización de claves de columnas"""
        self.assertEqual(normalize_key('Teléfono Móvil'), 'telefonomovil')
        self.assertEqual(normalize_key('Nombre Completo'), 'nombrecompleto')
        self.assertEqual(normalize_key('DIRECCIÓN'), 'direccion')


class TestAccountModelIntegration(unittest.TestCase):
    """Tests de integración con AccountModel"""
    
    def test_account_country_field(self):
        """Test que AccountModel tiene campo country"""
        from domain.models import AccountModel
        
        account = AccountModel(
            account_id="test-123",
            account_name="Test Account",
            country="AR",
            timezone="America/Argentina/Buenos_Aires"
        )
        
        self.assertEqual(account.country, "AR")
        self.assertEqual(account.timezone, "America/Argentina/Buenos_Aires")
    
    def test_account_default_country(self):
        """Test que el default sea Chile"""
        from domain.models import AccountModel
        
        account = AccountModel(
            account_id="test-456",
            account_name="Test Account CL"
        )
        
        self.assertEqual(account.country, "CL")
    
    def test_account_to_dict_includes_country(self):
        """Test que to_dict() incluya country"""
        from domain.models import AccountModel
        
        account = AccountModel(
            account_id="test-789",
            account_name="Test Account",
            country="AR",
            timezone="America/Argentina/Buenos_Aires"
        )
        
        account_dict = account.to_dict()
        self.assertIn('country', account_dict)
        self.assertEqual(account_dict['country'], 'AR')
        self.assertIn('timezone', account_dict)


def run_tests():
    """Ejecuta todos los tests y muestra resumen"""
    print("=" * 70)
    print("🧪 TEST SUITE: Soporte Multi-País")
    print("=" * 70)
    print()
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar todas las clases de test
    suite.addTests(loader.loadTestsFromTestCase(TestMultiCountrySupport))
    suite.addTests(loader.loadTestsFromTestCase(TestChilePhoneNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestArgentinaPhoneNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestRealWorldScenario))
    suite.addTests(loader.loadTestsFromTestCase(TestHelperFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestAccountModelIntegration))
    
    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Resumen
    print()
    print("=" * 70)
    print("📊 RESUMEN DE TESTS")
    print("=" * 70)
    print(f"✅ Tests ejecutados: {result.testsRun}")
    print(f"✅ Exitosos: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Fallidos: {len(result.failures)}")
    print(f"💥 Errores: {len(result.errors)}")
    print()
    
    if result.wasSuccessful():
        print("🎉 ¡TODOS LOS TESTS PASARON!")
        print()
        print("✅ El sistema ahora soporta:")
        print("   - 🇨🇱 Chile: Normalización de teléfonos +56XXXXXXXXX")
        print("   - 🇦🇷 Argentina: Normalización de teléfonos +54XXXXXXXXXXX")
        print("   - 🔄 Auto-detección de país por cuenta")
        print("   - 📱 ExcelDebtorProcessor multi-país")
        print("   - 🗂️ AccountModel con campos country y timezone")
    else:
        print("⚠️ Algunos tests fallaron. Revisa los errores arriba.")
    
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
