"""
Servicio para creación de batches y jobs desde archivos Excel
Implementa lógica anti-duplicación y procesamiento masivo
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging

from domain.models import BatchModel, JobModel, DebtorModel, ContactInfo, CallPayload
from domain.enums import JobStatus, CallMode
from infrastructure.database_manager import DatabaseManager
from utils.excel_processor import ExcelDebtorProcessor
from services.account_service import AccountService

logger = logging.getLogger(__name__)


class BatchCreationService:
    """Servicio para creación de batches y jobs desde Excel"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.excel_processor = ExcelDebtorProcessor()
        self.account_service = AccountService(db_manager)
    
    async def create_batch_from_excel(
        self, 
        file_content: bytes, 
        account_id: str, 
        batch_name: str = None,
        batch_description: str = None,
        allow_duplicates: bool = False,
        dias_fecha_limite: Optional[int] = None,
        dias_fecha_maxima: Optional[int] = None,
        call_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crea un batch completo desde archivo Excel con anti-duplicación
        
        Args:
            file_content: Contenido del archivo Excel
            account_id: ID de la cuenta
            batch_name: Nombre opcional del batch
            batch_description: Descripción opcional
            allow_duplicates: Si permite duplicados (default: False)
            dias_fecha_limite: Días a sumar a fecha actual para fecha_limite (ej: 30)
            dias_fecha_maxima: Días a sumar a fecha actual para fecha_maxima (ej: 45)
            call_settings: Configuración de llamadas específica para este batch
        
        Returns:
            Diccionario con resultado del procesamiento
        """
        try:
            # 1. Verificar que la cuenta existe y está activa
            account = await self.account_service.get_account(account_id)
            if not account:
                raise ValueError(f"Cuenta {account_id} no encontrada")
            
            if not account.can_make_calls:
                raise ValueError(f"Cuenta {account_id} no puede realizar llamadas")
            
            # 2. Procesar archivo Excel
            logger.info(f"Procesando archivo Excel para cuenta {account_id}")
            excel_data = self.excel_processor.process_excel_data(file_content, account_id)
            
            batch_id = excel_data['batch_id']
            debtors_data = excel_data['debtors']
            
            # 3. Verificar duplicados si no están permitidos
            duplicates_info = []
            if not allow_duplicates:
                duplicates_info = await self._check_duplicates(batch_id, debtors_data, account_id)
            
            # 4. Filtrar duplicados si los hay
            valid_debtors = debtors_data
            if duplicates_info and not allow_duplicates:
                duplicate_ruts = {dup['rut'] for dup in duplicates_info}
                valid_debtors = [d for d in debtors_data if d['rut'] not in duplicate_ruts]
                
                logger.warning(f"Se encontraron {len(duplicates_info)} duplicados, "
                             f"procesando {len(valid_debtors)} deudores únicos")
            
            if not valid_debtors:
                return {
                    'success': False,
                    'error': f'❌ No hay contactos válidos para procesar. Se encontraron {len(duplicates_info)} duplicados en otros batches. '
                             f'Si deseas crear un nuevo batch con estos mismos contactos, activa la opción "Permitir Duplicados" en el frontend.',
                    'duplicates': duplicates_info,
                    'total_processed': 0,
                    'suggestion': 'Activa allow_duplicates=true en el request para permitir contactos que ya existen en otros batches'
                }
            
            # 5. Crear el batch
            batch = BatchModel(
                account_id=account_id,
                batch_id=batch_id,
                name=batch_name or f"Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                description=batch_description or f"Importado desde Excel con {len(valid_debtors)} deudores",
                total_jobs=len(valid_debtors),
                pending_jobs=len(valid_debtors),
                call_settings=call_settings,  # Agregar call_settings
                created_at=datetime.utcnow()
            )
            
            # 6. Estimar costos del batch
            estimated_cost = 0.0
            for _ in valid_debtors:
                estimated_cost += account.estimate_call_cost()
            
            batch.estimated_cost = estimated_cost
            
            # 7. Verificar que la cuenta tiene suficiente saldo para todo el batch
            if not self._can_afford_batch(account, estimated_cost):
                return {
                    'success': False,
                    'error': f'Saldo insuficiente. Necesario: {estimated_cost:.2f}, '
                           f'Disponible: {account.credit_available if account.plan_type.value == "credit_based" else account.minutes_remaining}',
                    'estimated_cost': estimated_cost,
                    'total_processed': 0
                }
            
            # 8. Guardar batch en base de datos
            batch_doc = await self.db.batches.insert_one(batch.to_dict())
            batch._id = batch_doc.inserted_id
            
            logger.info(f"Batch {batch_id} creado con ID {batch._id}")
            
            # 9. Crear y guardar deudores
            logger.info(f"Creando {len(valid_debtors)} deudores para batch {batch_id}")
            debtors_created = await self._create_debtors(valid_debtors, batch_id)
            logger.info(f"Deudores creados: {len(debtors_created)}")
            
            # 10. Crear jobs de llamadas
            logger.info(f"Creando jobs de llamadas para {len(valid_debtors)} deudores")
            jobs_created = await self._create_jobs_from_debtors(
                valid_debtors, 
                account_id, 
                batch_id,
                dias_fecha_limite=dias_fecha_limite,
                dias_fecha_maxima=dias_fecha_maxima
            )
            logger.info(f"Jobs de llamadas creados: {len(jobs_created)}")
            
            if not jobs_created:
                logger.error("NO SE CREARON JOBS! Verificar datos y configuración")
                return {
                    'success': False,
                    'error': 'No se pudieron crear jobs de llamadas',
                    'batch_id': batch_id,
                    'debtors_processed': len(valid_debtors),
                    'total_processed': 0
                }
            
            # 11. Actualizar estadísticas del batch
            await self.db.batches.update_one(
                {"batch_id": batch_id},
                {
                    "$set": {
                        "total_jobs": len(jobs_created),
                        "pending_jobs": len(jobs_created),
                        "estimated_cost": estimated_cost
                    }
                }
            )
            
            result = {
                'success': True,
                'batch_id': batch_id,
                'batch_name': batch.name,
                'total_debtors': len(debtors_created),
                'total_jobs': len(jobs_created),
                'estimated_cost': estimated_cost,
                'duplicates_found': len(duplicates_info) if duplicates_info else 0,
                'duplicates': duplicates_info[:10] if duplicates_info else [],  # Solo primeros 10
                'created_at': batch.created_at.isoformat()
            }
            
            logger.info(f"Batch {batch_id} procesado exitosamente: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error creando batch desde Excel: {str(e)}")
            raise
    
    async def _check_duplicates(
        self, 
        new_batch_id: str, 
        debtors_data: List[Dict], 
        account_id: str
    ) -> List[Dict[str, Any]]:
        """Verifica duplicados en batches existentes"""
        duplicates = []
        
        # Crear conjunto de RUTs del nuevo batch
        new_ruts = {d['rut'] for d in debtors_data}
        
        # Buscar RUTs existentes en otros batches de la misma cuenta
        existing_debtors = await self.db.debtors.find({
            "rut": {"$in": list(new_ruts)},
            "batch_id": {"$ne": new_batch_id}  # Excluir el mismo batch
        }).to_list(None)
        
        # Buscar jobs existentes (anti-duplicación por deduplication_key)
        existing_job_keys = await self.db.jobs.find({
            "account_id": account_id,
            "deduplication_key": {"$regex": f"^{account_id}::.*"}
        }, {"deduplication_key": 1, "batch_id": 1}).to_list(None)
        
        existing_keys_set = {job["deduplication_key"] for job in existing_job_keys}
        
        # Verificar duplicados
        for debtor in debtors_data:
            rut = debtor['rut']
            potential_key = f"{account_id}::{rut}::{new_batch_id}"
            
            duplicate_info = {
                'rut': rut,
                'nombre': debtor['nombre'],
                'monto_total': debtor['monto_total'],
                'duplicate_reasons': []
            }
            
            # Verificar si el RUT ya existe en otros batches
            existing_debtor = next((d for d in existing_debtors if d['rut'] == rut), None)
            if existing_debtor:
                duplicate_info['duplicate_reasons'].append({
                    'type': 'existing_debtor',
                    'batch_id': existing_debtor['batch_id'],
                    'message': f"RUT ya existe en batch {existing_debtor['batch_id']}"
                })
            
            # Verificar si ya hay un job para este RUT en la cuenta
            conflicting_key = next((k for k in existing_keys_set if k.startswith(f"{account_id}::{rut}::")), None)
            if conflicting_key:
                conflicting_batch = conflicting_key.split("::")[-1]
                duplicate_info['duplicate_reasons'].append({
                    'type': 'existing_job',
                    'batch_id': conflicting_batch,
                    'deduplication_key': conflicting_key,
                    'message': f"Ya existe job para RUT {rut} en batch {conflicting_batch}"
                })
            
            if duplicate_info['duplicate_reasons']:
                duplicates.append(duplicate_info)
        
        return duplicates
    
    def _can_afford_batch(self, account, estimated_cost: float) -> bool:
        """Verifica si la cuenta puede pagar el batch completo"""
        if account.plan_type.value == "unlimited":
            return True
        elif account.plan_type.value == "minutes_based":
            return account.minutes_remaining >= estimated_cost
        else:  # credit_based
            return account.credit_available >= estimated_cost
    
    async def _create_debtors(self, debtors_data: List[Dict], batch_id: str) -> List[str]:
        """Crea documentos de deudores en la base de datos"""
        if not debtors_data:
            return []
        
        from pymongo import ReplaceOne
        
        # Convertir a modelos DebtorModel
        debtor_models = []
        for debtor_data in debtors_data:
            debtor = DebtorModel.from_dict(debtor_data)
            debtor_models.append(debtor.to_dict())
        
        # Insertar en bulk con upsert por clave única
        operations = []
        for debtor_dict in debtor_models:
            operations.append(
                ReplaceOne(
                    filter={'key': debtor_dict['key']},
                    replacement=debtor_dict,
                    upsert=True
                )
            )
        
        if operations:
            result = await self.db.debtors.bulk_write(operations)
            logger.info(f"Deudores creados/actualizados: {result.upserted_count + result.modified_count}")
            return [d['key'] for d in debtor_models]
        
        return []
    
    async def _create_jobs_from_debtors(
        self, 
        debtors_data: List[Dict], 
        account_id: str, 
        batch_id: str,
        dias_fecha_limite: Optional[int] = None,
        dias_fecha_maxima: Optional[int] = None
    ) -> List[str]:
        """
        Crea jobs de llamadas desde datos de deudores
        
        Args:
            debtors_data: Lista de deudores procesados
            account_id: ID de la cuenta
            batch_id: ID del batch
            dias_fecha_limite: Días a sumar a fecha actual para fecha_limite
            dias_fecha_maxima: Días a sumar a fecha actual para fecha_maxima
        """
        logger.info(f"_create_jobs_from_debtors iniciado: {len(debtors_data)} deudores, account={account_id}, batch={batch_id}")
        
        if not debtors_data:
            logger.warning("debtors_data está vacío!")
            return []
        
        jobs_data = []
        now = datetime.utcnow()
        
        # Calcular fechas dinámicas si se especificaron los días
        from datetime import timedelta
        fecha_limite_calculada = None
        fecha_maxima_calculada = None
        
        if dias_fecha_limite is not None:
            fecha_limite_calculada = (now + timedelta(days=dias_fecha_limite)).strftime('%Y-%m-%d')
            logger.info(f"Fecha límite calculada dinámicamente: HOY + {dias_fecha_limite} días = {fecha_limite_calculada}")
        
        if dias_fecha_maxima is not None:
            fecha_maxima_calculada = (now + timedelta(days=dias_fecha_maxima)).strftime('%Y-%m-%d')
            logger.info(f"Fecha máxima calculada dinámicamente: HOY + {dias_fecha_maxima} días = {fecha_maxima_calculada}")
        
        # Obtener tiempo local Chile para contexto
        import pytz
        chile_tz = pytz.timezone('America/Santiago')
        now_chile = datetime.now(chile_tz).strftime(
            '%A, %B %d, %Y at %I:%M:%S %p CLT'
        )
        
        for debtor in debtors_data:
            # Crear ContactInfo
            phones = [debtor['to_number']] if debtor['to_number'] else []
            if not phones:
                logger.warning(f"Deudor {debtor.get('rut', 'N/A')} sin teléfono válido, saltando job. Data: {debtor}")
                continue
            
            contact = ContactInfo(
                name=debtor['nombre'],
                dni=debtor['rut'],
                phones=phones
            )
            
            # Determinar qué fecha_limite usar: calculada dinámicamente o la del Excel
            fecha_limite_final = fecha_limite_calculada if fecha_limite_calculada else debtor.get('fecha_limite', '')
            
            # Preparar additional_info con fecha_maxima
            additional_info = {
                'cantidad_cupones': debtor.get('cantidad_cupones', 0),
                'current_time_America_Santiago': now_chile
            }
            
            # Agregar fecha_maxima (calculada o del Excel)
            if fecha_maxima_calculada:
                additional_info['fecha_maxima'] = fecha_maxima_calculada
            elif debtor.get('fecha_maxima'):
                additional_info['fecha_maxima'] = debtor.get('fecha_maxima', '')
            
            # Crear CallPayload con info de deuda
            payload = CallPayload(
                debt_amount=debtor['monto_total'],
                due_date=fecha_limite_final,
                company_name=debtor.get('origen_empresa', ''),
                additional_info=additional_info
            )
            
            # Crear JobModel
            job = JobModel(
                account_id=account_id,
                batch_id=batch_id,
                status=JobStatus.PENDING,
                contact=contact,
                payload=payload,
                mode=CallMode.SINGLE,
                created_at=now
            )
            
            # Generar clave de deduplicación
            job.deduplication_key = job.generate_deduplication_key()
            logger.info(f"Job creado para {debtor.get('rut', 'N/A')}: {job.deduplication_key}, teléfono: {debtor.get('to_number', 'N/A')}")
            
            jobs_data.append(job.to_dict())
        
        logger.info(f"Preparados {len(jobs_data)} jobs para insertar en DB")
        
        # Insertar jobs con anti-duplicación
        if jobs_data:
            from pymongo import ReplaceOne
            
            operations = []
            for job_dict in jobs_data:
                operations.append(
                    ReplaceOne(
                        filter={'deduplication_key': job_dict['deduplication_key']},
                        replacement=job_dict,
                        upsert=True
                    )
                )
            
            result = await self.db.jobs.bulk_write(operations)
            created_count = result.upserted_count + result.modified_count
            logger.info(f"Jobs creados/actualizados: {created_count}")
            logger.info(f"Detalles del resultado: upserted={result.upserted_count}, modified={result.modified_count}")
            
            if created_count == 0:
                logger.warning("No se crearon jobs! Posible problema con deduplication_key o datos")
                logger.warning(f"Jobs data sample: {jobs_data[0] if jobs_data else 'Empty'}")
            
            return [j['deduplication_key'] for j in jobs_data]
        
        return []
    
    async def get_batch_preview(self, file_content: bytes, account_id: str) -> Dict[str, Any]:
        """
        Genera vista previa del archivo Excel sin crear el batch
        Útil para mostrar al usuario qué se va a procesar
        """
        try:
            # Procesar Excel
            excel_data = self.excel_processor.process_excel_data(file_content, account_id)
            debtors_data = excel_data['debtors']
            
            # Verificar duplicados
            duplicates_info = await self._check_duplicates(
                excel_data['batch_id'], debtors_data, account_id
            )
            
            # Calcular estadísticas
            total_amount = sum(d['monto_total'] for d in debtors_data)
            valid_phones = sum(1 for d in debtors_data if d['to_number'])
            
            return {
                'success': True,
                'preview': {
                    'total_rows': len(debtors_data),
                    'valid_debtors': len(debtors_data),
                    'with_valid_phone': valid_phones,
                    'without_phone': len(debtors_data) - valid_phones,
                    'total_debt_amount': total_amount,
                    'duplicates_found': len(duplicates_info),
                    'duplicates_preview': duplicates_info[:5],  # Solo primeros 5
                    'sample_debtors': debtors_data[:3]  # Muestra primeros 3
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_batch_status(self, batch_id: str, account_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado actual de un batch"""
        batch_doc = await self.db.batches.find_one({
            "batch_id": batch_id,
            "account_id": account_id
        })
        
        if not batch_doc:
            return None
        
        batch = BatchModel.from_dict(batch_doc)
        
        # Obtener estadísticas actualizadas de jobs
        job_stats = await self.db.jobs.aggregate([
            {"$match": {"batch_id": batch_id, "account_id": account_id}},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(None)
        
        # Convertir a diccionario
        stats = {stat["_id"]: stat["count"] for stat in job_stats}
        
        return {
            'batch_id': batch.batch_id,
            'name': batch.name,
            'description': batch.description,
            'total_jobs': batch.total_jobs,
            'pending_jobs': stats.get('pending', 0),
            'completed_jobs': stats.get('completed', 0),
            'failed_jobs': stats.get('failed', 0),
            'suspended_jobs': stats.get('suspended', 0),
            'completion_rate': batch.completion_rate,
            'is_completed': batch.is_completed,
            'estimated_cost': batch.estimated_cost,
            'total_cost': batch.total_cost,
            'created_at': batch.created_at.isoformat() if batch.created_at else None,
            'started_at': batch.started_at.isoformat() if batch.started_at else None,
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None
        }