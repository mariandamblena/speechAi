"""
Script de diagnóstico para problemas con carga de Excel
Identifica problemas comunes en el procesamiento de archivos
"""
import pandas as pd
import os
from datetime import datetime
import sys

# Agregar el path del app al Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from utils.excel_processor import ExcelDebtorProcessor

def diagnose_excel_file(file_path: str):
    """Diagnostica un archivo Excel para identificar problemas"""
    
    print("🔍 DIAGNÓSTICO DEL ARCHIVO EXCEL")
    print("=" * 50)
    
    # 1. Verificar que el archivo existe
    if not os.path.exists(file_path):
        print(f"❌ ERROR: Archivo no encontrado: {file_path}")
        return
    
    print(f"✅ Archivo encontrado: {file_path}")
    
    try:
        # 2. Leer el archivo Excel
        df = pd.read_excel(file_path)
        print(f"✅ Excel leído correctamente")
        print(f"📊 Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
        
        # 3. Mostrar columnas disponibles
        print(f"\n📋 COLUMNAS ENCONTRADAS:")
        for i, col in enumerate(df.columns, 1):
            print(f"   {i:2}. '{col}'")
        
        # 4. Verificar columnas críticas
        print(f"\n🔍 VERIFICACIÓN DE COLUMNAS CRÍTICAS:")
        
        processor = ExcelDebtorProcessor()
        critical_fields = {
            'RUT': ['RUTS', 'RUT', 'Rut'],
            'Nombre': ['Nombre', 'nombre'],
            'Saldo': ['Saldo actualizado', 'Saldo Actualizado', ' Saldo actualizado ', 'saldo'],
            'Teléfono móvil': ['Teléfono móvil', 'Telefono movil', 'Teléfono celular', 'Celular'],
            'Teléfono fijo': ['Teléfono Residencial', 'Telefono residencial', 'Teléfono fijo', 'Telefono fijo']
        }
        
        for field_name, variants in critical_fields.items():
            found = False
            for variant in variants:
                if variant in df.columns:
                    print(f"   ✅ {field_name}: Encontrado como '{variant}'")
                    found = True
                    break
            
            if not found:
                print(f"   ❌ {field_name}: NO ENCONTRADO (buscaba: {variants})")
        
        # 5. Mostrar muestra de datos
        print(f"\n📋 MUESTRA DE DATOS (primeras 3 filas):")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        print(df.head(3).to_string())
        
        # 6. Verificar datos vacíos
        print(f"\n🔍 ANÁLISIS DE DATOS VACÍOS:")
        for col in df.columns:
            null_count = df[col].isnull().sum()
            empty_count = (df[col] == '').sum() if df[col].dtype == 'object' else 0
            total_empty = null_count + empty_count
            
            if total_empty > 0:
                percentage = (total_empty / len(df)) * 100
                print(f"   ⚠️ '{col}': {total_empty}/{len(df)} vacíos ({percentage:.1f}%)")
        
        # 7. Simular procesamiento
        print(f"\n🧪 SIMULANDO PROCESAMIENTO:")
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            result = processor.process_excel_data(file_content, "test_account")
            
            debtors = result['debtors']
            print(f"✅ Procesamiento exitoso:")
            print(f"   📊 Batch ID: {result['batch_id']}")
            print(f"   📊 Deudores procesados: {len(debtors)}")
            
            if debtors:
                print(f"\n📋 PRIMER DEUDOR PROCESADO:")
                first_debtor = debtors[0]
                for key, value in first_debtor.items():
                    print(f"   📄 {key}: {value}")
            else:
                print("❌ No se procesaron deudores - archivo vacío o formato incorrecto")
        
        except Exception as e:
            print(f"❌ ERROR en procesamiento: {str(e)}")
            import traceback
            print("Stack trace:")
            traceback.print_exc()
    
    except Exception as e:
        print(f"❌ ERROR leyendo Excel: {str(e)}")
        import traceback
        print("Stack trace:")
        traceback.print_exc()

def get_sample_excel_structure():
    """Muestra la estructura esperada del Excel"""
    
    print(f"\n📋 ESTRUCTURA ESPERADA DEL EXCEL:")
    print("=" * 50)
    
    expected_columns = [
        "RUTS (o RUT, Rut)",
        "Nombre",
        "Saldo actualizado (o saldo)",
        "Teléfono móvil (o Celular)",
        "Teléfono Residencial (opcional)",
        "Origen Empresa (opcional)",
        "FechaVencimiento (opcional)",
        "diasRetraso (opcional)"
    ]
    
    for i, col in enumerate(expected_columns, 1):
        print(f"   {i}. {col}")
    
    print(f"\n💡 CONSEJOS:")
    print(f"   • Las columnas pueden tener nombres similares")
    print(f"   • El RUT debe estar sin puntos ni guiones")
    print(f"   • Los teléfonos pueden incluir +56 o códigos de área")
    print(f"   • El saldo debe ser numérico (puede incluir $ y puntos)")

if __name__ == "__main__":
    print("🔧 HERRAMIENTA DE DIAGNÓSTICO EXCEL")
    print("=" * 60)
    
    # Usar archivo por defecto si no se proporciona
    default_file = "chile_usuarios (2).xlsx"
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_file
        print(f"💡 Usando archivo por defecto: {file_path}")
        print(f"   Para usar otro archivo: python excel_diagnosis.py <ruta_archivo>")
    
    print()
    diagnose_excel_file(file_path)
    get_sample_excel_structure()