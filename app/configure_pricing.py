"""
Configurador de costos por cuenta - Permite personalizar precios por cliente
"""
import os
from pymongo import MongoClient
from datetime import datetime, timezone

# Configuración MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "Debtors")

def configure_account_pricing(account_id: str, pricing_config: dict):
    """
    Configura precios específicos para una cuenta
    """
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    # Validar configuración
    valid_fields = [
        'cost_per_call_setup',
        'cost_per_minute', 
        'cost_failed_call',
        'plan_type',
        'credit_balance',
        'minutes_remaining'
    ]
    
    update_data = {}
    for field, value in pricing_config.items():
        if field in valid_fields:
            update_data[field] = value
        else:
            print(f"⚠️ Campo ignorado: {field}")
    
    # Agregar timestamp
    update_data['updated_at'] = datetime.now(timezone.utc)
    
    # Actualizar cuenta
    result = db.accounts.update_one(
        {"account_id": account_id},
        {"$set": update_data},
        upsert=True
    )
    
    if result.upserted_id:
        print(f"✅ Cuenta creada: {account_id}")
    else:
        print(f"✅ Cuenta actualizada: {account_id}")
    
    print(f"📊 Configuración aplicada:")
    for field, value in update_data.items():
        if field != 'updated_at':
            if 'cost' in field:
                print(f"   💰 {field}: ${value:.3f}")
            else:
                print(f"   ⚙️ {field}: {value}")
    
    client.close()

