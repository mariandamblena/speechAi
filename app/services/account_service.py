"""
Servicio para gestión de cuentas y sistema de créditos/límites
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List, Tuple
from bson import ObjectId

from domain.models import AccountModel
from domain.enums import AccountStatus, PlanType
from infrastructure.database_manager import DatabaseManager


class AccountService:
    """Servicio para gestión de cuentas y créditos"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.accounts_collection = db_manager.get_collection("accounts")
        self.logger = logging.getLogger(__name__)
    
    async def create_account(
        self, 
        account_id: str, 
        account_name: str,
        plan_type: PlanType = PlanType.MINUTES_BASED,
        initial_minutes: float = 0.0,
        initial_credits: float = 0.0,
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        features: Optional[Dict] = None,
        settings: Optional[Dict] = None
    ) -> AccountModel:
        """Crea una nueva cuenta con información completa"""
        
        # Verificar que no existe
        existing = await self.get_account(account_id)
        if existing:
            raise ValueError(f"Account {account_id} already exists")
        
        # Preparar datos de la cuenta
        account_data = {
            "account_id": account_id,
            "account_name": account_name,
            "plan_type": plan_type,
            "status": AccountStatus.ACTIVE,
            "minutes_purchased": initial_minutes,
            "credit_balance": initial_credits,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Agregar campos opcionales si se proporcionan
        if contact_name:
            account_data["contact_name"] = contact_name
        if contact_email:
            account_data["contact_email"] = contact_email
        if contact_phone:
            account_data["contact_phone"] = contact_phone
        if features:
            account_data["features"] = features
        if settings:
            account_data["settings"] = settings
        
        account = AccountModel(**account_data)
        
        result = await self.accounts_collection.insert_one(account.to_dict())
        account._id = result.inserted_id
        
        self.logger.info(f"Created account {account_id} with plan {plan_type.value}")
        return account
    
    async def get_account(self, account_id: str) -> Optional[AccountModel]:
        """Obtiene una cuenta por ID"""
        data = await self.accounts_collection.find_one({"account_id": account_id})
        if data:
            return AccountModel.from_dict(data)
        return None
    
    async def update_account(self, account: AccountModel) -> bool:
        """Actualiza una cuenta existente"""
        account.updated_at = datetime.utcnow()
        result = await self.accounts_collection.update_one(
            {"account_id": account.account_id},
            {"$set": account.to_dict()}
        )
        return result.modified_count > 0
    
    async def check_balance(self, account_id: str) -> Dict:
        """Verifica el saldo disponible de una cuenta"""
        account = await self.get_account(account_id)
        if not account:
            return {"error": "Account not found", "has_balance": False}
        
        if account.plan_type == PlanType.UNLIMITED:
            return {
                "has_balance": True,
                "plan_type": "unlimited",
                "can_make_calls": account.status == AccountStatus.ACTIVE
            }
        elif account.plan_type == PlanType.MINUTES_BASED:
            return {
                "has_balance": account.minutes_remaining > 0,
                "remaining": account.minutes_remaining,
                "used": account.minutes_used,
                "purchased": account.minutes_purchased,
                "reserved": account.minutes_reserved,
                "unit": "minutes",
                "plan_type": "minutes_based",
                "can_make_calls": account.can_make_calls
            }
        else:  # CREDIT_BASED
            return {
                "has_balance": account.credit_available > 0,
                "remaining": account.credit_available,
                "used": account.credit_used,
                "balance": account.credit_balance,
                "reserved": account.credit_reserved,
                "unit": "USD",
                "plan_type": "credit_based",
                "can_make_calls": account.can_make_calls
            }
    
    async def reserve_funds(
        self, 
        account_id: str, 
        estimated_minutes: float = 3.0
    ) -> Tuple[bool, Optional[float]]:
        """
        Reserva fondos para una llamada
        Returns: (success, reserved_amount)
        """
        account = await self.get_account(account_id)
        if not account:
            self.logger.error(f"Account {account_id} not found")
            return False, None
        
        if not account.reserve_funds(estimated_minutes):
            self.logger.warning(f"Insufficient balance for account {account_id}")
            return False, None
        
        # Guardar la reserva
        await self.update_account(account)
        
        reserved_amount = (
            estimated_minutes if account.plan_type == PlanType.MINUTES_BASED
            else account.estimate_call_cost(estimated_minutes)
        )
        
        self.logger.info(f"Reserved {reserved_amount} for account {account_id}")
        return True, reserved_amount
    
    async def consume_funds(
        self,
        account_id: str,
        actual_minutes: float,
        actual_cost: float = None
    ) -> bool:
        """Consume fondos después de una llamada completada"""
        account = await self.get_account(account_id)
        if not account:
            return False
        
        account.consume_funds(actual_minutes, actual_cost)
        success = await self.update_account(account)
        
        if success:
            consumed = actual_cost if actual_cost else actual_minutes
            unit = "USD" if actual_cost else "minutes"
            self.logger.info(f"Consumed {consumed} {unit} for account {account_id}")
        
        return success
    
    async def release_reservation(
        self, 
        account_id: str, 
        reserved_amount: float
    ) -> bool:
        """Libera una reserva de fondos"""
        account = await self.get_account(account_id)
        if not account:
            return False
        
        account.release_reservation(reserved_amount)
        success = await self.update_account(account)
        
        if success:
            self.logger.info(f"Released reservation {reserved_amount} for account {account_id}")
        
        return success
    
    async def add_minutes(self, account_id: str, minutes: float) -> bool:
        """Agrega minutos a una cuenta"""
        account = await self.get_account(account_id)
        if not account:
            return False
        
        account.add_minutes(minutes)
        success = await self.update_account(account)
        
        if success:
            self.logger.info(f"Added {minutes} minutes to account {account_id}")
        
        return success
    
    async def add_credits(self, account_id: str, amount: float) -> bool:
        """Agrega créditos a una cuenta"""
        account = await self.get_account(account_id)
        if not account:
            return False
        
        account.add_credits(amount)
        success = await self.update_account(account)
        
        if success:
            self.logger.info(f"Added ${amount} credits to account {account_id}")
        
        return success
    
    async def suspend_account(self, account_id: str, reason: str = "") -> bool:
        """Suspende una cuenta"""
        account = await self.get_account(account_id)
        if not account:
            return False
        
        account.status = AccountStatus.SUSPENDED
        success = await self.update_account(account)
        
        if success:
            self.logger.warning(f"Suspended account {account_id}: {reason}")
        
        return success
    
    async def activate_account(self, account_id: str) -> bool:
        """Activa una cuenta suspendida"""
        account = await self.get_account(account_id)
        if not account:
            return False
        
        account.status = AccountStatus.ACTIVE
        success = await self.update_account(account)
        
        if success:
            self.logger.info(f"Activated account {account_id}")
        
        return success
    
    async def get_account_stats(self, account_id: str) -> Dict:
        """Obtiene estadísticas detalladas de una cuenta"""
        account = await self.get_account(account_id)
        if not account:
            return {"error": "Account not found"}
        
        # Estadísticas básicas
        stats = {
            "account_id": account.account_id,
            "account_name": account.account_name,
            "status": account.status.value,
            "plan_type": account.plan_type.value,
            "created_at": account.created_at,
            "calls_today": account.calls_today,
            "daily_limit": account.daily_call_limit,
            "max_concurrent": account.max_concurrent_calls
        }
        
        # Balance según tipo de plan
        if account.plan_type == PlanType.MINUTES_BASED:
            stats.update({
                "minutes_purchased": account.minutes_purchased,
                "minutes_used": account.minutes_used,
                "minutes_remaining": account.minutes_remaining,
                "minutes_reserved": account.minutes_reserved
            })
        elif account.plan_type == PlanType.CREDIT_BASED:
            stats.update({
                "credit_balance": account.credit_balance,
                "credit_used": account.credit_used,
                "credit_available": account.credit_available,
                "credit_reserved": account.credit_reserved,
                "cost_per_minute": account.cost_per_minute,
                "cost_per_setup": account.cost_per_call_setup
            })
        
        return stats
    
    async def reset_daily_counters(self) -> int:
        """Resetea contadores diarios (para ejecutar con cron)"""
        result = await self.accounts_collection.update_many(
            {},
            {"$set": {"calls_today": 0, "updated_at": datetime.utcnow()}}
        )
        
        self.logger.info(f"Reset daily counters for {result.modified_count} accounts")
        return result.modified_count
    
    async def list_accounts(
        self, 
        status: Optional[AccountStatus] = None,
        plan_type: Optional[PlanType] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[AccountModel]:
        """Lista cuentas con filtros opcionales"""
        filters = {}
        if status:
            filters["status"] = status.value
        if plan_type:
            filters["plan_type"] = plan_type.value
        
        cursor = self.accounts_collection.find(filters).skip(skip).limit(limit)
        accounts = []
        
        async for doc in cursor:
            accounts.append(AccountModel.from_dict(doc))
        
        return accounts