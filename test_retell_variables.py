#!/usr/bin/env python3
"""
Script para probar las variables del prompt de Retell
Simula un job y verifica que todas las variables requeridas están presentes
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from domain.use_cases.debt_collection_processor import DebtCollectionPayload
from domain.models import JobModel, ContactInfo
from datetime import datetime

def test_retell_variables():
    """Prueba que todas las variables del prompt estén presentes"""
    
    print("🧪 PRUEBA DE VARIABLES PARA RETELL AI")
    print("=" * 50)
    
    # Variables requeridas por el prompt
    required_vars = [
        'nombre',           # {{nombre}}
        'empresa',          # {{empresa}}
        'cuotas_adeudadas', # {{cuotas_adeudadas}}
        'monto_total',      # {{monto_total}}
        'fecha_limite',     # {{fecha_limite}}
        'fecha_maxima',     # {{fecha_maxima}}
    ]
    
    # Crear payload de prueba
    payload = DebtCollectionPayload(
        debt_amount=38981.0,
        due_date="2025-09-01",
        company_name="Natura",
        overdue_days=5,
        debt_type='consolidated',
        payment_options=['full_payment', 'installment_plan'],
        additional_info={
            'cantidad_cupones': 1,
            'fecha_maxima': '2025-09-05',
            'rut': '213731017',
            'batch_origen': 'batch-test'
        }
    )
    
    # Crear contacto de prueba
    contact = ContactInfo(
        name="JUANA ESTHER CORONADO SIESQUEN",
        dni="213731017",
        phones=["+5491136530246"]
    )
    
    # Crear job de prueba
    job = JobModel(
        account_id="strasing",
        batch_id="batch-test",
        contact=contact,
        payload=payload
    )
    
    # Obtener contexto para Retell
    context = job.get_context_for_retell()
    
    print("\n📋 CONTEXTO GENERADO:")
    for key, value in sorted(context.items()):
        print(f"  {key}: {value}")
    
    print("\n✅ VERIFICACIÓN DE VARIABLES REQUERIDAS:")
    missing_vars = []
    for var in required_vars:
        if var in context and context[var]:
            print(f"  ✅ {var}: '{context[var]}'")
        else:
            print(f"  ❌ {var}: FALTANTE")
            missing_vars.append(var)
    
    print("\n📊 RESUMEN:")
    if missing_vars:
        print(f"  ❌ Variables faltantes: {missing_vars}")
        print("  🚨 EL PROMPT NO FUNCIONARÁ CORRECTAMENTE")
        return False
    else:
        print("  ✅ Todas las variables requeridas están presentes")
        print("  🎉 EL PROMPT DEBERÍA FUNCIONAR CORRECTAMENTE")
        return True

if __name__ == "__main__":
    success = test_retell_variables()
    sys.exit(0 if success else 1)