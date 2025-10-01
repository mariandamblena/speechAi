#!/usr/bin/env python3
"""
Test script para verificar la normalización de teléfonos argentinos
"""

import re

def _norm_ar_phone(phone_number):
    """
    Normaliza números telefónicos argentinos al formato internacional +54
    
    Formatos soportados:
    - 5491136530246 → +5491136530246
    - 1136530246 → +5491136530246 (Buenos Aires móvil)
    - 011-3653-0246 → +541136530246 (Buenos Aires fijo)
    - 15-3653-0246 → +5491136530246 (móvil con 15)
    """
    if not phone_number:
        return None
    
    # Limpiar el número: solo dígitos
    clean_phone = re.sub(r'[^\d]', '', str(phone_number))
    
    # Si ya tiene código de país argentino completo
    if clean_phone.startswith('54'):
        # Si ya está completo, solo agregar el +
        if len(clean_phone) >= 12:  # 54 + 9 + área + número
            return f"+{clean_phone}"
    
    # Casos específicos argentinos
    if clean_phone.startswith('11') and len(clean_phone) == 10:
        # Buenos Aires móvil: 1136530246 → +5491136530246
        return f"+549{clean_phone}"
    
    if clean_phone.startswith('011') and len(clean_phone) == 11:
        # Buenos Aires fijo: 01136530246 → +541136530246
        return f"+54{clean_phone[1:]}"  # Quitar el primer 0
    
    if clean_phone.startswith('15') and len(clean_phone) >= 10:
        # Móvil con 15: 1536530246 → +54915...
        area_and_number = clean_phone[2:]  # Quitar 15
        if len(area_and_number) >= 8:
            return f"+549{area_and_number}"
    
    # Si empieza con 9 (ya procesado para móvil)
    if clean_phone.startswith('9') and len(clean_phone) >= 11:
        return f"+54{clean_phone}"
    
    # Números de 8-10 dígitos (asumir que necesitan código de país)
    if 8 <= len(clean_phone) <= 10:
        # Si parece Buenos Aires (empieza con 11)
        if clean_phone.startswith('11'):
            return f"+549{clean_phone}"
        else:
            # Otras áreas, asumir móvil
            return f"+549{clean_phone}"
    
    # Si no encaja en ningún patrón, devolver con +54
    return f"+54{clean_phone}"

def test_phone_normalization():
    """Probar la normalización de números argentinos"""
    
    # Números de prueba
    test_phones = [
        "5491136530246",  # El número del usuario
        "1136530246",     # Sin código de país
        "9 11 3653 0246", # Con espacios
        "011-3653-0246",  # Con formato tradicional
        "+54 9 11 3653 0246", # Ya con código de país
        "54 9 11 3653 0246",  # Sin + inicial
        "15-3653-0246",   # Formato móvil común
    ]
    
    print("🇦🇷 PRUEBA DE NORMALIZACIÓN DE TELÉFONOS ARGENTINOS")
    print("=" * 60)
    
    for phone in test_phones:
        try:
            normalized = _norm_ar_phone(phone)
            print(f"📞 {phone:20} → {normalized}")
        except Exception as e:
            print(f"❌ {phone:20} → ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Prueba completada")

if __name__ == "__main__":
    test_phone_normalization()