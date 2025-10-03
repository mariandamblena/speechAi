#!/usr/bin/env python3
"""
Launcher principal para generar reportes de llamadas
Menú interactivo para elegir el tipo de reporte
"""

import os
import sys
import subprocess
from datetime import datetime

def show_menu():
    """Mostrar menú principal"""
    print("📊 GENERADOR DE REPORTES DE LLAMADAS")
    print("=" * 50)
    print()
    print("Opciones disponibles:")
    print("1. 📋 Reporte rápido (últimos 7 días)")
    print("2. 📅 Reporte personalizado por días")
    print("3. 🎯 Reporte de cuenta específica")
    print("4. 📦 Reporte de batch específico")
    print("5. 📈 Reporte con rango de fechas")
    print("6. 🔍 Ver estadísticas rápidas")
    print("7. ❓ Ayuda completa")
    print("0. 👋 Salir")
    print()

def quick_report():
    """Generar reporte rápido de últimos 7 días"""
    print("📋 Generando reporte rápido de los últimos 7 días...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reporte_rapido_{timestamp}.xlsx"
    
    cmd = ["python", "simple_report.py", "--days", "7", "--output", filename]
    subprocess.run(cmd)

def custom_days_report():
    """Reporte personalizado por días"""
    try:
        days = input("📅 ¿Cuántos días hacia atrás? (default 7): ").strip()
        days = int(days) if days else 7
        
        filename = input("💾 Nombre del archivo (Enter para automático): ").strip()
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reporte_{days}dias_{timestamp}.xlsx"
        
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        
        print(f"📊 Generando reporte de {days} días...")
        cmd = ["python", "generate_call_report.py", "--days", str(days), "--output", filename]
        subprocess.run(cmd)
        
    except ValueError:
        print("❌ Por favor ingresa un número válido")
    except KeyboardInterrupt:
        print("\n👋 Cancelado")

def account_report():
    """Reporte de cuenta específica"""
    try:
        account_id = input("🎯 ID de la cuenta: ").strip()
        if not account_id:
            print("❌ Debes ingresar un ID de cuenta")
            return
        
        days = input("📅 Días hacia atrás (default 30): ").strip()
        days = int(days) if days else 30
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reporte_cuenta_{account_id}_{timestamp}.xlsx"
        
        print(f"📊 Generando reporte para cuenta {account_id}...")
        cmd = [
            "python", "generate_call_report.py", 
            "--account-id", account_id,
            "--days", str(days),
            "--output", filename
        ]
        subprocess.run(cmd)
        
    except ValueError:
        print("❌ Por favor ingresa un número válido")
    except KeyboardInterrupt:
        print("\n👋 Cancelado")

def batch_report():
    """Reporte de batch específico"""
    try:
        batch_id = input("📦 ID del batch: ").strip()
        if not batch_id:
            print("❌ Debes ingresar un ID de batch")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reporte_batch_{batch_id}_{timestamp}.xlsx"
        
        print(f"📊 Generando reporte para batch {batch_id}...")
        cmd = [
            "python", "generate_call_report.py", 
            "--batch-id", batch_id,
            "--output", filename
        ]
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 Cancelado")

def date_range_report():
    """Reporte con rango de fechas"""
    try:
        print("📅 Formato de fecha: YYYY-MM-DD (ej: 2025-09-01)")
        start_date = input("📅 Fecha de inicio: ").strip()
        end_date = input("📅 Fecha de fin (Enter para hoy): ").strip()
        
        if not start_date:
            print("❌ Debes ingresar una fecha de inicio")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reporte_rango_{timestamp}.xlsx"
        
        cmd = [
            "python", "generate_call_report.py", 
            "--start-date", start_date,
            "--output", filename
        ]
        
        if end_date:
            cmd.extend(["--end-date", end_date])
        
        print(f"📊 Generando reporte desde {start_date}...")
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n👋 Cancelado")

def quick_stats():
    """Ver estadísticas rápidas"""
    print("🔍 Obteniendo estadísticas rápidas...")
    cmd = ["python", "test_reports.py"]
    subprocess.run(cmd)

def show_help():
    """Mostrar ayuda completa"""
    print("❓ AYUDA COMPLETA")
    print("=" * 30)
    print()
    print("📊 Scripts disponibles:")
    print("• simple_report.py    - Reportes rápidos y simples")
    print("• generate_call_report.py - Reportes completos con filtros")
    print("• test_reports.py     - Verificar conexión y estadísticas")
    print()
    print("🎯 Ejemplos de uso directo:")
    print("python simple_report.py --days 7")
    print("python generate_call_report.py --account-id cuenta123")
    print("python generate_call_report.py --start-date 2025-09-01")
    print()
    print("📋 Los reportes incluyen:")
    print("• Información completa de contactos")
    print("• Estados y resultados de llamadas")
    print("• Transcripciones y grabaciones")
    print("• Costos y duraciones")
    print("• Variables capturadas")
    print("• Estadísticas de éxito")
    print()
    print("📁 Archivos generados:")
    print("• reporte_*.xlsx - Archivo principal")
    print("• Hoja 'Llamadas' - Datos detallados")
    print("• Hoja 'Resumen' - Estadísticas agregadas")
    print()

def main():
    """Función principal con menú interactivo"""
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("app"):
        print("❌ Error: Ejecutar desde el directorio raíz del proyecto")
        print("Debe contener la carpeta 'app/'")
        return
    
    # Verificar dependencias
    try:
        import pandas as pd
        import openpyxl
    except ImportError:
        print("❌ Dependencias faltantes. Instalar con:")
        print("pip install pandas openpyxl")
        return
    
    while True:
        try:
            show_menu()
            choice = input("Selecciona una opción (0-7): ").strip()
            
            if choice == "0":
                print("👋 ¡Hasta luego!")
                break
            elif choice == "1":
                quick_report()
            elif choice == "2":
                custom_days_report()
            elif choice == "3":
                account_report()
            elif choice == "4":
                batch_report()
            elif choice == "5":
                date_range_report()
            elif choice == "6":
                quick_stats()
            elif choice == "7":
                show_help()
            else:
                print("❌ Opción no válida. Elige entre 0-7.")
            
            input("\nPresiona Enter para continuar...")
            print("\n" * 2)  # Limpiar pantalla
            
        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()