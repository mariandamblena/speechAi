"""
Generador de Reporte de Jobs en Excel
Extrae datos de MongoDB y genera archivo Excel con múltiples hojas
"""

import os
import pandas as pd
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import Counter

load_dotenv()

def generate_excel_report():
    """Genera reporte completo en Excel"""
    
    # Conexión a MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB = os.getenv("MONGO_DB", "Debtors")
    MONGO_COLL_JOBS = os.getenv("MONGO_COLL_JOBS", "jobs")
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    coll = db[MONGO_COLL_JOBS]
    
    # Obtener todos los jobs
    all_jobs = list(coll.find())
    
    print("📊 Generando reporte Excel...")
    print(f"📁 Total jobs encontrados: {len(all_jobs)}")
    
    # Crear archivo Excel con múltiples hojas
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"reporte_jobs_{timestamp}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        
        # ============================================================================
        # HOJA 1: RESUMEN EJECUTIVO
        # ============================================================================
        
        create_summary_sheet(all_jobs, writer)
        
        # ============================================================================
        # HOJA 2: JOBS EXITOSOS
        # ============================================================================
        
        create_successful_jobs_sheet(all_jobs, writer)
        
        # ============================================================================
        # HOJA 3: JOBS FALLIDOS
        # ============================================================================
        
        create_failed_jobs_sheet(all_jobs, writer)
        
        # ============================================================================
        # HOJA 4: ANÁLISIS DETALLADO
        # ============================================================================
        
        create_detailed_analysis_sheet(all_jobs, writer)
        
        # ============================================================================
        # HOJA 5: DATOS COMPLETOS
        # ============================================================================
        
        create_complete_data_sheet(all_jobs, writer)
    
    client.close()
    
    print(f"✅ Reporte Excel generado: {filename}")
    print(f"📍 Ubicación: {os.path.abspath(filename)}")
    
    return filename

def create_summary_sheet(jobs, writer):
    """Crea hoja de resumen ejecutivo"""
    
    print("📋 Creando hoja: Resumen Ejecutivo...")
    
    # Calcular métricas
    total_jobs = len(jobs)
    status_counts = Counter([job.get('status') for job in jobs])
    successful_jobs = status_counts.get('done', 0)
    failed_jobs = status_counts.get('failed', 0)
    success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
    
    avg_attempts = sum(job.get('attempts', 0) for job in jobs) / total_jobs if total_jobs > 0 else 0
    
    # Crear DataFrame de resumen
    summary_data = {
        'Métrica': [
            'Total de Jobs',
            'Jobs Exitosos',
            'Jobs Fallidos', 
            'Tasa de Éxito (%)',
            'Tasa de Fallo (%)',
            'Intentos Promedio',
            'Límite de Intentos',
            'Workers Activos',
            'Delay Error General (min)',
            'Delay No Contesta (min)'
        ],
        'Valor': [
            total_jobs,
            successful_jobs,
            failed_jobs,
            round(success_rate, 1),
            round(100 - success_rate, 1),
            round(avg_attempts, 1),
            int(os.getenv('MAX_TRIES', '3')),
            int(os.getenv('WORKER_COUNT', '3')),
            int(os.getenv('RETRY_DELAY_MINUTES', '1')),
            int(os.getenv('NO_ANSWER_RETRY_MINUTES', '2'))
        ]
    }
    
    df_summary = pd.DataFrame(summary_data)
    df_summary.to_excel(writer, sheet_name='Resumen Ejecutivo', index=False)

def create_successful_jobs_sheet(jobs, writer):
    """Crea hoja de jobs exitosos"""
    
    print("✅ Creando hoja: Jobs Exitosos...")
    
    successful_jobs = [job for job in jobs if job.get('status') == 'done']
    
    if not successful_jobs:
        # Crear DataFrame vacío si no hay jobs exitosos
        df_empty = pd.DataFrame({'Mensaje': ['No hay jobs exitosos en este batch']})
        df_empty.to_excel(writer, sheet_name='Jobs Exitosos', index=False)
        return
    
    # Preparar datos
    successful_data = []
    for job in successful_jobs:
        call_result = job.get('call_result', {})
        contact = job.get('contact', {})
        
        successful_data.append({
            'ID': str(job.get('_id', '')),
            'Nombre': job.get('nombre', 'N/A'),
            'RUT/DNI': contact.get('dni', 'N/A'),
            'Teléfono': job.get('to_number', 'N/A'),
            'Intentos': job.get('attempts', 0),
            'Estado Llamada': call_result.get('call_status', 'N/A'),
            'Duración (seg)': call_result.get('duration_ms', 0) / 1000 if call_result.get('duration_ms') else 0,
            'Fecha Creación': format_date(job.get('created_at')),
            'Fecha Completado': format_date(job.get('finished_at')),
            'Call ID': call_result.get('call_id', 'N/A'),
            'Éxito': call_result.get('success', False)
        })
    
    df_successful = pd.DataFrame(successful_data)
    df_successful.to_excel(writer, sheet_name='Jobs Exitosos', index=False)