def show_pricing_examples():
    """Muestra ejemplos de configuraciones de precios"""
    
    print("🎯 EJEMPLOS DE CONFIGURACIONES DE PRECIOS")
    print("=" * 50)
    
    examples = [
        {
            "name": "🏢 EMPRESA PEQUEÑA",
            "account_id": "pequeña_empresa",
            "config": {
                "plan_type": "credit_based",
                "cost_per_call_setup": 0.02,  # 2 centavos por llamada
                "cost_per_minute": 0.10,      # 10 centavos por minuto
                "cost_failed_call": 0.005,    # 0.5 centavos por falla
                "credit_balance": 25.00        # $25 USD iniciales
            }
        },
        {
            "name": "🏭 EMPRESA MEDIANA", 
            "account_id": "mediana_empresa",
            "config": {
                "plan_type": "credit_based", 
                "cost_per_call_setup": 0.015, # 1.5 centavos (descuento)
                "cost_per_minute": 0.08,      # 8 centavos (descuento)
                "cost_failed_call": 0.003,    # 0.3 centavos
                "credit_balance": 100.00       # $100 USD iniciales
            }
        },
        {
            "name": "🏢 EMPRESA GRANDE",
            "account_id": "gran_empresa", 
            "config": {
                "plan_type": "credit_based",
                "cost_per_call_setup": 0.01,  # 1 centavo (gran descuento)
                "cost_per_minute": 0.05,      # 5 centavos (gran descuento) 
                "cost_failed_call": 0.001,    # 0.1 centavos
                "credit_balance": 500.00       # $500 USD iniciales
            }
        },
        {
            "name": "⭐ PLAN MINUTOS",
            "account_id": "plan_minutos",
            "config": {
                "plan_type": "minutes_based",
                "minutes_remaining": 200,      # 200 minutos incluidos
                "cost_per_call_setup": 0.0,   # Sin costo de setup 
                "cost_per_minute": 1.0,       # 1 minuto = 1 minuto
                "cost_failed_call": 0.0       # Sin costo por fallas
            }
        }
    ]
    
    for example in examples:
        print(f"\n{example['name']}")
        print(f"Account ID: {example['account_id']}")
        
        config = example['config']
        plan = config['plan_type']
        
        if plan == 'credit_based':
            setup_cost = config['cost_per_call_setup']
            minute_cost = config['cost_per_minute']
            balance = config['credit_balance']
            
            # Calcular costo de llamada de 3 minutos
            call_cost = setup_cost + (3 * minute_cost)
            max_calls = int(balance // call_cost)
            
            print(f"  💳 Balance inicial: ${balance:.2f}")
            print(f"  📞 Costo por llamada (3min): ${call_cost:.3f}")
            print(f"  📊 Llamadas posibles: {max_calls}")
            
        elif plan == 'minutes_based':
            minutes = config['minutes_remaining']
            print(f"  ⏱️ Minutos incluidos: {minutes}")
            print(f"  📞 Llamadas posibles (3min c/u): {minutes // 3}")
        
        print(f"  ⚙️ Para aplicar: configure_pricing('{example['account_id']}')")

def configure_pricing(account_id: str):
    """Configurador interactivo de precios"""
    print(f"\n🎛️ CONFIGURANDO PRECIOS PARA: {account_id}")
    print("-" * 40)
    
    # Preguntar tipo de plan
    print("1. Plan basado en créditos (credit_based)")
    print("2. Plan basado en minutos (minutes_based)")
    print("3. Plan ilimitado (unlimited)")
    
    while True:
        choice = input("Selecciona tipo de plan (1-3): ")
        if choice in ['1', '2', '3']:
            break
        print("⚠️ Opción inválida")
    
    config = {}
    
    if choice == '1':  # Credit based
        config['plan_type'] = 'credit_based'
        
        print("\n💰 CONFIGURACIÓN DE COSTOS:")
        config['cost_per_call_setup'] = float(input("Costo por iniciar llamada (USD): "))
        config['cost_per_minute'] = float(input("Costo por minuto (USD): "))
        config['cost_failed_call'] = float(input("Costo por llamada fallida (USD): "))
        config['credit_balance'] = float(input("Balance inicial de créditos (USD): "))
        
    elif choice == '2':  # Minutes based
        config['plan_type'] = 'minutes_based'
        config['minutes_remaining'] = int(input("Minutos incluidos: "))
        config['cost_per_call_setup'] = 0.0
        config['cost_per_minute'] = 1.0  # 1 minuto = 1 minuto
        config['cost_failed_call'] = 0.0
        
    elif choice == '3':  # Unlimited
        config['plan_type'] = 'unlimited'
        config['cost_per_call_setup'] = 0.0
        config['cost_per_minute'] = 0.0
        config['cost_failed_call'] = 0.0
    
    # Aplicar configuración
    configure_account_pricing(account_id, config)
    
def list_current_accounts():
    """Lista cuentas existentes con su configuración de precios"""
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    
    print("\n📋 CUENTAS EXISTENTES:")
    print("=" * 50)
    
    accounts = db.accounts.find({})
    
    for account in accounts:
        account_id = account.get('account_id', 'Unknown')
        plan_type = account.get('plan_type', 'Unknown')
        
        print(f"\n👤 {account_id}")
        print(f"   📋 Plan: {plan_type}")
        
        if plan_type == 'credit_based':
            setup = account.get('cost_per_call_setup', 0)
            minute = account.get('cost_per_minute', 0)
            balance = account.get('credit_balance', 0)
            
            print(f"   💰 Setup: ${setup:.3f}")
            print(f"   ⏱️ Por minuto: ${minute:.3f}")
            print(f"   💳 Balance: ${balance:.2f}")
            
        elif plan_type == 'minutes_based':
            minutes = account.get('minutes_remaining', 0)
            print(f"   ⏱️ Minutos restantes: {minutes}")
            
        elif plan_type == 'unlimited':
            print(f"   ♾️ Sin límites")
    
    client.close()

if __name__ == "__main__":
    print("🎛️ CONFIGURADOR DE COSTOS SAAS")
    print("=" * 40)
    
    while True:
        print("\n📋 OPCIONES:")
        print("1. Ver ejemplos de configuraciones")
        print("2. Configurar precios para una cuenta")
        print("3. Listar cuentas existentes")
        print("4. Salir")
        
        choice = input("\nSelecciona opción (1-4): ")
        
        if choice == '1':
            show_pricing_examples()
        elif choice == '2':
            account_id = input("Account ID: ")
            configure_pricing(account_id)
        elif choice == '3':
            list_current_accounts()
        elif choice == '4':
            print("👋 ¡Hasta luego!")
            break
        else:
            print("⚠️ Opción inválida")