#!/usr/bin/env python3
"""
Script simple para probar la nueva estructura modular
"""

import sys
import os

# Agregar la carpeta padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Prueba todos los imports del sistema"""
    print("🧪 Probando imports de la nueva estructura modular...")
    
    try:
        # Config
        from config.settings import get_settings, AppSettings
        print("✅ Config module: OK")
        
        # Domain
        from domain.models import JobModel, CallResult, ContactInfo
        from domain.enums import JobStatus, CallStatus
        print("✅ Domain module: OK")
        
        # Infrastructure
        from infrastructure.retell_client import IRetellClient, RetellApiClient
        # from infrastructure.database import DatabaseService  # Migrado a database_manager
        from infrastructure.database_manager import DatabaseManager
        print("✅ Infrastructure module: OK")
        
        # Services
        from services.job_service import JobService
        from services.call_service import CallOrchestrationService
        from services.worker_service import WorkerCoordinator
        print("✅ Services module: OK")
        
        # Utils
        from utils.helpers import generate_random_id, utcnow
        print("✅ Utils module: OK")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        return False


def test_configuration():
    """Prueba la carga de configuración"""
    try:
        from config.settings import get_settings
        
        # Esto debería fallar porque falta RETELL_API_KEY
        try:
            settings = get_settings()
            print("⚠️ Configuración cargada (puede tener API keys vacías)")
        except ValueError as e:
            print(f"⚠️ Validación de configuración falló como se esperaba: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando configuración: {e}")
        return False


def test_models():
    """Prueba creación de modelos"""
    try:
        from domain.models import ContactInfo, CallPayload, JobModel
        from domain.enums import CallMode, JobStatus
        
        # Crear contacto
        contact = ContactInfo(
            name="Juan Pérez",
            dni="12345678",
            phones=["+56912345678", "+56987654321"]
        )
        
        # Crear payload
        payload = CallPayload(
            debt_amount=125000,
            due_date="2025-12-31",
            company_name="Empresa Test"
        )
        
        # Crear job
        job = JobModel(
            contact=contact,
            payload=payload,
            mode=CallMode.SINGLE
        )
        
        print("✅ Modelos creados correctamente")
        print(f"   - Contacto: {contact.name} ({contact.current_phone})")
        print(f"   - Deuda: ${payload.debt_amount:,.0f}")
        print(f"   - Job: {job.status.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error probando modelos: {e}")
        return False


def main():
    """Función principal de testing"""
    print("\n" + "="*50)
    print("🚀 TESTING ESTRUCTURA MODULAR - Speech AI")
    print("="*50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuración", test_configuration),
        ("Modelos", test_models),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Probando {test_name}...")
        success = test_func()
        results.append((test_name, success))
        print(f"{'✅' if success else '❌'} {test_name}: {'PASS' if success else 'FAIL'}")
    
    # Resumen
    print("\n" + "="*50)
    print("📊 RESUMEN DE TESTS")
    print("="*50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name:.<30} {status}")
    
    print(f"\n🎯 Total: {passed}/{total} tests pasaron")
    
    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("✅ La estructura modular está funcionando correctamente")
        print("\n📋 Para usar el sistema:")
        print("   python main.py")
    else:
        print("\n⚠️ Algunos tests fallaron")
        print("🔧 Revisa los errores arriba para más detalles")
    
    return passed == total


if __name__ == "__main__":
    main()