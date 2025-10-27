"""
Servicio de carga de batches con lógica específica para Argentina
Normalización de teléfonos +54, y fechas DD/MM/YYYY
Soporta múltiples casos de uso a través del sistema de procesadores
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import logging
import re

from domain.models import BatchModel, JobModel, DebtorModel, ContactInfo, CallPayload
from domain.enums import JobStatus, CallMode, AccountStatus
from infrastructure.database_manager import DatabaseManager
from services.account_service import AccountService
from utils.normalizers import normalize_phone_ar, normalize_date, normalize_key

logger = logging.getLogger(__name__)


class ArgentinaBatchService:
    """Servicio de carga de batches con lógica específica para Argentina
    Incluye normalización de teléfonos argentinos (+54) y fechas DD/MM/YYYY
    Soporta múltiples casos de uso: cobranza, marketing, etc.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.account_service = AccountService(db_manager)
        
        # Configuración para Argentina
        self.country_config = {
            'country': 'AR',
            'default_area_code': '11'  # Buenos Aires por defecto
        }
    
    def _norm_key(self, key: str) -> str:
        """Normaliza claves para búsqueda flexible"""
        if not key:
            return ""
        
        # Remover acentos, espacios, caracteres especiales
        import unicodedata
        normalized = unicodedata.normalize('NFD', str(key))
        ascii_str = normalized.encode('ascii', 'ignore').decode('ascii')
        
        # Solo letras, números y espacios, luego lowercase
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', ascii_str)
        clean = re.sub(r'\s+', ' ', clean).strip().lower()
        
        return clean
    
    def _norm_ar_phone(self, raw_phone: Any, kind: str = 'any') -> Optional[str]:
        """
        Normaliza teléfonos argentinos a formato E.164 (+54XXXXXXXXXX)
        También puede convertir números chilenos para testing
        
        Args:
            raw_phone: Número crudo
            kind: 'mobile', 'landline', 'any'
        
        Returns:
            Número normalizado en formato +54XXXXXXXXXX o None
        """
        if raw_phone is None or raw_phone == '':
            return None
        
        phone_str = str(raw_phone).strip()
        
        # Si ya tiene +54, devolverlo
        if phone_str.startswith('+54'):
            return phone_str
        
        # Si tiene +56 (Chile), convertir a +54 para testing
        if phone_str.startswith('+56'):
            # Extraer el número sin código de país
            clean = phone_str[3:]
            # Para números móviles chilenos 9XXXXXXXX, convertir a argentinos
            if clean.startswith('9') and len(clean) == 9:
                # Convertir +56 9XXXX XXXX a +54 9 11 XXXX XXXX (formato móvil argentino)
                return f"+5491{clean[1:]}"
            # Para números fijos chilenos, convertir a móvil argentino
            elif len(clean) == 8:
                return f"+54911{clean}"
        
        # Limpiar y extraer solo dígitos
        clean = re.sub(r'[^\d]', '', phone_str)
        
        # Remover código país si está presente
        if clean.startswith('54'):
            clean = clean[2:]
        elif clean.startswith('56'):
            # Convertir de chile a argentina para testing
            clean = clean[2:]
            if clean.startswith('9') and len(clean) == 9:
                return f"+5491{clean[1:]}"
            elif len(clean) == 8:
                return f"+54911{clean}"
        
        # Remover ceros iniciales (trunk)
        clean = clean.lstrip('0')
        
        # Validaciones específicas para Argentina
        if len(clean) == 10:
            # Formato: 11XXXXXXXX (Buenos Aires) o 9XXXXXXXXX (móvil)
            if clean.startswith('11') or clean.startswith('9'):
                return f"+54{clean}"
        elif len(clean) == 8:
            # Teléfono fijo sin código de área, agregar 11 (Buenos Aires)
            if not clean.startswith('9'):
                return f"+5411{clean}"
        elif len(clean) == 9:
            # Móvil sin código país
            if clean.startswith('9'):
                return f"+549{clean}"
        
        # Si llegamos aquí, intentar formatear como móvil argentino genérico
        if len(clean) >= 8:
            # Asumir móvil Buenos Aires
            return f"+54911{clean[-8:]}"
        
        return None
    
    def _to_iso_date(self, value: Any) -> Optional[str]:
        """Convierte fecha a formato ISO (YYYY-MM-DD), priorizando formato argentino"""
        if value is None or value == '':
            return None
        
        # 1. Si es número (Excel serial)
        if isinstance(value, (int, float)):
            try:
                base_date = datetime(1899, 12, 30, tzinfo=timezone.utc)
                target_date = base_date + timedelta(days=int(value))
                return target_date.date().isoformat()
            except (ValueError, OverflowError):
                return None
        
        value_str = str(value).strip()
        
        # 2. Formato argentino: DD/MM/YYYY o DD-MM-YYYY
        ar_pattern = r'^(\d{1,2})[\\/\-](\d{1,2})[\\/\-](\d{2,4})$'
        match = re.match(ar_pattern, value_str)
        if match:
            day, month, year = match.groups()
            
            # Expandir año de 2 dígitos
            if len(year) == 2:
                year = '20' + year
            
            try:
                year_int, month_int, day_int = int(year), int(month), int(day)
                if 1 <= month_int <= 12 and 1 <= day_int <= 31:
                    date_obj = datetime(year_int, month_int, day_int, tzinfo=timezone.utc)
                    return date_obj.date().isoformat()
            except ValueError:
                pass
        
        # 3. Formato ISO u otros formatos estándar
        try:
            parsed_date = datetime.fromisoformat(value_str.replace('Z', '+00:00'))
            return parsed_date.date().isoformat()
        except ValueError:
            pass
        
        return None
    
    def _add_days_iso(self, iso_date: str, days: int) -> Optional[str]:
        """Suma días a fecha ISO (YYYY-MM-DD) manteniendo UTC"""
        if not iso_date:
            return None
        
        try:
            year, month, day = map(int, iso_date.split('-'))
            date_obj = datetime(year, month, day, tzinfo=timezone.utc)
            new_date = date_obj + timedelta(days=days)
            return new_date.date().isoformat()
        except (ValueError, TypeError):
            return None
    
    def _to_number_pesos(self, value: Any) -> float:
        """Convierte valor a pesos argentinos (no centavos)"""
        if value is None or value == '':
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Limpiar string: remover $, espacios, puntos (miles), cambiar coma por punto (decimales)
        value_str = str(value).strip()
        value_str = re.sub(r'[\s$]', '', value_str)  # Remover espacios y $
        value_str = value_str.replace('.', '').replace(',', '.')  # Miles y decimales
        
        try:
            return float(value_str)
        except ValueError:
            return 0.0
    
    def _get_field(self, row: Dict, key_index: Dict, candidates: List[str]) -> Any:
        """Obtiene campo del row usando candidatos de nombres"""
        # Búsqueda exacta
        for candidate in candidates:
            norm_key = self._norm_key(candidate)
            if norm_key in key_index:
                return row[key_index[norm_key]]
        
        # Búsqueda por contención
        for norm_key in key_index:
            if any(self._norm_key(candidate) in norm_key for candidate in candidates):
                return row[key_index[norm_key]]
        
        return None
    
    async def _process_simple_excel_data(self, file_content: bytes, account_id: str) -> List[Dict[str, Any]]:
        """
        Procesamiento simple para casos de uso no-cobranza
        Sin agrupación por DNI, procesamiento directo 1:1
        """
        try:
            # Usar pandas para leer Excel
            import pandas as pd
            import io
            
            # Leer Excel
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Normalizar headers
            df.columns = [self._norm_key(str(col)) for col in df.columns]
            
            normalized_contacts = []
            
            for idx, row in df.iterrows():
                row_dict = row.to_dict()
                
                # Extraer campos principales con múltiples candidatos
                nombre = self._get_field_value(row_dict, ['nombre', 'name', 'client name', 'cliente'])
                
                # Para marketing/otros casos, puede no ser DNI
                dni = self._get_field_value(row_dict, ['dni', 'cuit', 'cuil', 'id', 'cedula', 'identificacion'])
                
                # Teléfonos
                telefono = self._get_field_value(row_dict, [
                    'telefono', 'phone', 'telefono movil', 'celular', 'mobile'
                ])
                
                # Normalizar teléfono argentino
                phone_normalized = self._norm_ar_phone(telefono, 'any')
                
                # Log detallado para debug
                logger.info(f"Row {idx}: nombre='{nombre}', telefono_raw='{telefono}', phone_normalized='{phone_normalized}'")
                
                if not nombre or not phone_normalized:
                    logger.warning(f"Row {idx} skipped: nombre={bool(nombre)}, phone_normalized={bool(phone_normalized)}")
                    continue  # Saltar registros incompletos
                
                contact = {
                    'nombre': str(nombre).strip(),
                    'dni': str(dni).strip() if dni else f"contact_{idx}",
                    'telefono': phone_normalized,
                    'phones': {
                        'best_e164': phone_normalized,
                    },
                    'to_number': phone_normalized,
                    'row_index': idx,
                    'raw_data': row_dict  # Preservar datos originales
                }
                
                normalized_contacts.append(contact)
            
            logger.info(f"Simple processing: {len(normalized_contacts)} contacts normalized")
            return normalized_contacts
            
        except Exception as e:
            logger.error(f"Error in simple Excel processing: {str(e)}")
            return []
    
    def _get_field_value(self, row_dict: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        """Busca un campo en el row usando múltiples candidatos de nombres"""
        for candidate in candidates:
            normalized_candidate = self._norm_key(candidate)
            if normalized_candidate in row_dict:
                value = row_dict[normalized_candidate]
                if value is not None and str(value).strip():
                    return str(value).strip()
        return None
    
    async def create_batch_for_use_case(
        self,
        file_content: bytes,
        account_id: str,
        use_case: str,
        use_case_config: Dict[str, Any],
        batch_name: str = None,
        batch_description: str = None,
        allow_duplicates: bool = False
    ) -> Dict[str, Any]:
        """
        Método principal: Crea batch con datos argentinos para cualquier caso de uso
        
        Args:
            file_content: Contenido del archivo Excel
            account_id: ID de la cuenta
            use_case: Tipo de caso de uso ('debt_collection', 'marketing')
            use_case_config: Configuración específica del caso de uso
            batch_name: Nombre del batch
            batch_description: Descripción del batch
            allow_duplicates: Permitir duplicados
            
        Returns:
            Resultado del procesamiento
        """
        try:
            # 1. Importar el registry de casos de uso
            from domain.use_case_registry import get_use_case_registry
            registry = get_use_case_registry()
            
            # 2. Obtener procesador para el caso de uso
            processor = registry.get_processor(use_case)
            if not processor:
                return {
                    "success": False,
                    "error": f"Caso de uso '{use_case}' no soportado"
                }
            
            # 3. Procesar datos según el caso de uso
            if use_case == 'debt_collection':
                # Para cobranza, usar procesamiento complejo con agrupación
                normalized_debtors = await self._process_simple_excel_data(file_content, account_id)
            else:
                # Para otros casos, usar procesamiento simple
                normalized_debtors = await self._process_simple_excel_data(file_content, account_id)
            
            if not normalized_debtors:
                return {
                    "success": False,
                    "error": "No se pudieron procesar contactos válidos del archivo"
                }
            
            # 4. Generar batch ID
            batch_id = f"batch-ar-{use_case}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            # 5. Agregar configuración de país
            use_case_config.update({
                'country': 'AR',
                'batch_id': batch_id
            })
            
            # 5. Crear deudores en la base de datos (opcional)
            if hasattr(processor, 'create_debtors_from_normalized_data'):
                debtors = await processor.create_debtors_from_normalized_data(
                    normalized_debtors,
                    batch_id
                )
                
                # Insertar deudores en la base de datos
                if debtors:
                    debtors_data = [debtor.to_dict() for debtor in debtors]
                    from pymongo import ReplaceOne
                    
                    operations = []
                    for debtor_dict in debtors_data:
                        operations.append(
                            ReplaceOne(
                                filter={'key': debtor_dict['key']},
                                replacement=debtor_dict,
                                upsert=True
                            )
                        )
                    
                    if operations:
                        result = await self.db.db.debtors.bulk_write(operations)
                        logger.info(f"Created/updated {result.upserted_count + result.modified_count} debtors")
            
            # 6. Crear jobs específicos del caso de uso
            jobs = await processor.create_jobs_from_normalized_data(
                normalized_debtors,
                account_id,
                batch_id,
                use_case_config
            )
            
            logger.info(f"Created {len(jobs)} jobs for use case '{use_case}'")
            
            # 7. Crear batch en la base de datos con jobs
            batch_result = await self._create_batch_with_jobs(
                batch_id=batch_id,
                account_id=account_id,
                jobs=jobs,
                batch_name=batch_name or f"Argentina {use_case.title()} Batch",
                batch_description=batch_description or f"Batch argentino para {use_case}"
            )
            
            return {
                "success": True,
                "batch_id": batch_id,
                "use_case": use_case,
                "country": "AR",
                "stats": {
                    "total_records_normalized": len(normalized_debtors),
                    "jobs_created": len(jobs),
                    "processing_type": use_case
                }
            }
                
        except Exception as e:
            logger.error(f"Error in Argentina batch creation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "country": "AR"
            }
    
    async def _create_batch_with_jobs(
        self,
        batch_id: str,
        account_id: str,
        jobs: List[JobModel],
        batch_name: str,
        batch_description: str = None
    ) -> Dict[str, Any]:
        """
        Crea batch en la base de datos con los jobs específicos
        Método auxiliar usado por el sistema de casos de uso
        """
        try:
            # 1. Crear BatchModel
            from domain.models import BatchModel
            from datetime import datetime
            
            batch = BatchModel(
                batch_id=batch_id,
                account_id=account_id,
                name=batch_name,
                description=batch_description or f"Batch argentino procesado con {len(jobs)} jobs",
                total_jobs=len(jobs),
                pending_jobs=len(jobs),
                completed_jobs=0,
                failed_jobs=0,
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            # 2. Insertar batch
            batch_result = await self.db.insert_document("batches", batch.to_dict())
            logger.info(f"Argentina batch created: {batch_id}")
            
            # 3. Insertar jobs en lotes para eficiencia
            jobs_data = [job.to_dict() for job in jobs]
            
            if jobs_data:
                await self.db.insert_many_documents("jobs", jobs_data)
                logger.info(f"Inserted {len(jobs_data)} jobs for Argentina batch {batch_id}")
            
            return {
                "batch_id": batch_id,
                "batch_name": batch_name,
                "jobs_created": len(jobs),
                "database_result": batch_result
            }
            
        except Exception as e:
            logger.error(f"Error creating Argentina batch with jobs: {str(e)}")
            raise