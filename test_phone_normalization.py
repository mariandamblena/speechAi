#!/usr/bin/env python3
"""
Prueba rápida de normalización de teléfonos argentinos
"""

import re

def _norm_ar_phone(phone):
    """Normalizar número de teléfono argentino al formato +54"""
    if not phone:
        return ''
    
    # Convertir a string y limpiar
    phone_str = str(phone).strip()
    
    # Si ya tiene +54, verificar formato
    if phone_str.startswith('+54'):
        return phone_str
    
    # Si empieza con 54, agregar +
    if phone_str.startswith('54'):
        return '+' + phone_str
    
    # Limpiar caracteres no numéricos
    clean_phone = re.sub(r'[^\d]', '', phone_str)
    
    # Si empieza con 0, quitarlo (formato local)
    if clean_phone.startswith('0'):
        clean_phone = clean_phone[1:]
    
    # Casos para Buenos Aires (área 11) con código móvil
    if clean_phone.startswith('11'):
        # 11-1234-5678 → 5491112345678
        if len(clean_phone) == 10:
            return '+549' + clean_phone
    
    # Caso móvil directo: 91112345678
    if clean_phone.startswith('9') and len(clean_phone) == 11:
        return '+54' + clean_phone
    
    # Caso sin 9: agregar código móvil
    if len(clean_phone) == 10 and clean_phone.startswith('11'):
        return '+549' + clean_phone
    
    # Caso completo sin +: 5491112345678
    if len(clean_phone) == 13 and clean_phone.startswith('549'):
        return '+' + clean_phone
    
    # Si no cumple ningún patrón, devolver con +54
    return '+54' + clean_phone

if __name__ == "__main__":
    # Probar números
    test_phones = [
        '5491136530246',    # Tu número específico
        '11-3653-0246',     # Formato con guiones
        '1136530246',       # Sin código de país
        '91136530246',      # Con 9 móvil
        '+5491136530246'    # Ya normalizado
    ]

    print("🇦🇷 Prueba de normalización de teléfonos argentinos")
    print("=" * 50)
    
    for phone in test_phones:
        normalized = _norm_ar_phone(phone)
        print(f'{phone:15} → {normalized}')
    
    print("\n✅ Tu número 5491136530246 queda normalizado como:")
    print(f"   {_norm_ar_phone('5491136530246')}")