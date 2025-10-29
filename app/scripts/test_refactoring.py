#!/usr/bin/env python3
"""
Script para probar la refactorización de duplicados
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from domain.models import get_job_field

def test_helper_with_old_structure():
    """Test helper con estructura antigua (campos en root)"""
    old_job = {
        'nombre': 'Juan Pérez',
        'rut': '12345678-9',
        'to_number': '+56912345678',
        'monto_total': 100000,
        'deuda': 50000,
        'fecha_limite': '2024-12-31',
        'origen_empresa': 'TestCompany'
    }
    
    print("🔍 Testing OLD structure (root level):")
    print(f"  nombre: {get_job_field(old_job, 'nombre')}")
    print(f"  rut: {get_job_field(old_job, 'rut')}")
    print(f"  to_number: {get_job_field(old_job, 'to_number')}")
    print(f"  monto_total: {get_job_field(old_job, 'monto_total')}")
    print(f"  deuda: {get_job_field(old_job, 'deuda')}")
    print(f"  fecha_limite: {get_job_field(old_job, 'fecha_limite')}")
    print(f"  origen_empresa: {get_job_field(old_job, 'origen_empresa')}")
    print()

def test_helper_with_new_structure():
    """Test helper con estructura nueva (campos en nested objects)"""
    new_job = {
        'contact': {
            'name': 'María González',
            'dni': '98765432-1',
            'phone': '+56987654321',
            'phones': ['+56987654321', '+56987654322']
        },
        'payload': {
            'debt_amount': 200000,
            'due_date': '2024-11-30',
            'company_name': 'NewCompany'
        },
        'to_number': '+56987654321'  # Este está a nivel root
    }
    
    print("🔍 Testing NEW structure (nested objects):")
    print(f"  nombre: {get_job_field(new_job, 'nombre')}")
    print(f"  rut: {get_job_field(new_job, 'rut')}")
    print(f"  to_number: {get_job_field(new_job, 'to_number')}")
    print(f"  monto_total: {get_job_field(new_job, 'monto_total')}")
    print(f"  deuda: {get_job_field(new_job, 'deuda')}")
    print(f"  fecha_limite: {get_job_field(new_job, 'fecha_limite')}")
    print(f"  origen_empresa: {get_job_field(new_job, 'origen_empresa')}")
    print()

def test_helper_with_mixed_structure():
    """Test helper con estructura mixta (algunos campos en ambos lados)"""
    mixed_job = {
        'nombre': 'Pedro López (root)',
        'contact': {
            'name': 'Pedro López (nested)',
            'dni': '11111111-1',
            'phone': '+56911111111',
            'phones': ['+56911111111']
        },
        'payload': {
            'debt_amount': 150000
        },
        'monto_total': 160000,  # Different value at root
        'to_number': '+56911111111'
    }
    
    print("🔍 Testing MIXED structure (should prefer root):")
    print(f"  nombre: {get_job_field(mixed_job, 'nombre')}")
    print(f"  rut: {get_job_field(mixed_job, 'rut')}")
    print(f"  to_number: {get_job_field(mixed_job, 'to_number')}")
    print(f"  monto_total: {get_job_field(mixed_job, 'monto_total')} (expects 160000 from root)")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing get_job_field() helper function")
    print("=" * 60)
    print()
    
    test_helper_with_old_structure()
    test_helper_with_new_structure()
    test_helper_with_mixed_structure()
    
    print("✅ All tests completed!")
