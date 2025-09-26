"""
Script para verificar y crear la cuenta de usuario
"""
import asyncio
import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.getcwd())

from services.account_service import AccountService
from infrastructure.database_manager import DatabaseManager
from config.settings import get_settings

async def check_and_create_account():
    print("🔍 VERIFICANDO CUENTA 'strasing'")
    print("=" * 40)
    
    # Obtener configuración
    settings = get_settings()
    
    # Inicializar database manager
    db = DatabaseManager(settings.database.uri, settings.database.database)
    await db.connect()
    
    # Inicializar account service
    service = AccountService(db)
    
    # Verificar si la cuenta existe
    account = await service.get_account('strasing')
    
    if account:
        print(f"✅ Cuenta encontrada: strasing")
        print(f"   📋 Plan: {account.plan_type}")
        print(f"   💰 Puede hacer llamadas: {account.can_make_calls}")
        
        if hasattr(account, 'credit_balance'):
            print(f"   💳 Balance: ${account.credit_balance}")
        if hasattr(account, 'minutes_remaining'):
            print(f"   ⏱️ Minutos: {account.minutes_remaining}")
    else:
        print("❌ Cuenta 'strasing' no encontrada")
        print("\n🔧 Creando cuenta...")
        
        # Crear cuenta básica
        try:
            new_account = await service.create_account(
                account_id="strasing",
                account_name="Cuenta Strasing",
                plan_type="credit_based",
                initial_credits=100.0  # $100 iniciales para pruebas
            )
            
            print(f"✅ Cuenta creada exitosamente:")
            print(f"   📋 ID: {new_account.account_id}")
            print(f"   📋 Plan: {new_account.plan_type}")
            print(f"   💳 Balance: ${new_account.credit_balance}")
            
        except Exception as e:
            print(f"❌ Error creando cuenta: {str(e)}")
    
    # Cerrar conexión (sin await porque no hay método disconnect)

if __name__ == "__main__":
    asyncio.run(check_and_create_account())