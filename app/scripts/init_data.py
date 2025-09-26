"""
Script para inicializar datos de prueba en el sistema
Crea cuentas de ejemplo y datos de prueba
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Agregar la carpeta padre al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database_manager import DatabaseManager
from services.account_service import AccountService
from domain.enums import PlanType, AccountStatus
from config.settings import get_settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)

async def create_sample_accounts():
    """Crea cuentas de ejemplo para testing"""
    
    settings = get_settings()
    db_manager = DatabaseManager(settings.database.uri, settings.database.database)
    
    try:
        await db_manager.connect()
        account_service = AccountService(db_manager)
        
        # Cuenta basada en minutos
        print("Creating sample accounts...")
        
        account1 = await account_service.create_account(
            account_id="demo_minutes",
            account_name="Demo Account (Minutes)",
            plan_type=PlanType.MINUTES_BASED,
            initial_minutes=100.0,
            initial_credits=0.0
        )
        
        print(f"✅ Created account: {account1.account_id} with {account1.minutes_purchased} minutes")
        
        # Cuenta basada en créditos
        account2 = await account_service.create_account(
            account_id="demo_credits",
            account_name="Demo Account (Credits)",
            plan_type=PlanType.CREDIT_BASED,
            initial_minutes=0.0,
            initial_credits=50.0
        )
        
        print(f"✅ Created account: {account2.account_id} with ${account2.credit_balance} credits")
        
        # Cuenta premium
        account3 = await account_service.create_account(
            account_id="premium_client",
            account_name="Premium Client Corp",
            plan_type=PlanType.UNLIMITED,
            initial_minutes=0.0,
            initial_credits=0.0
        )
        
        print(f"✅ Created account: {account3.account_id} with unlimited plan")
        
        print("\n🎉 Sample accounts created successfully!")
        print("\nYou can now:")
        print("- Start the API: python -m uvicorn api:app --reload")
        print("- Test endpoints with these account_ids:")
        print("  * demo_minutes")
        print("  * demo_credits") 
        print("  * premium_client")
        
    except Exception as e:
        print(f"❌ Error creating accounts: {e}")
        
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(create_sample_accounts())