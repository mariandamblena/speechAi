"""
Generador de Excel de prueba con formato correcto para cobranzas
"""
import pandas as pd
import os

def create_sample_excel():
    """Crea un archivo Excel de muestra con formato correcto"""
    
    print("📄 CREANDO EXCEL DE PRUEBA")
    print("=" * 40)
    
    # Datos de muestra en formato correcto
    sample_data = [
        {
            'RUTS': '12345678',
            'Nombre': 'Juan Pérez García',
            'Saldo actualizado': 150000,
            'Teléfono móvil': '+56912345678',
            'Teléfono Residencial': '+56221234567',
            'Origen Empresa': 'Empresa ABC',
            'FechaVencimiento': '2024-08-15',
            'diasRetraso': 30
        },
        {
            'RUTS': '87654321',
            'Nombre': 'María González López',
            'Saldo actualizado': 275000,
            'Teléfono móvil': '+56987654321',
            'Teléfono Residencial': '',
            'Origen Empresa': 'Empresa XYZ',
            'FechaVencimiento': '2024-07-20',
            'diasRetraso': 45
        },
        {
            'RUTS': '11223344',
            'Nombre': 'Carlos Rodríguez Silva',
            'Saldo actualizado': 89000,
            'Teléfono móvil': '+56911223344',
            'Teléfono Residencial': '+56225566778',
            'Origen Empresa': 'Empresa DEF',
            'FechaVencimiento': '2024-09-01',
            'diasRetraso': 15
        },
        {
            'RUTS': '99887766',
            'Nombre': 'Ana Martínez Torres',
            'Saldo actualizado': 320000,
            'Teléfono móvil': '+56999887766',
            'Teléfono Residencial': '',
            'Origen Empresa': 'Empresa GHI',
            'FechaVencimiento': '2024-06-30',
            'diasRetraso': 60
        },
        {
            'RUTS': '55443322',
            'Nombre': 'Diego Fernández Muñoz',
            'Saldo actualizado': 125000,
            'Teléfono móvil': '+56955443322',
            'Teléfono Residencial': '+56233445566',
            'Origen Empresa': 'Empresa JKL',
            'FechaVencimiento': '2024-08-10',
            'diasRetraso': 35
        }
    ]
    
    # Crear DataFrame
    df = pd.DataFrame(sample_data)
    
    # Guardar archivo Excel
    filename = 'ejemplo_cobranza_formato_correcto.xlsx'
    df.to_excel(filename, index=False, engine='openpyxl')
    
    print(f"✅ Archivo creado: {filename}")
    print(f"📊 Registros: {len(sample_data)}")
    print()
    print("📋 ESTRUCTURA DEL ARCHIVO:")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i}. {col}")
    
    print(f"\n💡 MUESTRA DE DATOS:")
    print(df.head(2).to_string(index=False))
    
    print(f"\n🚀 PARA PROBAR:")
    print(f"   1. Usa este archivo: {filename}")
    print(f"   2. Endpoint: POST /api/v1/batches/excel/create")
    print(f"   3. Parámetros:")
    print(f"      - file: {filename}")
    print(f"      - account_id: strasing")
    print(f"      - allow_duplicates: false")
    
    return filename

def show_curl_command(filename):
    """Muestra el comando curl para probar"""
    
    print(f"\n🔧 COMANDO CURL DE PRUEBA:")
    print("=" * 50)
    
    curl_command = f"""curl -X POST \\
  'http://localhost:8000/api/v1/batches/excel/create?account_id=strasing&allow_duplicates=false' \\
  -H 'accept: application/json' \\
  -H 'Content-Type: multipart/form-data' \\
  -F 'file=@{filename};type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'"""
    
    print(curl_command)
    
    print(f"\n📋 EXPLICACIÓN:")
    print(f"   • account_id=strasing (cuenta que ya existe)")
    print(f"   • allow_duplicates=false (filtrar duplicados)")
    print(f"   • Archivo: {filename}")
    
    print(f"\n⚡ PASOS PARA PROBAR:")
    print(f"   1. Asegúrate de que la API esté corriendo:")
    print(f"      cd app && python run_api.py")
    print(f"   2. En otra terminal, ejecuta el curl command")
    print(f"   3. Deberías ver resultado exitoso con estadísticas")

if __name__ == "__main__":
    filename = create_sample_excel()
    show_curl_command(filename)