def create_failed_jobs_sheet(jobs, writer):
    """Crea hoja de jobs fallidos"""
    
    print("❌ Creando hoja: Jobs Fallidos...")
    
    failed_jobs = [job for job in jobs if job.get('status') == 'failed']
    
    if not failed_jobs:
        # Crear DataFrame vacío si no hay jobs fallidos
        df_empty = pd.DataFrame({'Mensaje': ['No hay jobs fallidos en este batch']})
        df_empty.to_excel(writer, sheet_name='Jobs Fallidos', index=False)
        return
    
    # Preparar datos
    failed_data = []
    for job in failed_jobs:
        contact = job.get('contact', {})
        
        failed_data.append({
            'ID': str(job.get('_id', '')),
            'Nombre': job.get('nombre', 'N/A'),
            'RUT/DNI': contact.get('dni', 'N/A'),
            'Teléfono': job.get('to_number', 'N/A'),
            'Intentos': job.get('attempts', 0),
            'Intentos Máximos': job.get('max_attempts', 3),
            'Último Error': job.get('last_error', 'N/A'),
            'Próximo Intento': format_date(job.get('next_try_at')),
            'Fecha Creación': format_date(job.get('created_at')),
            'Última Actualización': format_date(job.get('updated_at')),
            'Estado Final': 'TERMINADO' if job.get('attempts', 0) >= job.get('max_attempts', 3) else 'PENDIENTE',
            'Worker ID': job.get('worker_id', 'N/A'),
            'Índice Teléfono': contact.get('next_phone_index', 0)
        })
    
    df_failed = pd.DataFrame(failed_data)
    df_failed.to_excel(writer, sheet_name='Jobs Fallidos', index=False)

def create_detailed_analysis_sheet(jobs, writer):
    """Crea hoja de análisis detallado"""
    
    print("🔍 Creando hoja: Análisis Detallado...")
    
    # Análisis por estado
    status_analysis = []
    status_counts = Counter([job.get('status') for job in jobs])
    total_jobs = len(jobs)
    
    for status, count in status_counts.items():
        percentage = (count / total_jobs * 100) if total_jobs > 0 else 0
        status_analysis.append({
            'Estado': status.upper(),
            'Cantidad': count,
            'Porcentaje': round(percentage, 1)
        })
    
    # Análisis por número de intentos
    attempts_analysis = []
    attempts_counts = Counter([job.get('attempts', 0) for job in jobs])
    
    for attempts, count in sorted(attempts_counts.items()):
        percentage = (count / total_jobs * 100) if total_jobs > 0 else 0
        attempts_analysis.append({
            'Intentos': attempts,
            'Cantidad Jobs': count,
            'Porcentaje': round(percentage, 1)
        })
    
    # Análisis de errores más comunes
    error_analysis = []
    errors = [job.get('last_error', 'N/A') for job in jobs if job.get('last_error')]
    error_counts = Counter(errors)
    
    for error, count in error_counts.most_common(10):
        percentage = (count / len(errors) * 100) if errors else 0
        error_analysis.append({
            'Error': error[:50] + '...' if len(error) > 50 else error,
            'Frecuencia': count,
            'Porcentaje': round(percentage, 1)
        })
    
    # Crear DataFrames y escribir en diferentes secciones
    df_status = pd.DataFrame(status_analysis)
    df_attempts = pd.DataFrame(attempts_analysis)
    df_errors = pd.DataFrame(error_analysis)
    
    # Escribir análisis en la misma hoja con separaciones
    start_row = 0
    
    # Análisis por estado
    pd.DataFrame([['ANÁLISIS POR ESTADO']]).to_excel(
        writer, sheet_name='Análisis Detallado', 
        startrow=start_row, index=False, header=False
    )
    df_status.to_excel(
        writer, sheet_name='Análisis Detallado', 
        startrow=start_row + 2, index=False
    )
    
    # Análisis por intentos
    start_row += len(df_status) + 6
    pd.DataFrame([['ANÁLISIS POR INTENTOS']]).to_excel(
        writer, sheet_name='Análisis Detallado', 
        startrow=start_row, index=False, header=False
    )
    df_attempts.to_excel(
        writer, sheet_name='Análisis Detallado', 
        startrow=start_row + 2, index=False
    )
    
    # Análisis de errores
    start_row += len(df_attempts) + 6
    pd.DataFrame([['ERRORES MÁS COMUNES']]).to_excel(
        writer, sheet_name='Análisis Detallado', 
        startrow=start_row, index=False, header=False
    )
    df_errors.to_excel(
        writer, sheet_name='Análisis Detallado', 
        startrow=start_row + 2, index=False
    )

