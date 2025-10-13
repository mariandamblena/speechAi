"""
Servicio para gestión de transacciones financieras
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List
from bson import ObjectId

from domain.models import TransactionModel, AccountModel
from domain.enums import TransactionType
from infrastructure.database_manager import DatabaseManager


class TransactionService:
    """Servicio para gestión de transacciones financieras"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.transactions_collection = db_manager.get_collection("transactions")
        self.logger = logging.getLogger(__name__)
    
    async def create_transaction(
        self,
        account_id: str,
        transaction_type: TransactionType,
        amount: float,
        cost: int,
        description: str,
        reference_id: Optional[str] = None
    ) -> TransactionModel:
        """Crea una nueva transacción"""
        
        transaction = TransactionModel(
            account_id=account_id,
            type=transaction_type,
            amount=amount,
            cost=cost,
            description=description,
            reference_id=reference_id,
            created_at=datetime.utcnow()
        )
        
        result = await self.transactions_collection.insert_one(transaction.to_dict())
        transaction._id = result.inserted_id
        
        self.logger.info(f"Created transaction {transaction.transaction_id} for account {account_id}")
        return transaction
    
    async def get_account_transactions(
        self,
        account_id: str,
        limit: int = 50,
        skip: int = 0,
        transaction_type: Optional[TransactionType] = None
    ) -> List[TransactionModel]:
        """Obtiene transacciones de una cuenta"""
        
        filters = {"account_id": account_id}
        if transaction_type:
            filters["type"] = transaction_type.value
        
        cursor = self.transactions_collection.find(filters).sort(
            "created_at", -1
        ).skip(skip).limit(limit)
        
        transactions = []
        async for doc in cursor:
            transactions.append(TransactionModel.from_dict(doc))
        
        return transactions
    
    async def get_transaction(self, transaction_id: str) -> Optional[TransactionModel]:
        """Obtiene una transacción por ID"""
        data = await self.transactions_collection.find_one({"transaction_id": transaction_id})
        if data:
            return TransactionModel.from_dict(data)
        return None
    
    async def get_account_transaction_summary(self, account_id: str) -> Dict:
        """Obtiene resumen de transacciones de una cuenta"""
        
        pipeline = [
            {"$match": {"account_id": account_id}},
            {"$group": {
                "_id": "$type",
                "total_amount": {"$sum": "$amount"},
                "total_cost": {"$sum": "$cost"},
                "count": {"$sum": 1}
            }}
        ]
        
        cursor = self.transactions_collection.aggregate(pipeline)
        results = []
        async for doc in cursor:
            results.append(doc)
        
        # Procesar resultados
        summary = {
            "total_recharges": 0.0,
            "total_usage": 0.0,
            "total_cost": 0,
            "transaction_count": 0,
            "by_type": {}
        }
        
        for result in results:
            transaction_type = result["_id"]
            amount = result["total_amount"]
            cost = result["total_cost"]
            count = result["count"]
            
            summary["by_type"][transaction_type] = {
                "amount": amount,
                "cost": cost,
                "count": count
            }
            
            summary["total_cost"] += cost
            summary["transaction_count"] += count
            
            if amount > 0:
                summary["total_recharges"] += amount
            else:
                summary["total_usage"] += abs(amount)
        
        return summary
    
    async def create_topup_transaction(
        self,
        account_id: str,
        amount: float,
        cost: int,
        unit_type: str = "credits",
        description: Optional[str] = None
    ) -> TransactionModel:
        """Crea transacción de recarga"""
        
        if unit_type == "credits":
            transaction_type = TransactionType.TOPUP_CREDITS
            desc = description or f"Recarga de {amount:,.0f} créditos"
        else:
            transaction_type = TransactionType.TOPUP_MINUTES
            desc = description or f"Recarga de {amount:,.1f} minutos"
        
        return await self.create_transaction(
            account_id=account_id,
            transaction_type=transaction_type,
            amount=amount,
            cost=cost,
            description=desc
        )
    
    async def create_usage_transaction(
        self,
        account_id: str,
        amount: float,
        cost: int,
        batch_id: Optional[str] = None,
        job_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> TransactionModel:
        """Crea transacción de uso/gasto"""
        
        desc = description or f"Uso en campaña - {amount:,.0f} créditos"
        reference_id = batch_id or job_id
        
        return await self.create_transaction(
            account_id=account_id,
            transaction_type=TransactionType.CALL_USAGE,
            amount=-abs(amount),  # Siempre negativo para uso
            cost=cost,
            description=desc,
            reference_id=reference_id
        )
    
    async def create_bonus_transaction(
        self,
        account_id: str,
        amount: float,
        description: str,
        reference_id: Optional[str] = None
    ) -> TransactionModel:
        """Crea transacción de bono (sin costo)"""
        
        return await self.create_transaction(
            account_id=account_id,
            transaction_type=TransactionType.BONUS,
            amount=amount,
            cost=0,
            description=description,
            reference_id=reference_id
        )