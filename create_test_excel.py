#!/usr/bin/env python3
"""
Convierte CSV a Excel para testing del endpoint argentino
"""

import pandas as pd

# Leer CSV
df = pd.read_csv('test_argentina.csv')

# Guardar como Excel
df.to_excel('test_argentina.xlsx', index=False)

print("✅ Archivo test_argentina.xlsx creado")
print("\nDatos incluidos:")
print(df.to_string())