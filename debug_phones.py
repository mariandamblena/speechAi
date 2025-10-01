#!/usr/bin/env python3
"""
Script para diagnosticar y normalizar teléfonos chilenos
"""

import json
import re

def normalize_chilean_phone(raw_phone):
    """Normaliza teléfono chileno según la lógica del sistema"""
    if not raw_phone:
        return None, "Empty phone"
    
    # Limpiar y extraer solo dígitos
    clean = re.sub(r'[^\d]', '', str(raw_phone))
    
    # Remover código país si está presente
    if clean.startswith('56'):
        clean = clean[2:]
    
    # Remover ceros iniciales
    clean = clean.lstrip('0')
    
    # Validar largo
    if len(clean) != 9:
        return None, f"Invalid length: {len(clean)} (expected 9)"
    
    # Validar formato móvil/fijo
    if clean[0] == '9':
        # Móvil válido
        return f"+56{clean}", "Mobile OK"
    elif clean[0] == '2':
        # Fijo válido (Santiago)
        return f"+56{clean}", "Landline OK"
    else:
        return None, f"Invalid prefix: {clean[0]} (expected 9 for mobile or 2 for landline)"

def analyze_phones_in_json(file_path):
    """Analiza teléfonos en un archivo JSON"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        phones_found = []
        
        # Buscar teléfonos en diferentes campos
        if isinstance(data, list):
            for item in data:
                phones = extract_phones_from_item(item)
                phones_found.extend(phones)
        else:
            phones = extract_phones_from_item(data)
            phones_found.extend(phones)
        
        # Analizar cada teléfono
        print("📞 ANÁLISIS DE TELÉFONOS")
        print("=" * 50)
        
        valid_count = 0
        invalid_count = 0
        
        for original, source in phones_found:
            normalized, status = normalize_chilean_phone(original)
            
            if normalized:
                print(f"✅ {original} -> {normalized} ({status}) [from: {source}]")
                valid_count += 1
            else:
                print(f"❌ {original} -> ERROR: {status} [from: {source}]")
                invalid_count += 1
        
        print("\n📊 RESUMEN")
        print(f"Total teléfonos: {len(phones_found)}")
        print(f"Válidos: {valid_count}")
        print(f"Inválidos: {invalid_count}")
        print(f"Tasa de éxito: {(valid_count/len(phones_found)*100):.1f}%" if phones_found else "0%")
        
        return phones_found
        
    except Exception as e:
        print(f"Error leyendo archivo: {e}")
        return []

def extract_phones_from_item(item, path=""):
    """Extrae teléfonos de un objeto JSON recursivamente"""
    phones = []
    
    if isinstance(item, dict):
        for key, value in item.items():
            current_path = f"{path}.{key}" if path else key
            
            # Campos que típicamente contienen teléfonos
            if any(phone_field in key.lower() for phone_field in ['phone', 'telefono', 'to_number', 'mobile', 'celular', 'landline', 'fijo']):
                if value and str(value).strip():
                    phones.append((str(value).strip(), current_path))
            
            # Buscar recursivamente
            if isinstance(value, (dict, list)):
                phones.extend(extract_phones_from_item(value, current_path))
    
    elif isinstance(item, list):
        for i, sub_item in enumerate(item):
            current_path = f"{path}[{i}]" if path else f"[{i}]"
            phones.extend(extract_phones_from_item(sub_item, current_path))
    
    return phones

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Uso: python debug_phones.py <archivo.json>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    analyze_phones_in_json(file_path)