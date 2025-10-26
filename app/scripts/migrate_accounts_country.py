"""
Script de migración: Agregar campo 'country' a cuentas existentes
Ejecutar una sola vez después del deploy
"""

import asyncio
import logging
from datetime import datetime
import sys
import os

# Agregar el directorio app al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from infrastructure.database_manager import DatabaseManager
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_accounts_add_country():
    """
    Agrega campo 'country' y 'timezone' a todas las cuentas existentes
    Default: Chile (CL) con timezone America/Santiago
    """
    db_manager = DatabaseManager(settings.MONGODB_URI, settings.DATABASE_NAME)
    await db_manager.connect()
    
    try:
        accounts_collection = db_manager.get_collection("accounts")
        
        # 1. Contar cuentas sin country
        count_without_country = await accounts_collection.count_documents({
            "country": {"$exists": False}
        })
        
        logger.info(f"📊 Encontradas {count_without_country} cuentas sin campo 'country'")
        
        if count_without_country == 0:
            logger.info("✅ Todas las cuentas ya tienen el campo 'country'")
            return
        
        # 2. Actualizar cuentas sin country
        # Inferir país basado en timezone si existe
        result = await accounts_collection.update_many(
            {"country": {"$exists": False}},
            {
                "$set": {
                    "country": "CL",  # Default: Chile
                    "timezone": "America/Santiago",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"✅ Actualizadas {result.modified_count} cuentas con country='CL'")
        
        # 3. Casos especiales: Si timezone contiene "Argentina", actualizar a AR
        argentina_accounts = await accounts_collection.find({
            "timezone": {"$regex": "Argentina", "$options": "i"}
        }).to_list(None)
        
        if argentina_accounts:
            logger.info(f"🇦🇷 Encontradas {len(argentina_accounts)} cuentas con timezone Argentina")
            
            for account in argentina_accounts:
                await accounts_collection.update_one(
                    {"_id": account["_id"]},
                    {
                        "$set": {
                            "country": "AR",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                logger.info(f"   - Actualizada cuenta {account['account_id']} a country='AR'")
        
        # 4. Mostrar resumen final
        total_accounts = await accounts_collection.count_documents({})
        cl_accounts = await accounts_collection.count_documents({"country": "CL"})
        ar_accounts = await accounts_collection.count_documents({"country": "AR"})
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("📊 RESUMEN FINAL")
        logger.info("=" * 60)
        logger.info(f"Total de cuentas: {total_accounts}")
        logger.info(f"🇨🇱 Chile (CL): {cl_accounts}")
        logger.info(f"🇦🇷 Argentina (AR): {ar_accounts}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error durante la migración: {e}")
        raise
    finally:
        await db_manager.close()


async def show_accounts_country_status():
    """Muestra el estado actual de los campos country en las cuentas"""
    db_manager = DatabaseManager(settings.MONGODB_URI, settings.DATABASE_NAME)
    await db_manager.connect()
    
    try:
        accounts_collection = db_manager.get_collection("accounts")
        
        # Obtener todas las cuentas
        accounts = await accounts_collection.find({}).to_list(None)
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("📋 ESTADO ACTUAL DE CUENTAS")
        logger.info("=" * 80)
        logger.info(f"{'Account ID':<25} {'Nombre':<30} {'Country':<10} {'Timezone'}")
        logger.info("-" * 80)
        
        for account in accounts:
            account_id = account.get('account_id', 'N/A')
            name = account.get('account_name', 'N/A')[:28]
            country = account.get('country', 'NO SET')
            timezone = account.get('timezone', 'NO SET')
            
            logger.info(f"{account_id:<25} {name:<30} {country:<10} {timezone}")
        
        logger.info("=" * 80)
        
        # Estadísticas
        total = len(accounts)
        with_country = sum(1 for a in accounts if 'country' in a)
        without_country = total - with_country
        
        logger.info(f"\n📊 Estadísticas:")
        logger.info(f"   Total: {total}")
        logger.info(f"   ✅ Con 'country': {with_country}")
        logger.info(f"   ❌ Sin 'country': {without_country}")
        
    except Exception as e:
        logger.error(f"❌ Error al mostrar estado: {e}")
        raise
    finally:
        await db_manager.close()


async def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migración de campo country en cuentas')
    parser.add_argument(
        '--action',
        choices=['status', 'migrate'],
        default='status',
        help='Acción a realizar: status (ver estado) o migrate (ejecutar migración)'
    )
    
    args = parser.parse_args()
    
    if args.action == 'status':
        logger.info("🔍 Mostrando estado actual de cuentas...")
        await show_accounts_country_status()
    elif args.action == 'migrate':
        logger.info("🚀 Iniciando migración de cuentas...")
        await migrate_accounts_add_country()
        logger.info("")
        logger.info("✅ Migración completada exitosamente")
        logger.info("")
        logger.info("📝 Verificando resultado...")
        await show_accounts_country_status()


if __name__ == '__main__':
    asyncio.run(main())
