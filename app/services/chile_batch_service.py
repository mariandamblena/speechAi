"""
Servicio de carga de batches con lógica específica para Chile
Normalización de RUT, teléfonos +56, y fechas DD/MM/YYYY
Soporta múltiples casos de uso a través del sistema de procesadores
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
import logging
import re
from decimal import Decimal

from domain.models import BatchModel, JobModel, DebtorModel, ContactInfo, CallPayload
from domain.enums import JobStatus, CallMode, AccountStatus
from infrastructure.database_manager import DatabaseManager
from utils.excel_processor import ExcelDebtorProcessor
from services.account_service import AccountService

logger = logging.getLogger(__name__)


class ChileBatchService:
    """Servicio de carga de batches con lógica específica para Chile
    Incluye normalización de RUT, teléfonos chilenos (+56) y fechas DD/MM/YYYY
    Ahora soporta múltiples casos de uso: cobranza, marketing, etc.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.excel_processor = ExcelDebtorProcessor()
        self.account_service = AccountService(db_manager)
        
        # Configuración para Chile
        self.country_config = {
            'country': 'CL',
            'default_area_code': '2'
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
    
    def _norm_rut(self, rut_raw: Any) -> Optional[str]:
        """Normaliza RUT chileno removiendo puntos y guiones"""
        if rut_raw is None or rut_raw == '':
            return None
        
        # Quitar puntos y guion, mantener mayúsculas
        rut_clean = str(rut_raw).replace('.', '').replace('-', '').strip().upper()
        return rut_clean if rut_clean else None
    
    def _to_number_pesos(self, value: Any) -> float:
        """Convierte valor a pesos (no centavos)"""
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
    
    def _to_int(self, value: Any, default: int = 0) -> int:
        """Convierte valor a entero"""
        if value is None or value == '':
            return default
        
        try:
            # Limpiar y convertir
            clean_str = re.sub(r'[^\d\-]', '', str(value))
            return int(clean_str) if clean_str else default
        except ValueError:
            return default
    
    def _split_phones(self, raw_phone: str) -> List[str]:
        """Genera candidatos de número telefónico"""
        if not raw_phone:
            return []
        
        phone_str = str(raw_phone).strip()
        
        # Separar por caracteres no dígitos
        parts = re.split(r'\D+', phone_str)
        parts = [p for p in parts if p]  # Filtrar vacíos
        
        # Todos los dígitos juntos
        all_digits = re.sub(r'\D+', '', phone_str)
        
        candidates = set()
        if all_digits:
            candidates.add(all_digits)
        
        for part in parts:
            candidates.add(part)
        
        # Si hay al menos 2 partes y la primera es corta (código área), unir primeras dos
        if len(parts) >= 2 and len(parts[0]) <= 3:
            candidates.add(parts[0] + parts[1])
        
        return list(candidates)
    
    def _norm_cl_phone(self, raw_phone: Any, kind: str = 'any') -> Optional[str]:
        """
        Normaliza teléfonos chilenos a formato E.164 (+56XXXXXXXXX)
        
        Args:
            raw_phone: Número crudo
            kind: 'mobile', 'landline', 'any'
        
        Returns:
            Número normalizado en formato +56XXXXXXXXX o None
        """
        if raw_phone is None or raw_phone == '':
            return None
        
        want_mobile = kind == 'mobile'
        want_landline = kind == 'landline'
        want_any = kind == 'any'
        
        candidates = self._split_phones(str(raw_phone))
        
        for number in candidates:
            # 1. Remover código país y trunk
            if number.startswith('56'):
                number = number[2:]
            
            # Remover ceros iniciales (trunk)
            number = re.sub(r'^0+', '', number)
            
            # 2. Heurísticas para casos frecuentes
            
            # Móviles que llegan como "5699xxxxxxxx" -> "99xxxxxxxx" (10 dígitos)
            if len(number) == 10 and number.startswith('99'):
                number = number[1:]  # -> "9xxxxxxxx" (9 dígitos)
            
            # Móvil legado: 8 dígitos empezando con 9 -> anteponer 9
            # Ej: "09-2125907" -> "92125907" -> "992125907"
            if len(number) == 8 and number[0] == '9':
                number = '9' + number
            
            # Fijo Santiago legado: "2" + 7 dígitos -> anteponer otro '2'
            # Ej: "02-8151807" -> "28151807" -> "228151807"
            if len(number) == 8 and number[0] == '2' and not number.startswith('22'):
                number = '2' + number
            
            # 3. Normalización por tipo
            if want_mobile and len(number) == 8 and number[0] != '9':
                number = '9' + number
            
            if (want_landline or want_any) and len(number) in [7, 8] and number[0] != '9':
                area_code = self.country_config.get('default_area_code', '2')
                number = area_code + number
            
            # 4. Validación final
            if len(number) != 9:
                continue
            
            is_mobile = number.startswith('9')
            
            if want_mobile and not is_mobile:
                continue
            if want_landline and is_mobile:
                continue
            
            return f'+56{number}'
        
        return None
    
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
    
    def _to_iso_date(self, value: Any) -> Optional[str]:
        """Convierte fecha a formato ISO (YYYY-MM-DD), priorizando formato chileno"""
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
        
        # 2. Formato chileno: DD/MM/YYYY o DD-MM-YYYY
        cl_pattern = r'^(\d{1,2})[\\/\-](\d{1,2})[\\/\-](\d{2,4})$'
        match = re.match(cl_pattern, value_str)
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
        
        # 4. Intento genérico
        try:
            parsed_date = datetime.strptime(value_str, '%Y-%m-%d')
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
    
    def _process_acquisition_data(self, rows: List[Dict]) -> List[Dict]:
        """
        Procesa datos con lógica de adquisición (agrupación por RUT)
        
        Lógica:
        - Agrupa por RUT
        - fecha_limite = (FechaVencimiento MÁS GRANDE del RUT) + diasRetraso + 3 días
        - fecha_maxima = (FechaVencimiento MÁS CHICA del RUT) + diasRetraso + 7 días
        - Suma montos y cuenta cupones por RUT
        """
        batch_id = f"batch-{datetime.utcnow().strftime('%Y-%m-%d-%H%M%S')}"
        now_cl = datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p CLT')  # Solo para mostrar al usuario
        
        by_rut = {}
        
        for i, row in enumerate(rows):
            # Crear índice de claves normalizadas
            key_index = {}
            for key in row.keys():
                key_index[self._norm_key(key)] = key
            
            # Extraer campos principales
            rut = self._norm_rut(self._get_field(row, key_index, ['RUTS', 'RUT']))
            nombre = str(self._get_field(row, key_index, ['Nombre']) or '').strip()
            empresa = str(self._get_field(row, key_index, [
                'Origen Empresa', 'OrigenEmpresa', 'Empresa'
            ]) or '').strip()
            saldo = self._to_number_pesos(self._get_field(row, key_index, [
                'Saldo actualizado', 'Saldo Actualizado', ' Saldo actualizado '
            ]))
            
            # Fechas y días
            fecha_venc = self._to_iso_date(self._get_field(row, key_index, [
                'FechaVencimiento', 'Fecha Vencimiento', 'Fecha vencimiento', 
                'Vencimiento', 'Fecha de Vencimiento'
            ]))
            
            dias_retraso = self._to_int(self._get_field(row, key_index, [
                'diasRetraso',  # header real confirmado
                'Días de retraso', 'Dias de retraso', 'Días de atraso', 'Dias de atraso',
                'Dias retraso', 'Días retraso', 'dias_de_retraso', 'diasretraso',
                'dias atraso', 'dias_atraso'
            ]))
            
            # Teléfonos
            mobile_raw = self._get_field(row, key_index, [
                'Teléfono móvil', 'Telefono movil', 'Teléfono celular', 'Celular'
            ])
            landline_raw = self._get_field(row, key_index, [
                'Teléfono Residencial', 'Telefono residencial', 'Teléfono fijo', 'Telefono fijo'
            ])
            
            mobile = self._norm_cl_phone(mobile_raw, 'mobile')
            landline = self._norm_cl_phone(landline_raw, 'landline') or self._norm_cl_phone(landline_raw, 'any')
            best_phone = mobile or landline
            
            if not rut:
                logger.warning(f"Row {i}: Missing RUT, skipping")
                continue
            
            # Inicializar o actualizar RUT
            if rut not in by_rut:
                by_rut[rut] = {
                    'batch_id': batch_id,
                    'rut': rut,
                    'nombre': nombre,
                    'origen_empresa': empresa or None,
                    'phones': {
                        'raw_mobile': mobile_raw,
                        'raw_landline': landline_raw,
                        'mobile_e164': mobile,
                        'landline_e164': landline,
                        'best_e164': best_phone
                    },
                    'cantidad_cupones': 0,
                    'monto_total': 0.0,
                    '_max_base': None,  # {'fv': 'YYYY-MM-DD', 'dias': N}
                    '_min_base': None,  # {'fv': 'YYYY-MM-DD', 'dias': N}
                    'fecha_limite': None,
                    'fecha_maxima': None,
                    'debug': {'max_base': None, 'min_base': None}
                }
            
            debtor = by_rut[rut]
            
            # Acumular datos
            debtor['cantidad_cupones'] += 1
            debtor['monto_total'] += saldo
            
            # Completar teléfonos si faltan
            if not debtor['phones']['mobile_e164'] and mobile:
                debtor['phones']['mobile_e164'] = mobile
            if not debtor['phones']['landline_e164'] and landline:
                debtor['phones']['landline_e164'] = landline
            if not debtor['phones']['best_e164'] and best_phone:
                debtor['phones']['best_e164'] = best_phone
            
            # Registrar fechas máximas/mínimas con sus días de retraso
            if fecha_venc:
                if not debtor['_max_base'] or fecha_venc > debtor['_max_base']['fv']:
                    debtor['_max_base'] = {'fv': fecha_venc, 'dias': dias_retraso}
                    debtor['debug']['max_base'] = debtor['_max_base']
                
                if not debtor['_min_base'] or fecha_venc < debtor['_min_base']['fv']:
                    debtor['_min_base'] = {'fv': fecha_venc, 'dias': dias_retraso}
                    debtor['debug']['min_base'] = debtor['_min_base']
        
        # Calcular fechas finales
        processed_debtors = []
        
        for rut, debtor in by_rut.items():
            # Calcular fechas límite según lógica del workflow
            if debtor['_max_base']:
                dias_extra = debtor['_max_base']['dias'] + 3
                debtor['fecha_limite'] = self._add_days_iso(debtor['_max_base']['fv'], dias_extra)
            
            if debtor['_min_base']:
                dias_extra = debtor['_min_base']['dias'] + 7
                debtor['fecha_maxima'] = self._add_days_iso(debtor['_min_base']['fv'], dias_extra)
            
            # Limpiar campos internos
            del debtor['_max_base']
            del debtor['_min_base']
            
            # Agregar campos para job
            debtor.update({
                'to_number': debtor['phones']['best_e164'],
                'key': f"{batch_id}::{rut}",
                'created_at': datetime.utcnow().isoformat(),
                'current_time_america_santiago': now_cl
            })
            
            processed_debtors.append(debtor)
        
        return processed_debtors
    
    async def _process_simple_excel_data(self, file_content: bytes, account_id: str) -> List[Dict[str, Any]]:
        """
        Procesamiento simple para casos de uso no-cobranza
        Sin agrupación por RUT, procesamiento directo 1:1
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
                
                # Para marketing/otros casos, puede no ser RUT
                dni = self._get_field_value(row_dict, ['rut', 'dni', 'id', 'cedula', 'identificacion'])
                
                # Teléfonos
                telefono = self._get_field_value(row_dict, [
                    'telefono', 'phone', 'telefono movil', 'celular', 'mobile'
                ])
                
                # Normalizar teléfono chileno
                phone_normalized = self._norm_cl_phone(telefono, 'any')
                
                if not nombre or not phone_normalized:
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
        Método principal: Crea batch con datos chilenos para cualquier caso de uso
        
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
            
            # 2. Validar caso de uso
            if use_case not in registry.get_available_use_cases():
                raise ValueError(f"Caso de uso '{use_case}' no soportado. Disponibles: {registry.get_available_use_cases()}")
            
            # 3. Validar configuración del caso de uso
            config_errors = registry.validate_use_case_config(use_case, use_case_config)
            if config_errors:
                raise ValueError(f"Configuración inválida: {'; '.join(config_errors)}")
            
            # 4. Verificar cuenta
            account = await self.account_service.get_account(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            if account.status != AccountStatus.ACTIVE:
                raise ValueError(f"Account {account_id} is not active (status: {account.status})")
            
            # 5. NORMALIZACIÓN CHILENA (siempre igual, independiente del caso de uso)
            if use_case == 'debt_collection':
                # Para cobranza, usar lógica avanzada de agrupación por RUT
                excel_result = self.excel_processor.process_excel_data(file_content, account_id)
                normalized_data = excel_result['debtors']
                batch_id = excel_result['batch_id']
            else:
                # Para otros casos de uso, procesar directamente (sin agrupación compleja)
                normalized_data = await self._process_simple_excel_data(file_content, account_id)
                batch_id = f"batch-{use_case}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            logger.info(f"Normalized {len(normalized_data)} records for use case '{use_case}'")
            
            if not normalized_data:
                return {
                    "success": False,
                    "error": "No valid data found after normalization"
                }
            
            # 6. DELEGACIÓN AL PROCESADOR ESPECÍFICO
            processor = registry.get_processor(use_case)
            
            # Agregar configuración de país
            use_case_config.update({
                'country': 'CL',
                'batch_id': batch_id
            })
            
            # 6. Crear deudores en la base de datos
            if hasattr(processor, 'create_debtors_from_normalized_data'):
                debtors = await processor.create_debtors_from_normalized_data(
                    normalized_data,
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
                        result = await self.db_manager.db.debtors.bulk_write(operations)
                        logger.info(f"Created/updated {result.upserted_count + result.modified_count} debtors")
            
            # 7. Crear jobs específicos del caso de uso
            jobs = await processor.create_jobs_from_normalized_data(
                normalized_data,
                account_id,
                batch_id,
                use_case_config
            )
            
            logger.info(f"Created {len(jobs)} jobs for use case '{use_case}'")
            
            # 8. Crear batch en la base de datos
            batch_result = await self._create_batch_with_jobs(
                batch_id=batch_id,
                account_id=account_id,
                jobs=jobs,
                batch_name=batch_name or f"Chile {use_case.title()} Batch",
                batch_description=batch_description or f"Batch chileno para {use_case}"
            )
            
            return {
                "success": True,
                "batch_id": batch_id,
                "use_case": use_case,
                "country": "CL",
                "stats": {
                    "total_records_normalized": len(normalized_data),
                    "jobs_created": len(jobs),
                    "processing_type": use_case
                },
                "batch_result": batch_result
            }
            
        except Exception as e:
            logger.error(f"Error creating batch for use case '{use_case}': {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "use_case": use_case
            }
    
    async def create_batch_from_excel_acquisition(
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
        Crea batch usando lógica de adquisición avanzada
        
        Args:
            file_content: Contenido del archivo Excel
            account_id: ID de la cuenta
            batch_name: Nombre del batch
            batch_description: Descripción del batch
            allow_duplicates: Permitir duplicados
            dias_fecha_limite: Días a sumar a fecha actual para fecha_limite
            dias_fecha_maxima: Días a sumar a fecha actual para fecha_maxima
            call_settings: Configuración de llamadas específica para este batch
            
        Returns:
            Resultado del procesamiento
        """
        try:
            # 1. Verificar cuenta
            account = await self.account_service.get_account(account_id)
            if not account:
                raise ValueError(f"Account {account_id} not found")
            
            if account.status != AccountStatus.ACTIVE:
                raise ValueError(f"Account {account_id} is not active (status: {account.status})")
            
            # 2. Procesar Excel con el procesador existente (que ya tiene lógica de adquisición)
            excel_result = self.excel_processor.process_excel_data(file_content, account_id)
            
            # El excel_processor ya devuelve los datos procesados y agrupados
            batch_id = excel_result['batch_id']
            processed_debtors = excel_result['debtors']
            
            logger.info(f"Excel processing result: {len(processed_debtors)} unique debtors from processor")
            
            if not processed_debtors:
                return {
                    "success": False,
                    "error": "No valid debtors found after processing"
                }
            
            # 3. Verificar duplicados si no están permitidos
            valid_debtors = []
            existing_ruts = []
            
            if not allow_duplicates:
                # Buscar RUTs existentes en la base
                ruts_to_check = [d['rut'] for d in processed_debtors]
                existing_docs = await self.db.find_documents(
                    "debtors",
                    {"rut": {"$in": ruts_to_check}}
                )
                existing_ruts = [doc['rut'] for doc in existing_docs]
                
                # Filtrar duplicados
                for debtor in processed_debtors:
                    if debtor['rut'] not in existing_ruts:
                        valid_debtors.append(debtor)
                
                if not valid_debtors:
                    return {
                        "success": False,
                        "error": "All debtors are duplicates",
                        "duplicates_count": len(existing_ruts),
                        "total_processed": len(processed_debtors)
                    }
            else:
                valid_debtors = processed_debtors
            
            # 4. Crear batch
            batch_name = batch_name or f"Acquisition Batch {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            
            # Generar un batch_id único usando timestamp + microsegundos
            batch_id_unique = f"batch-acq-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{datetime.utcnow().microsecond}"
            
            batch = BatchModel(
                account_id=account_id,
                batch_id=batch_id_unique,  # Usar el ID único generado
                name=batch_name,
                description=batch_description or f"Acquisition batch with {len(valid_debtors)} debtors",
                total_jobs=len(valid_debtors),
                pending_jobs=len(valid_debtors),
                completed_jobs=0,
                failed_jobs=0,
                is_active=True,
                call_settings=call_settings,  # Agregar call_settings
                created_at=datetime.utcnow(),
                priority=1
            )
            
            # Guardar batch
            batch_result = await self.db.insert_document("batches", batch.to_dict())
            batch.id = str(batch_result.inserted_id)
            
            # Usar el batch_id único para los deudores y jobs
            
            # Calcular fechas dinámicas si se especificaron los días
            fecha_limite_calculada = None
            fecha_maxima_calculada = None
            
            if dias_fecha_limite is not None:
                fecha_limite_calculada = (datetime.utcnow() + timedelta(days=dias_fecha_limite)).strftime('%Y-%m-%d')
                logger.info(f"Fecha límite calculada dinámicamente: HOY + {dias_fecha_limite} días = {fecha_limite_calculada}")
            
            if dias_fecha_maxima is not None:
                fecha_maxima_calculada = (datetime.utcnow() + timedelta(days=dias_fecha_maxima)).strftime('%Y-%m-%d')
                logger.info(f"Fecha máxima calculada dinámicamente: HOY + {dias_fecha_maxima} días = {fecha_maxima_calculada}")
            
            # 5. Crear jobs y debtors
            jobs_created = 0
            debtors_created = 0
            
            for debtor_data in valid_debtors:
                try:
                    # Determinar qué fechas usar: calculadas dinámicamente o las del Excel
                    fecha_limite_final = fecha_limite_calculada if fecha_limite_calculada else debtor_data.get('fecha_limite')
                    fecha_maxima_final = fecha_maxima_calculada if fecha_maxima_calculada else debtor_data.get('fecha_maxima')
                    
                    # Crear debtor usando el modelo DebtorModel diseñado para esto
                    debtor = DebtorModel(
                        batch_id=batch.batch_id,  # Usar batch_id único
                        rut=debtor_data['rut'],
                        rut_fmt=debtor_data.get('rut_fmt', debtor_data['rut']),
                        nombre=debtor_data['nombre'],
                        origen_empresa=debtor_data['origen_empresa'],
                        phones=debtor_data['phones'],
                        cantidad_cupones=debtor_data['cantidad_cupones'],
                        monto_total=debtor_data['monto_total'],
                        fecha_limite=fecha_limite_final,
                        fecha_maxima=fecha_maxima_final,
                        to_number=debtor_data['phones'].get('best_e164'),
                        key=debtor_data.get('key', f"{batch.batch_id}::{debtor_data['rut']}"),  # Usar batch_id único
                        created_at=datetime.utcnow()
                    )
                    
                    debtor_result = await self.db.insert_document("debtors", debtor.to_dict())
                    debtors_created += 1
                    
                    # Crear job con la estructura correcta
                    contact_info = ContactInfo(
                        name=debtor_data['nombre'],
                        dni=debtor_data['rut'],
                        phones=[phone for phone in [
                            debtor_data['phones'].get('mobile_e164'),
                            debtor_data['phones'].get('landline_e164')
                        ] if phone]
                    )
                    
                    call_payload = CallPayload(
                        debt_amount=debtor_data['monto_total'],
                        due_date=fecha_limite_final or '',
                        company_name=debtor_data.get('origen_empresa', ''),
                        reference_number=debtor_data['rut'],
                        additional_info={
                            "rut": debtor_data['rut'],
                            "nombre": debtor_data['nombre'],
                            "cantidad_cupones": debtor_data['cantidad_cupones'],
                            "fecha_maxima": fecha_maxima_final or '',
                            "current_time_america_santiago": debtor_data.get('current_time_america_santiago', '')
                        }
                    )
                    
                    job = JobModel(
                        account_id=account_id,
                        batch_id=batch.batch_id,  # Usar batch_id único
                        contact=contact_info,
                        payload=call_payload,
                        status=JobStatus.PENDING,
                        max_attempts=3,
                        attempts=0,
                        created_at=datetime.utcnow(),
                        mode=CallMode.SINGLE
                    )
                    
                    await self.db.insert_document("jobs", job.to_dict())
                    jobs_created += 1
                    
                except Exception as e:
                    logger.error(f"Error creating job for RUT {debtor_data.get('rut', 'unknown')}: {str(e)}")
                    continue
            
            # 6. Actualizar batch con contadores finales
            await self.db.update_document(
                "batches",
                {"_id": batch_result.inserted_id},
                {
                    "$set": {
                        "total_jobs": jobs_created,
                        "pending_jobs": jobs_created,
                        "completed_jobs": 0,
                        "failed_jobs": 0
                    }
                }
            )
            
            return {
                "success": True,
                "batch_id": batch.batch_id,  # Usar batch_id único
                "batch_name": batch_name,
                "processing_type": "acquisition",
                "stats": {
                    "total_rows_processed": excel_result.get('total_rows', len(processed_debtors)),
                    "unique_debtors_found": len(processed_debtors),
                    "valid_debtors": len(valid_debtors),
                    "duplicates_filtered": len(processed_debtors) - len(valid_debtors),
                    "existing_duplicates": len(existing_ruts),
                    "jobs_created": jobs_created,
                    "debtors_created": debtors_created
                }
            }
            
        except Exception as e:
            logger.error(f"Error in acquisition batch creation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "processing_type": "acquisition"
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
            batch = BatchModel(
                batch_id=batch_id,
                account_id=account_id,
                name=batch_name,
                description=batch_description or f"Batch procesado con {len(jobs)} jobs",
                total_jobs=len(jobs),
                pending_jobs=len(jobs),
                completed_jobs=0,
                failed_jobs=0,
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            # 2. Insertar batch
            batch_result = await self.db.insert_document("batches", batch.to_dict())
            logger.info(f"Batch created: {batch_id}")
            
            # 3. Insertar jobs en lotes para eficiencia
            jobs_data = [job.to_dict() for job in jobs]
            
            if jobs_data:
                await self.db.insert_many_documents("jobs", jobs_data)
                logger.info(f"Inserted {len(jobs_data)} jobs for batch {batch_id}")
            
            return {
                "batch_id": batch_id,
                "batch_name": batch_name,
                "jobs_created": len(jobs),
                "database_result": batch_result
            }
            
        except Exception as e:
            logger.error(f"Error creating batch with jobs: {str(e)}")
            raise