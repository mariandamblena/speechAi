"""
Debug del problema de duplicados - Analiza por qué todos los deudores son marcados como duplicados
"""
import pandas as pd
import sys
import os
sys.path.append('app')

from utils.excel_processor import ExcelDebtorProcessor

def debug_duplicates_issue():
    """Analiza el problema específico de duplicados"""
    
    print("🔍 DEBUG: PROBLEMA DE DUPLICADOS")
    print("=" * 50)
    
    # 1. Leer el archivo Excel
    file_path = "docs/chile_usuarios.xlsx"
    
    try:
        # Leer con pandas para inspección
        df = pd.read_excel(file_path)
        print(f"✅ Archivo leído: {len(df)} filas")
        
        # 2. Verificar columna RUTS
        print(f"\n📋 ANÁLISIS DE RUTS:")
        ruts_column = 'RUTS'
        if ruts_column in df.columns:
            print(f"✅ Columna RUTS encontrada")
            
            # Mostrar primeros RUTs
            print(f"\n🔍 PRIMEROS 10 RUTS:")
            for i, rut in enumerate(df[ruts_column].head(10)):
                print(f"   {i+1:2}. '{rut}' (tipo: {type(rut)})")
            
            # Verificar duplicados reales
            unique_ruts = df[ruts_column].nunique()
            total_ruts = len(df[ruts_column].dropna())
            real_duplicates = total_ruts - unique_ruts
            
            print(f"\n📊 ESTADÍSTICAS DE RUTS:")
            print(f"   Total filas: {len(df)}")
            print(f"   RUTs no nulos: {total_ruts}")
            print(f"   RUTs únicos: {unique_ruts}")
            print(f"   Duplicados reales: {real_duplicates}")
            
            if real_duplicates > 0:
                print(f"\n🔍 ALGUNOS RUTS DUPLICADOS:")
                duplicated_ruts = df[df.duplicated(subset=[ruts_column], keep=False)][ruts_column]
                for rut in duplicated_ruts.value_counts().head(5).index:
                    count = duplicated_ruts.value_counts()[rut]
                    print(f"   RUT '{rut}' aparece {count} veces")
        
        # 3. Probar el procesador
        print(f"\n🧪 PROBANDO PROCESADOR:")
        processor = ExcelDebtorProcessor()
        
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Procesar datos
        result = processor.process_excel_data(file_content, "strasing")
        debtors = result['debtors']
        
        print(f"   Deudores procesados: {len(debtors)}")
        
        if len(debtors) > 0:
            print(f"\n📋 PRIMER DEUDOR PROCESADO:")
            first_debtor = debtors[0]
            for key, value in first_debtor.items():
                print(f"   {key}: {value}")
        
        # 4. Simular check de duplicados
        print(f"\n🔍 SIMULANDO CHECK DE DUPLICADOS:")
        
        # Simular lo que hace el servicio
        from services.batch_creation_service import BatchCreationService
        from infrastructure.database_manager import DatabaseManager
        from config.settings import get_settings
        import asyncio
        
        async def check_dups():
            settings = get_settings()
            db = DatabaseManager(settings.database.uri, settings.database.database)
            await db.connect()
            
            service = BatchCreationService(db)
            batch_id = result['batch_id']
            
            # Verificar duplicados
            duplicates = await service._check_duplicates(batch_id, debtors, "strasing")
            print(f"   Duplicados encontrados por el servicio: {len(duplicates)}")
            
            if duplicates:
                print(f"\n📋 PRIMEROS 5 DUPLICADOS:")
                for i, dup in enumerate(duplicates[:5]):
                    print(f"   {i+1}. RUT: {dup.get('rut', 'N/A')}, Razón: {dup.get('reason', 'N/A')}")
        
        asyncio.run(check_dups())
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_duplicates_issue()