"""
Script de ejemplo para crear batches con fechas dinámicas
Demuestra cómo usar los parámetros dias_fecha_limite y dias_fecha_maxima
"""

import requests
from datetime import datetime, timedelta

# Configuración
API_URL = "http://localhost:8000/api/v1/batches/excel/create"
ACCOUNT_ID = "strasing"
EXCEL_FILE = "chile_10_usuarios (1).xlsx"


def ejemplo_1_fechas_del_excel():
    """
    EJEMPLO 1: Usar fechas del Excel (comportamiento por defecto)
    """
    print("\n" + "="*60)
    print("EJEMPLO 1: Fechas del Excel (sin cálculo dinámico)")
    print("="*60)
    
    with open(EXCEL_FILE, 'rb') as f:
        files = {'file': f}
        data = {
            'account_id': ACCOUNT_ID,
            'batch_name': 'Test - Fechas del Excel',
            'processing_type': 'basic'
        }
        
        response = requests.post(API_URL, files=files, data=data)
        
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()


def ejemplo_2_fecha_limite_30_dias():
    """
    EJEMPLO 2: Calcular fecha_limite dinámicamente (HOY + 30 días)
    """
    print("\n" + "="*60)
    print("EJEMPLO 2: fecha_limite = HOY + 30 días")
    print("="*60)
    
    # Calcular fecha esperada
    fecha_esperada = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    print(f"Fecha límite esperada: {fecha_esperada}")
    
    with open(EXCEL_FILE, 'rb') as f:
        files = {'file': f}
        data = {
            'account_id': ACCOUNT_ID,
            'batch_name': 'Test - 30 días límite',
            'processing_type': 'basic',
            'dias_fecha_limite': 30
        }
        
        response = requests.post(API_URL, files=files, data=data)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()


def ejemplo_3_ambas_fechas_dinamicas():
    """
    EJEMPLO 3: Calcular ambas fechas dinámicamente
    """
    print("\n" + "="*60)
    print("EJEMPLO 3: fecha_limite = HOY + 30, fecha_maxima = HOY + 45")
    print("="*60)
    
    # Calcular fechas esperadas
    fecha_limite = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    fecha_maxima = (datetime.now() + timedelta(days=45)).strftime('%Y-%m-%d')
    
    print(f"Fecha límite esperada: {fecha_limite}")
    print(f"Fecha máxima esperada: {fecha_maxima}")
    
    with open(EXCEL_FILE, 'rb') as f:
        files = {'file': f}
        data = {
            'account_id': ACCOUNT_ID,
            'batch_name': 'Test - Ambas fechas dinámicas',
            'processing_type': 'basic',
            'dias_fecha_limite': 30,
            'dias_fecha_maxima': 45
        }
        
        response = requests.post(API_URL, files=files, data=data)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()


def ejemplo_4_acquisition_con_fechas_dinamicas():
    """
    EJEMPLO 4: Usar procesamiento 'acquisition' con fechas dinámicas
    """
    print("\n" + "="*60)
    print("EJEMPLO 4: Acquisition + fechas dinámicas (60 y 75 días)")
    print("="*60)
    
    # Calcular fechas esperadas
    fecha_limite = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d')
    fecha_maxima = (datetime.now() + timedelta(days=75)).strftime('%Y-%m-%d')
    
    print(f"Fecha límite esperada: {fecha_limite}")
    print(f"Fecha máxima esperada: {fecha_maxima}")
    
    with open(EXCEL_FILE, 'rb') as f:
        files = {'file': f}
        data = {
            'account_id': ACCOUNT_ID,
            'batch_name': 'Test - Acquisition con fechas',
            'processing_type': 'acquisition',
            'dias_fecha_limite': 60,
            'dias_fecha_maxima': 75
        }
        
        response = requests.post(API_URL, files=files, data=data)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()


