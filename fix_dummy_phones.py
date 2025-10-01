#!/usr/bin/env python3
"""
Script para reemplazar números dummy con números válidos en el JSON
"""

import json
import re

def replace_dummy_phones(file_path, output_path=None):
    """Reemplaza números dummy con números válidos para testing"""
    
    # Número válido que sabemos que funciona
    VALID_TEST_NUMBER = "+5491136530246"
    
    # Patrones de números dummy a reemplazar
    DUMMY_PATTERNS = [
        r'\+5491111110\d{3}',  # +5491111110XXX
        r'\+549111111\d{4}',   # +549111111XXXX
        r'\+54911111\d{5}',    # +54911111XXXXX
    ]
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        replacements_made = 0
        
        # Reemplazar cada patrón dummy
        for pattern in DUMMY_PATTERNS:
            matches = re.findall(pattern, content)
            replacements_made += len(matches)
            content = re.sub(pattern, VALID_TEST_NUMBER, content)
        
        # Guardar resultado
        output_file = output_path or file_path.replace('.json', '_fixed.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ Procesamiento completado:")
        print(f"   📁 Archivo original: {file_path}")
        print(f"   📁 Archivo corregido: {output_file}")
        print(f"   🔄 Reemplazos realizados: {replacements_made}")
        print(f"   📞 Número usado para testing: {VALID_TEST_NUMBER}")
        
        # Mostrar algunos ejemplos de cambios
        if replacements_made > 0:
            print(f"\n🔍 Ejemplos de números reemplazados:")
            for pattern in DUMMY_PATTERNS:
                dummy_matches = re.findall(pattern, original_content)
                if dummy_matches:
                    for dummy in set(dummy_matches[:3]):  # Mostrar máximo 3 ejemplos
                        print(f"   ❌ {dummy} -> ✅ {VALID_TEST_NUMBER}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error procesando archivo: {e}")
        return None

def validate_fixed_json(file_path):
    """Valida que el JSON corregido esté bien formado"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ JSON válido: {len(data) if isinstance(data, list) else 1} registros")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python fix_dummy_phones.py <archivo.json> [archivo_salida.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("🔧 REPARADOR DE NÚMEROS DUMMY")
    print("=" * 40)
    
    # Procesar archivo
    fixed_file = replace_dummy_phones(input_file, output_file)
    
    if fixed_file:
        # Validar resultado
        print("\n🔍 Validando archivo corregido...")
        if validate_fixed_json(fixed_file):
            print(f"\n🎉 ¡Listo! Usa el archivo: {fixed_file}")
        else:
            print("\n⚠️ Hay errores en el archivo corregido")
    else:
        print("\n❌ No se pudo procesar el archivo")