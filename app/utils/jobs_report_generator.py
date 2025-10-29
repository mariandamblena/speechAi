"""
Generador Unificado de Reportes - Sistema SpeechAI
Genera reportes de jobs en múltiples formatos: Markdown, Excel, Terminal
"""

import os
import sys
import pandas as pd
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv
from collections import Counter
import argparse

# Agregar path del proyecto para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar helper para acceso a campos de job
from domain.models import get_job_field

load_dotenv()

class JobsReportGenerator:
    """Generador de reportes de jobs con múltiples formatos de salida"""
    
    def __init__(self):
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.mongo_db = os.getenv("MONGO_DB", "Debtors")
        self.mongo_coll = os.getenv("MONGO_COLL_JOBS", "jobs")
        self.max_tries = int(os.getenv("MAX_TRIES", "3"))
        self.retry_delay = int(os.getenv("RETRY_DELAY_MINUTES", "1"))
        self.no_answer_delay = int(os.getenv("NO_ANSWER_RETRY_MINUTES", "2"))
        
        self.client = None
        self.jobs = []
        
    def connect_database(self):
        """Conecta a MongoDB y obtiene los jobs"""
        try:
            self.client = MongoClient(self.mongo_uri)
            db = self.client[self.mongo_db]
            coll = db[self.mongo_coll]
            
            self.jobs = list(coll.find())
            print(f"✅ Conectado a MongoDB - {len(self.jobs)} jobs encontrados")
            return True
            
        except Exception as e:
            print(f"❌ Error conectando a MongoDB: {e}")
            return False
    
    def close_connection(self):
        """Cierra la conexión a MongoDB"""
        if self.client:
            self.client.close()
    
    def generate_terminal_report(self):
        """Genera reporte en terminal con colores y emojis"""
        
        if not self.jobs:
            print("❌ No hay jobs para analizar")
            return
        
        print("="*100)
        print("📊 REPORTE DE JOBS - SISTEMA SPEECHAI")
        print("="*100)
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔢 Total jobs: {len(self.jobs)}")
        
        # Métricas básicas
        status_counts = Counter([job.get('status') for job in self.jobs])
        successful = status_counts.get('done', 0)
        failed = status_counts.get('failed', 0)
        success_rate = (successful / len(self.jobs) * 100) if self.jobs else 0
        
        print(f"\n📈 RESUMEN:")
        print(f"   ✅ Exitosos: {successful} ({success_rate:.1f}%)")
        print(f"   ❌ Fallidos: {failed} ({100-success_rate:.1f}%)")
        print(f"   🔄 Intentos promedio: {sum(job.get('attempts', 0) for job in self.jobs) / len(self.jobs):.1f}")
        
        # Jobs exitosos
        successful_jobs = [job for job in self.jobs if job.get('status') == 'done']
        if successful_jobs:
            print(f"\n✅ JOBS EXITOSOS ({len(successful_jobs)}):")
            for job in successful_jobs:
                name = str(get_job_field(job, 'nombre') or 'N/A')[:40]
                phone = get_job_field(job, 'to_number') or 'N/A'
                attempts = job.get('attempts', 0)
                print(f"   👤 {name}... - 📞 {phone} - 🔄 {attempts} intentos")
        
        # Jobs fallidos
        failed_jobs = [job for job in self.jobs if job.get('status') == 'failed']
        if failed_jobs:
            print(f"\n❌ JOBS FALLIDOS ({len(failed_jobs)}):")
            for job in failed_jobs[:5]:  # Solo mostrar primeros 5
                name = str(get_job_field(job, 'nombre') or 'N/A')[:40]
                phone = get_job_field(job, 'to_number') or 'N/A'
                attempts = job.get('attempts', 0)
                error = job.get('last_error', 'N/A')[:30]
                print(f"   👤 {name}... - 📞 {phone} - 🔄 {attempts}/{self.max_tries} - ❌ {error}...")
            
            if len(failed_jobs) > 5:
                print(f"   ... y {len(failed_jobs) - 5} más")
        
        print("="*100)
    
    def generate_markdown_report(self, filename=None):
        """Genera reporte en formato Markdown"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"jobs_report_{timestamp}.md"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 📊 Reporte de Jobs - Sistema SpeechAI\n\n")
            f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Total Jobs:** {len(self.jobs)}  \n\n")
            
            # Resumen por estado
            status_counts = Counter([job.get('status') for job in self.jobs])
            f.write("## 📈 Resumen por Estado\n\n")
            for status, count in status_counts.items():
                percentage = (count / len(self.jobs)) * 100
                f.write(f"- **{status.upper()}:** {count} ({percentage:.1f}%)  \n")
            
            # Jobs exitosos
            successful_jobs = [job for job in self.jobs if job.get('status') == 'done']
            if successful_jobs:
                f.write(f"\n## ✅ Jobs Exitosos ({len(successful_jobs)})\n\n")
                f.write("| Nombre | Teléfono | Intentos | Estado Llamada |\n")
                f.write("|--------|----------|----------|----------------|\n")
                for job in successful_jobs:
                    name = str(get_job_field(job, 'nombre') or 'N/A')[:30]
                    phone = get_job_field(job, 'to_number') or 'N/A'
                    attempts = job.get('attempts', 0)
                    call_status = job.get('call_result', {}).get('call_status', 'N/A')
                    f.write(f"| {name} | {phone} | {attempts} | {call_status} |\n")
            
            # Jobs fallidos
            failed_jobs = [job for job in self.jobs if job.get('status') == 'failed']
            if failed_jobs:
                f.write(f"\n## ❌ Jobs Fallidos ({len(failed_jobs)})\n\n")
                f.write("| Nombre | Teléfono | Intentos | Último Error |\n")
                f.write("|--------|----------|----------|---------------|\n")
                for job in failed_jobs:
                    name = str(get_job_field(job, 'nombre') or 'N/A')[:30]
                    phone = get_job_field(job, 'to_number') or 'N/A'
                    attempts = job.get('attempts', 0)
                    error = job.get('last_error', 'N/A')[:50]
                    f.write(f"| {name} | {phone} | {attempts} | {error} |\n")
            
            f.write(f"\n---\n*Reporte generado automáticamente por SpeechAI System*")
        
        print(f"📄 Reporte Markdown guardado: {filename}")
        return filename
    
    def generate_excel_report(self, filename=None):
        """Genera reporte en formato Excel con múltiples hojas"""
        
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reporte_jobs_{timestamp}.xlsx"
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                
                # Hoja 1: Resumen Ejecutivo
                self._create_excel_summary_sheet(writer)
                
                # Hoja 2: Jobs Exitosos
                self._create_excel_successful_sheet(writer)
                
                # Hoja 3: Jobs Fallidos
                self._create_excel_failed_sheet(writer)
                
                # Hoja 4: Datos Completos
                self._create_excel_complete_sheet(writer)
            
            print(f"📊 Reporte Excel guardado: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Error generando Excel: {e}")
            return None
    
    def _create_excel_summary_sheet(self, writer):
        """Crea hoja de resumen para Excel"""
        
        total_jobs = len(self.jobs)
        status_counts = Counter([job.get('status') for job in self.jobs])
        successful = status_counts.get('done', 0)
        failed = status_counts.get('failed', 0)
        success_rate = (successful / total_jobs * 100) if total_jobs > 0 else 0
        avg_attempts = sum(job.get('attempts', 0) for job in self.jobs) / total_jobs if total_jobs > 0 else 0
        
        summary_data = {
            'Métrica': [
                'Total de Jobs',
                'Jobs Exitosos',
                'Jobs Fallidos',
                'Tasa de Éxito (%)',
                'Intentos Promedio',
                'Límite de Intentos',
                'Workers Activos',
                'Delay General (min)',
                'Delay No Contesta (min)'
            ],
            'Valor': [
                total_jobs,
                successful,
                failed,
                round(success_rate, 1),
                round(avg_attempts, 1),
                self.max_tries,
                int(os.getenv('WORKER_COUNT', '3')),
                self.retry_delay,
                self.no_answer_delay
            ]
        }
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='Resumen', index=False)
    
    def _create_excel_successful_sheet(self, writer):
        """Crea hoja de jobs exitosos para Excel"""
        
        successful_jobs = [job for job in self.jobs if job.get('status') == 'done']
        
        if not successful_jobs:
            df_empty = pd.DataFrame({'Mensaje': ['No hay jobs exitosos']})
            df_empty.to_excel(writer, sheet_name='Exitosos', index=False)
            return
        
        successful_data = []
        for job in successful_jobs:
            call_result = job.get('call_result', {})
            contact = job.get('contact', {})
            
            successful_data.append({
                'Nombre': get_job_field(job, 'nombre') or 'N/A',
                'DNI': contact.get('dni', 'N/A'),
                'Teléfono': get_job_field(job, 'to_number') or 'N/A',
                'Intentos': job.get('attempts', 0),
                'Estado Llamada': call_result.get('call_status', 'N/A'),
                'Call ID': call_result.get('call_id', 'N/A'),
                'Duración (seg)': call_result.get('duration_ms', 0) / 1000 if call_result.get('duration_ms') else 0,
                'Fecha Completado': self._format_date(job.get('finished_at'))
            })
        
        df_successful = pd.DataFrame(successful_data)
        df_successful.to_excel(writer, sheet_name='Exitosos', index=False)
    
    def _create_excel_failed_sheet(self, writer):
        """Crea hoja de jobs fallidos para Excel"""
        
        failed_jobs = [job for job in self.jobs if job.get('status') == 'failed']
        
        if not failed_jobs:
            df_empty = pd.DataFrame({'Mensaje': ['No hay jobs fallidos']})
            df_empty.to_excel(writer, sheet_name='Fallidos', index=False)
            return
        
        failed_data = []
        for job in failed_jobs:
            contact = job.get('contact', {})
            
            failed_data.append({
                'Nombre': get_job_field(job, 'nombre') or 'N/A',
                'DNI': contact.get('dni', 'N/A'),
                'Teléfono': get_job_field(job, 'to_number') or 'N/A',
                'Intentos': job.get('attempts', 0),
                'Último Error': job.get('last_error', 'N/A'),
                'Próximo Intento': self._format_date(job.get('next_try_at')),
                'Worker ID': job.get('worker_id', 'N/A'),
                'Última Actualización': self._format_date(job.get('updated_at'))
            })
        
        df_failed = pd.DataFrame(failed_data)
        df_failed.to_excel(writer, sheet_name='Fallidos', index=False)
    
    def _create_excel_complete_sheet(self, writer):
        """Crea hoja de datos completos para Excel"""
        
        complete_data = []
        for job in self.jobs:
            contact = job.get('contact', {})
            call_result = job.get('call_result', {})
            payload = job.get('payload', {})
            
            complete_data.append({
                'ID': str(job.get('_id', '')),
                'Estado': job.get('status', 'N/A'),
                'Nombre': get_job_field(job, 'nombre') or 'N/A',
                'DNI': contact.get('dni', 'N/A'),
                'Teléfono': get_job_field(job, 'to_number') or 'N/A',
                'Intentos': job.get('attempts', 0),
                'Último Error': job.get('last_error', 'N/A'),
                'Call ID': call_result.get('call_id', 'N/A'),
                'Estado Llamada': call_result.get('call_status', 'N/A'),
                'Worker ID': job.get('worker_id', 'N/A'),
                'Creado': self._format_date(job.get('created_at')),
                'Actualizado': self._format_date(job.get('updated_at')),
                'Account ID': job.get('account_id', 'N/A'),
                'Batch ID': job.get('batch_id', 'N/A'),
                'Cantidad Cupones': payload.get('cantidad_cupones', 'N/A'),
                'Fecha Máxima': payload.get('fecha_maxima', 'N/A')
            })
        
        df_complete = pd.DataFrame(complete_data)
        df_complete.to_excel(writer, sheet_name='Datos Completos', index=False)
    
    def _format_date(self, date_value):
        """Formatea fechas para reportes"""
        if not date_value:
            return 'N/A'
        
        try:
            if isinstance(date_value, str):
                dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            elif hasattr(date_value, 'strftime'):
                dt = date_value
            else:
                return str(date_value)
            
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return str(date_value)
    
    def generate_all_reports(self, base_filename=None):
        """Genera todos los tipos de reporte"""
        
        if not base_filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"jobs_report_{timestamp}"
        
        print("🔄 Generando todos los reportes...")
        
        # Terminal
        self.generate_terminal_report()
        
        # Markdown
        md_file = self.generate_markdown_report(f"{base_filename}.md")
        
        # Excel
        xlsx_file = self.generate_excel_report(f"{base_filename}.xlsx")
        
        print(f"\n✅ Reportes generados:")
        print(f"   📄 Markdown: {md_file}")
        print(f"   📊 Excel: {xlsx_file}")
        
        return {
            'markdown': md_file,
            'excel': xlsx_file
        }

def main():
    """Función principal con argumentos de línea de comandos"""
    
    parser = argparse.ArgumentParser(description='Generador de Reportes de Jobs - SpeechAI')
    parser.add_argument('--format', choices=['terminal', 'markdown', 'excel', 'all'], 
                       default='terminal', help='Formato del reporte')
    parser.add_argument('--output', help='Nombre del archivo de salida (sin extensión)')
    
    args = parser.parse_args()
    
    # Crear generador
    generator = JobsReportGenerator()
    
    try:
        # Conectar a base de datos
        if not generator.connect_database():
            return 1
        
        # Generar reportes según el formato solicitado
        if args.format == 'terminal':
            generator.generate_terminal_report()
        elif args.format == 'markdown':
            filename = f"{args.output}.md" if args.output else None
            generator.generate_markdown_report(filename)
        elif args.format == 'excel':
            filename = f"{args.output}.xlsx" if args.output else None
            generator.generate_excel_report(filename)
        elif args.format == 'all':
            generator.generate_all_reports(args.output)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
        
    finally:
        generator.close_connection()

if __name__ == "__main__":
    exit(main())