def verificar_fechas_en_jobs(batch_id):
    """
    Verificar las fechas que se guardaron en los jobs
    """
    print("\n" + "="*60)
    print(f"VERIFICANDO FECHAS EN JOBS DEL BATCH: {batch_id}")
    print("="*60)
    
    # Obtener jobs del batch
    jobs_url = f"http://localhost:8000/api/v1/batches/{batch_id}/jobs"
    response = requests.get(jobs_url)
    
    if response.status_code == 200:
        jobs = response.json()
        
        if jobs:
            print(f"\nTotal jobs: {len(jobs)}")
            print("\nPrimer job:")
            first_job = jobs[0]
            print(f"  - Job ID: {first_job.get('job_id')}")
            print(f"  - Nombre: {first_job.get('contact', {}).get('name')}")
            print(f"  - fecha_limite (due_date): {first_job.get('payload', {}).get('due_date')}")
            print(f"  - fecha_maxima: {first_job.get('payload', {}).get('additional_info', {}).get('fecha_maxima')}")
        else:
            print("No se encontraron jobs")
    else:
        print(f"Error obteniendo jobs: {response.status_code}")


# ============================================================================
# EJEMPLOS DE CURL (para copiar y pegar en terminal)
# ============================================================================

def generar_comandos_curl():
    """
    Genera comandos curl equivalentes para usar desde terminal
    """
    print("\n" + "="*60)
    print("COMANDOS CURL EQUIVALENTES")
    print("="*60)
    
    print("\n# EJEMPLO 1: Fechas del Excel")
    print(f'''curl -X POST "{API_URL}" \\
  -F "file=@{EXCEL_FILE}" \\
  -F "account_id={ACCOUNT_ID}" \\
  -F "batch_name=Test Curl - Fechas Excel" \\
  -F "processing_type=basic"
''')
    
    print("\n# EJEMPLO 2: fecha_limite = HOY + 30 días")
    print(f'''curl -X POST "{API_URL}" \\
  -F "file=@{EXCEL_FILE}" \\
  -F "account_id={ACCOUNT_ID}" \\
  -F "batch_name=Test Curl - 30 días" \\
  -F "processing_type=basic" \\
  -F "dias_fecha_limite=30"
''')
    
    print("\n# EJEMPLO 3: Ambas fechas dinámicas")
    print(f'''curl -X POST "{API_URL}" \\
  -F "file=@{EXCEL_FILE}" \\
  -F "account_id={ACCOUNT_ID}" \\
  -F "batch_name=Test Curl - Ambas fechas" \\
  -F "processing_type=basic" \\
  -F "dias_fecha_limite=30" \\
  -F "dias_fecha_maxima=45"
''')
    
    print("\n# EJEMPLO 4: Acquisition con fechas dinámicas")
    print(f'''curl -X POST "{API_URL}" \\
  -F "file=@{EXCEL_FILE}" \\
  -F "account_id={ACCOUNT_ID}" \\
  -F "batch_name=Test Curl - Acquisition" \\
  -F "processing_type=acquisition" \\
  -F "dias_fecha_limite=60" \\
  -F "dias_fecha_maxima=75"
''')


if __name__ == "__main__":
    print("🚀 EJEMPLOS DE USO: FECHAS DINÁMICAS EN BATCHES")
    print(f"📅 Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Ejecutar ejemplos
        resultado_1 = ejemplo_1_fechas_del_excel()
        
        # Esperar un momento entre requests
        import time
        time.sleep(2)
        
        resultado_2 = ejemplo_2_fecha_limite_30_dias()
        time.sleep(2)
        
        resultado_3 = ejemplo_3_ambas_fechas_dinamicas()
        time.sleep(2)
        
        resultado_4 = ejemplo_4_acquisition_con_fechas_dinamicas()
        
        # Verificar fechas en el último batch creado
        if resultado_4.get('success') and resultado_4.get('batch_id'):
            time.sleep(2)
            verificar_fechas_en_jobs(resultado_4['batch_id'])
        
        # Mostrar comandos curl
        generar_comandos_curl()
        
        print("\n" + "="*60)
        print("✅ EJEMPLOS COMPLETADOS")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
