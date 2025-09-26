"""
Database Manager moderno para API asíncrona con Motor
"""

import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection


class DatabaseManager:
    """Manager para conexiones asíncronas a MongoDB usando Motor"""
    
    def __init__(self, connection_string: str, database_name: str):
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        self.logger = logging.getLogger(__name__)
    
    async def connect(self) -> None:
        """Conecta a MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client[self.database_name]
            
            # Verificar conexión
            await self.db.command("ping")
            
            self.logger.info(f"Connected to MongoDB: {self.database_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self) -> None:
        """Cierra la conexión"""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed")
    
    def get_collection(self, collection_name: str) -> AsyncIOMotorCollection:
        """Obtiene una colección específica"""
        if self.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.db[collection_name]
    
    # Propiedades para acceso directo a colecciones
    @property
    def accounts(self) -> AsyncIOMotorCollection:
        """Colección de cuentas de usuario"""
        return self.get_collection("accounts")
    
    @property
    def jobs(self) -> AsyncIOMotorCollection:
        """Colección de jobs de llamadas"""
        return self.get_collection("jobs")
    
    @property
    def batches(self) -> AsyncIOMotorCollection:
        """Colección de batches"""
        return self.get_collection("batches")
    
    @property
    def debtors(self) -> AsyncIOMotorCollection:
        """Colección de deudores"""
        return self.get_collection("debtors")
    
    @property
    def call_results(self) -> AsyncIOMotorCollection:
        """Colección de resultados de llamadas"""
        return self.get_collection("call_results")
    
    async def health_check(self) -> bool:
        """Verifica la salud de la conexión"""
        try:
            if self.db is None:
                return False
            await self.db.command("ping")
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    # ============================================================================
    # MÉTODOS DE OPERACIONES CRUD
    # ============================================================================
    
    async def find_documents(self, collection_name: str, filter_dict: Dict[str, Any] = None) -> list:
        """Busca documentos en una colección"""
        try:
            collection = self.get_collection(collection_name)
            cursor = collection.find(filter_dict or {})
            documents = await cursor.to_list(length=None)
            return documents
        except Exception as e:
            self.logger.error(f"Error finding documents in {collection_name}: {e}")
            raise
    
    async def find_one_document(self, collection_name: str, filter_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Busca un documento en una colección"""
        try:
            collection = self.get_collection(collection_name)
            document = await collection.find_one(filter_dict)
            return document
        except Exception as e:
            self.logger.error(f"Error finding document in {collection_name}: {e}")
            raise
    
    async def insert_document(self, collection_name: str, document: Dict[str, Any]):
        """Inserta un documento en una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = await collection.insert_one(document)
            return result
        except Exception as e:
            self.logger.error(f"Error inserting document in {collection_name}: {e}")
            raise
    
    async def insert_many_documents(self, collection_name: str, documents: list):
        """Inserta múltiples documentos en una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = await collection.insert_many(documents)
            return result
        except Exception as e:
            self.logger.error(f"Error inserting documents in {collection_name}: {e}")
            raise
    
    async def update_document(self, collection_name: str, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """Actualiza un documento en una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = await collection.update_one(filter_dict, update_dict)
            return result
        except Exception as e:
            self.logger.error(f"Error updating document in {collection_name}: {e}")
            raise
    
    async def update_many_documents(self, collection_name: str, filter_dict: Dict[str, Any], update_dict: Dict[str, Any]):
        """Actualiza múltiples documentos en una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = await collection.update_many(filter_dict, update_dict)
            return result
        except Exception as e:
            self.logger.error(f"Error updating documents in {collection_name}: {e}")
            raise
    
    async def delete_document(self, collection_name: str, filter_dict: Dict[str, Any]):
        """Elimina un documento de una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = await collection.delete_one(filter_dict)
            return result
        except Exception as e:
            self.logger.error(f"Error deleting document from {collection_name}: {e}")
            raise
    
    async def delete_many_documents(self, collection_name: str, filter_dict: Dict[str, Any]):
        """Elimina múltiples documentos de una colección"""
        try:
            collection = self.get_collection(collection_name)
            result = await collection.delete_many(filter_dict)
            return result
        except Exception as e:
            self.logger.error(f"Error deleting documents from {collection_name}: {e}")
            raise