def create_complete_data_sheet(jobs, writer):
    """Crea hoja con todos los datos completos"""
    
    print("📊 Creando hoja: Datos Completos...")
    
    # Preparar datos completos
    complete_data = []
    for job in jobs:
        contact = job.get('contact', {})
        call_result = job.get('call_result', {})
        payload = job.get('payload', {})
        
        complete_data.append({
            'ID': str(job.get('_id', '')),
            'Estado': job.get('status', 'N/A'),
            'Nombre': job.get('nombre', 'N/A'),
            'RUT/DNI': contact.get('dni', 'N/A'),
            'Teléfono Principal': job.get('to_number', 'N/A'),
            'Teléfonos Disponibles': str(contact.get('phones', [])),
            'Índice Teléfono Actual': contact.get('next_phone_index', 0),
            'Intentos': job.get('attempts', 0),
            'Intentos Máximos': job.get('max_attempts', 3),
            'Último Error': job.get('last_error', 'N/A'),
            'Próximo Intento': format_date(job.get('next_try_at')),
            'Call ID': call_result.get('call_id', 'N/A'),
            'Estado Llamada': call_result.get('call_status', 'N/A'),
            'Duración (ms)': call_result.get('duration_ms', 0),
            'Éxito Llamada': call_result.get('success', False),
            'Worker ID': job.get('worker_id', 'N/A'),
            'Fecha Creación': format_date(job.get('created_at')),
            'Fecha Inicio': format_date(job.get('started_at')),
            'Fecha Finalización': format_date(job.get('finished_at')),
            'Última Actualización': format_date(job.get('updated_at')),
            'Reservado Hasta': format_date(job.get('reserved_until')),
            'Caso de Uso': job.get('use_case', 'N/A'),
            'País': job.get('country', 'N/A'),
            'Account ID': job.get('account_id', 'N/A'),
            'Batch ID': job.get('batch_id', 'N/A'),
            'Cantidad Cupones': payload.get('cantidad_cupones', 'N/A'),
            'Fecha Máxima': payload.get('fecha_maxima', 'N/A'),
            'Monto Deuda': payload.get('monto_deuda', 'N/A'),
        })
    
    df_complete = pd.DataFrame(complete_data)
    df_complete.to_excel(writer, sheet_name='Datos Completos', index=False)

def format_date(date_value):
    """Formatea fechas para Excel"""
    if not date_value:
        return 'N/A'
    
    try:
        if isinstance(date_value, str):
            # Intentar parsear string de fecha
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
        elif hasattr(date_value, 'strftime'):
            # Ya es un objeto datetime
            dt = date_value
        else:
            return str(date_value)
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(date_value)

if __name__ == "__main__":
    filename = generate_excel_report()
    print(f"\n🎉 Reporte Excel completado!")
    print(f"📁 Archivo: {filename}")
    print(f"📊 Contiene 5 hojas:")
    print(f"   1️⃣ Resumen Ejecutivo")
    print(f"   2️⃣ Jobs Exitosos") 
    print(f"   3️⃣ Jobs Fallidos")
    print(f"   4️⃣ Análisis Detallado")
    print(f"   5️⃣ Datos Completos")