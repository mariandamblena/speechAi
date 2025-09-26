"""
Generador de archivo Excel de ejemplo para pruebas
"""

import pandas as pd
from datetime import datetime, timedelta
import random

def generate_sample_excel(filename: str = "ejemplo_deudores.xlsx"):
    """Genera un archivo Excel de ejemplo con datos realistas chilenos"""
    
    # Datos de ejemplo
    nombres = [
        "Juan Carlos Pérez Silva", "María Alejandra González López", "Carlos Eduardo Rodríguez Méndez",
        "Ana Patricia Martínez Vega", "José Luis Hernández Torres", "Carmen Rosa Jiménez Morales",
        "Miguel Ángel Vargas Soto", "Lucía Fernanda Castro Ruiz", "Roberto Antonio Moreno Díaz",
        "Valentina Isidora Muñoz Araya", "Francisco Javier Rojas Peña", "Claudia Beatriz Espinoza Núñez",
        "Diego Alejandro Fuentes Campos", "Esperanza del Carmen Poblete Guzmán", "Andrés Felipe Contreras Pizarro"
    ]
    
    empresas = [
        "BANCO DE CHILE", "BANCO SANTANDER", "BANCO ESTADO", "FALABELLA",
        "RIPLEY", "LA POLAR", "CENCOSUD", "BANCO SECURITY"
    ]
    
    # Generar RUTs chilenos válidos (aproximados)
    def generate_rut():
        num = random.randint(5000000, 25000000)
        # Cálculo simplificado del dígito verificador
        dv_calc = 11 - (sum((2 + i % 6) * int(d) for i, d in enumerate(str(num)[::-1])) % 11)
        if dv_calc == 11:
            dv = '0'
        elif dv_calc == 10:
            dv = 'K'
        else:
            dv = str(dv_calc)
        return f"{num}-{dv}"
    
    # Generar teléfonos chilenos
    def generate_mobile():
        formats = [
            f"+56 9 {random.randint(1000, 9999)} {random.randint(1000, 9999)}",
            f"09-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}",
            f"569{random.randint(10000000, 99999999)}",
            f"9{random.randint(1000, 9999)}{random.randint(1000, 9999)}"
        ]
        return random.choice(formats)
    
    def generate_landline():
        area_codes = ['02', '032', '033', '034', '041', '042', '043', '045', '051', '052', '055', '057', '058', '061', '063', '064', '065', '067']
        area = random.choice(area_codes)
        if area == '02':  # Santiago
            formats = [
                f"{area}-{random.randint(200, 999)}-{random.randint(1000, 9999)}",
                f"2{random.randint(2000000, 9999999)}",
                f"02 {random.randint(200, 999)} {random.randint(1000, 9999)}"
            ]
        else:
            formats = [
                f"{area}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                f"{area} {random.randint(100, 999)} {random.randint(1000, 9999)}"
            ]
        return random.choice(formats)
    
    # Generar fechas de vencimiento
    def generate_venc_date():
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now() - timedelta(days=30)
        time_between = end_date - start_date
        days_between = time_between.days
        random_days = random.randrange(days_between)
        date = start_date + timedelta(days=random_days)
        return date.strftime("%d/%m/%Y")
    
    # Generar datos
    data = []
    
    # Algunos deudores con múltiples deudas (mismo RUT)
    base_debtors = []
    for i in range(12):  # 12 personas base
        rut = generate_rut()
        nombre = random.choice(nombres)
        empresa = random.choice(empresas)
        mobile = generate_mobile() if random.random() > 0.1 else ""  # 90% tienen móvil
        landline = generate_landline() if random.random() > 0.3 else ""  # 70% tienen fijo
        
        base_debtors.append({
            'rut': rut,
            'nombre': nombre,
            'empresa': empresa,
            'mobile': mobile,
            'landline': landline
        })
    
    # Generar hasta 25 deudas (algunas personas con múltiples deudas)
    for i in range(25):
        if i < 12:  # Primeras 12 son personas únicas
            debtor = base_debtors[i].copy()
        else:  # Las siguientes pueden repetir personas
            debtor = random.choice(base_debtors[:8]).copy()  # Solo los primeros 8 pueden tener múltiples deudas
        
        # Formatear RUT con variaciones
        rut_formats = [
            debtor['rut'],  # Con formato
            debtor['rut'].replace('-', '').replace('.', ''),  # Sin formato
            debtor['rut'].replace('-', '').replace('.', '').replace('', '').strip()  # Limpio
        ]
        
        saldo = random.randint(50000, 5000000)  # Entre $50k y $5M
        saldo_format = random.choice([
            f"{saldo:,}".replace(',', '.'),  # Formato chileno: 1.250.000
            f"{saldo:,}.00".replace(',', '.'),  # Con decimales: 1.250.000.00  
            str(saldo),  # Sin formato
            f"${saldo:,}".replace(',', '.')  # Con símbolo peso
        ])
        
        row = {
            'RUT': random.choice(rut_formats),
            'Nombre': debtor['nombre'],
            'Origen Empresa': debtor['empresa'],
            'Saldo actualizado': saldo_format,
            'FechaVencimiento': generate_venc_date(),
            'diasRetraso': random.randint(0, 180),
            'Teléfono móvil': debtor['mobile'],
            'Teléfono Residencial': debtor['landline']
        }
        
        data.append(row)
    
    # Crear DataFrame y Excel
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    
    print(f"Archivo '{filename}' generado con {len(data)} registros")
    print(f"Deudores únicos: {len(set(row['RUT'] for row in data))}")
    print(f"Con teléfono móvil: {sum(1 for row in data if row['Teléfono móvil'])}")
    print(f"Con teléfono fijo: {sum(1 for row in data if row['Teléfono Residencial'])}")
    
    # Mostrar primeros 3 registros
    print("\nPrimeros registros:")
    print(df.head(3).to_string())


if __name__ == "__main__":
    generate_sample_excel("ejemplo_deudores_chile.xlsx")