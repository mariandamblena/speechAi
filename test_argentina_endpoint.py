#!/usr/bin/env python3
"""
Test script para validar el endpoint de Argentina
"""

import requests
import io
import pandas as pd

def create_test_excel():
    """Crear un archivo Excel de prueba con datos argentinos"""
    data = {
        'nombre': ['Juan Pérez', 'María González', 'Carlos López'],
        'dni': ['12.345.678', '23.456.789', '34.567.890'],
        'telefono': ['11-2345-6789', '11-3456-7890', '11-4567-8901'],
        'email': ['juan@example.com', 'maria@example.com', 'carlos@example.com'],
        'monto_deuda': [1500.50, 2300.75, 890.25],
        'fecha_vencimiento': ['01/12/2025', '15/12/2025', '30/12/2025']
    }
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel en memoria
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, sheet_name='deudores')
    excel_buffer.seek(0)
    
    return excel_buffer

def test_argentina_endpoint():
    """Probar el endpoint de Argentina"""
    print("🇦🇷 Probando endpoint de Argentina...")
    
    # URL del endpoint
    url = "http://localhost:8000/api/v1/batches/argentina/debt_collection"
    
    # Crear archivo de prueba
    excel_file = create_test_excel()
    
    # Datos del formulario
    form_data = {
        'account_id': 'test_account_argentina',
        'company_name': 'Empresa Test Argentina',
        'batch_name': 'Prueba Argentina Batch',
        'batch_description': 'Batch de prueba para números argentinos',
        'allow_duplicates': 'false',
        'retell_agent_id': 'agent_test_argentina'
    }
    
    # Archivo
    files = {
        'file': ('test_argentina.xlsx', excel_file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    }
    
    try:
        response = requests.post(url, data=form_data, files=files)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Endpoint de Argentina funcionando correctamente!")
        else:
            print("❌ Error en el endpoint de Argentina")
            
    except requests.exceptions.ConnectionError:
        print("🔧 Servidor no está corriendo. Para probar:")
        print("   cd app && python run_api.py")
        print("   Luego ejecuta este script nuevamente")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

def test_use_cases_endpoint():
    """Probar el endpoint de use cases para ver si incluye Argentina"""
    print("\n📋 Probando endpoint de use cases...")
    
    url = "http://localhost:8000/api/v1/use-cases"
    
    try:
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        result = response.json()
        print(f"Use Cases: {result.get('use_cases', [])}")
        print(f"Countries: {result.get('countries', {})}")
        
        if 'argentina' in result.get('countries', {}):
            print("✅ Argentina disponible en use cases!")
        else:
            print("❌ Argentina no encontrada en use cases")
            
    except requests.exceptions.ConnectionError:
        print("🔧 Servidor no está corriendo")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Test de Endpoint Argentina")
    print("=" * 40)
    
    # Instalar pandas si no está instalado
    try:
        import pandas as pd
    except ImportError:
        print("📦 Instalando pandas...")
        import subprocess
        subprocess.check_call(["pip", "install", "pandas", "openpyxl"])
        import pandas as pd
    
    test_use_cases_endpoint()
    test_argentina_endpoint()
    
    print("\n🎯 Para usar el endpoint:")
    print("POST /api/v1/batches/argentina/debt_collection")
    print("POST /api/v1/batches/argentina/marketing")
    print("\nEjemplo de teléfonos argentinos:")
    print("- 11-2345-6789 → +5491123456789")
    print("- 5491136530246 → +5491136530246")