#!/usr/bin/env python3
"""
Script simple para generar reportes rápidos de llamadas
Versión simplificada para uso cotidiano
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
import pandas as pd

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from infrastructure.database_manager import DatabaseManager
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), 'app', '.env'))

async def generate_simple_report(days_back: int = 7, output_file: str = None):
    """
    Generar reporte simple de los últimos días
    
    Args:
        days_back: Días hacia atrás para incluir en el reporte
        output_file: Nombre del archivo de salida
    """
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"reporte_llamadas_{timestamp}.xlsx"
    
    print(f"📊 Generando reporte de los últimos {days_back} días...")
    
    # Conectar a la base de datos
    db_manager = DatabaseManager(
        connection_string=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        database_name=os.getenv("MONGO_DB", "speechai_db")
    )
    await db_manager.connect()
    
    try:
        # Calcular fechas
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back)
        
        # Query para obtener jobs recientes
        collection = db_manager.get_collection("jobs")
        query = {
            "created_at": {
                "$gte": start_date,
                "$lte": end_date
            }
        }
        
        cursor = collection.find(query).sort("created_at", -1)
        
        # Procesar datos
        calls_data = []
        async for doc in cursor:
            call_data = {
                "Fecha": doc.get("created_at", "").strftime("%Y-%m-%d %H:%M") if doc.get("created_at") else "",
                "Job ID": str(doc.get("_id", "")),
                "Cuenta": doc.get("account_id", ""),
                "Batch": doc.get("batch_id", ""),
                "Nombre": doc.get("nombre", ""),
                "RUT": doc.get("rut", ""),
                "Teléfono": doc.get("to_number", ""),
                "Estado": doc.get("status", ""),
                "Deuda": doc.get("deuda", 0),
            }
            
            # Información de la llamada si existe
            call_result = doc.get("call_result", {})
            if call_result:
                summary = call_result.get("summary", {})
                call_data.update({
                    "Duración (min)": round(doc.get("call_duration_seconds", 0) / 60, 2),
                    "Éxito": call_result.get("success", False),
                    "Estado Llamada": call_result.get("status", ""),
                    "Costo USD": summary.get("call_cost", {}).get("combined_cost", 0) if isinstance(summary.get("call_cost"), dict) else summary.get("call_cost", 0),
                    "URL Grabación": summary.get("recording_url", ""),
                    "Motivo Desconexión": summary.get("disconnection_reason", ""),
                })
                
                # Variables capturadas
                vars_captured = summary.get("collected_dynamic_variables", {})
                call_data.update({
                    "Fecha Pago Prometida": vars_captured.get("fecha_pago_cliente", ""),
                    "Monto Pago Prometido": vars_captured.get("monto_pago_cliente", ""),
                })
            else:
                call_data.update({
                    "Duración (min)": 0,
                    "Éxito": False,
                    "Estado Llamada": "No iniciada",
                    "Costo USD": 0,
                    "URL Grabación": "",
                    "Motivo Desconexión": "",
                    "Fecha Pago Prometida": "",
                    "Monto Pago Prometido": "",
                })
            
            calls_data.append(call_data)
        
        # Crear DataFrame y exportar
        df = pd.DataFrame(calls_data)
        
        if df.empty:
            print("⚠️ No se encontraron llamadas en el período especificado")
            return
        
        # Exportar a Excel
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Hoja principal
            df.to_excel(writer, sheet_name='Llamadas', index=False)
            
            # Hoja de resumen
            summary_data = {
                "Métrica": [
                    "Total Llamadas",
                    "Llamadas Exitosas", 
                    "Llamadas Fallidas",
                    "Tasa de Éxito (%)",
                    "Costo Total (USD)",
                    "Tiempo Total (min)"
                ],
                "Valor": [
                    len(df),
                    len(df[df["Éxito"] == True]),
                    len(df[df["Éxito"] == False]),
                    round(len(df[df["Éxito"] == True]) / len(df) * 100, 1) if len(df) > 0 else 0,
                    round(df["Costo USD"].sum(), 2),
                    round(df["Duración (min)"].sum(), 2)
                ]
            }
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Resumen', index=False)
        
        print(f"✅ Reporte generado: {output_file}")
        print(f"📊 Total llamadas: {len(df)}")
        print(f"🎯 Tasa éxito: {round(len(df[df['Éxito'] == True]) / len(df) * 100, 1)}%" if len(df) > 0 else "N/A")
        print(f"💰 Costo total: ${round(df['Costo USD'].sum(), 2)} USD")
        
    finally:
        await db_manager.close()

def main():
    """Función principal con interfaz simple"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Generador simple de reportes")
    parser.add_argument("--days", type=int, default=7, help="Días hacia atrás (default: 7)")
    parser.add_argument("--output", help="Nombre del archivo de salida")
    parser.add_argument("--interactive", action="store_true", help="Modo interactivo")
    
    args = parser.parse_args()
    
    print("🚀 Generador de Reportes de Llamadas")
    print("=" * 40)
    
    # Verificar dependencias
    try:
        import pandas as pd
        import openpyxl
    except ImportError:
        print("❌ Instalar dependencias:")
        print("pip install pandas openpyxl")
        return
    
    days = args.days
    filename = args.output
    
    # Modo interactivo si se solicita
    if args.interactive:
        try:
            days_input = input("📅 Días hacia atrás (default 7): ").strip()
            days = int(days_input) if days_input else 7
            
            filename_input = input("💾 Nombre archivo (Enter para auto): ").strip()
            filename = filename_input if filename_input else None
            
        except KeyboardInterrupt:
            print("\n👋 Cancelado por el usuario")
            return
        except Exception as e:
            print(f"❌ Error en entrada: {e}")
            return
    
    # Generar nombre automático si no se especifica
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reporte_llamadas_{timestamp}.xlsx"
    
    if not filename.endswith('.xlsx'):
        filename += '.xlsx'
    
    print(f"\n📊 Generando reporte de {days} días...")
    print(f"💾 Archivo: {filename}")
    print("-" * 40)
    
    try:
        asyncio.run(generate_simple_report(days, filename))
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()