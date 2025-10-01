"""
Procesador de casos de uso: COBRANZA
Convierte datos normalizados → Jobs de cobranza con contexto específico para Retell AI
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass

from ..models import JobModel, ContactInfo, CallPayload, DebtorModel
from ..enums import JobStatus


@dataclass
class DebtCollectionPayload(CallPayload):
    """Payload especializado para cobranza con campos adicionales"""
    
    # Campos base heredados de CallPayload
    # debt_amount: float
    # due_date: str  
    # company_name: str
    # additional_info: Dict[str, Any]
    
    # Campos específicos de cobranza
    overdue_days: int = 0
    debt_type: str = 'consolidated'  # 'individual', 'consolidated'
    payment_options: List[str] = None
    
    def __post_init__(self):
        """Post-procesamiento tras inicialización del dataclass"""
        # No llamamos super().__init__() porque dataclass ya maneja la inicialización
        pass
        if self.payment_options is None:
            self.payment_options = ['full_payment', 'installment_plan']
    
    def to_retell_context(self) -> Dict[str, str]:
        """Contexto específico para IA de cobranza"""
        base_context = super().to_retell_context()
        
        # Agregar contexto específico de cobranza
        debt_context = {
            'tipo_llamada': 'cobranza',
            'dias_vencidos': str(self.overdue_days),
            'tipo_deuda': self.debt_type,
            'opciones_pago': '|'.join(self.payment_options),
            'urgencia': 'alta' if self.overdue_days > 30 else 'media' if self.overdue_days > 0 else 'baja',
            
            # Variables específicas requeridas por el prompt de Retell
            'cuotas_adeudadas': str(self.additional_info.get('cantidad_cupones', 1)),
            'fecha_limite': self._format_date_for_speech(self.due_date),  # Formato hablado
            'fecha_maxima': self._format_date_for_speech(self.additional_info.get('fecha_maxima', '')),
            'monto_total': str(int(self.debt_amount)),  # Sin decimales para el prompt
            'empresa': self.company_name,
            # El nombre se agrega desde JobModel.get_context_for_retell()
            
            # Información adicional para el contexto
            'cantidad_cupones': str(self.additional_info.get('cantidad_cupones', 1)),
            'rut': self.additional_info.get('rut', ''),
        }
        
        return {**base_context, **debt_context}

    def _format_date_for_speech(self, iso_date: str) -> str:
        """Convierte fecha ISO (2025-09-28) a formato legible para voz"""
        if not iso_date:
            return ""
        
        try:
            # Parsear fecha ISO
            if 'T' in iso_date:  # Si tiene hora, extraer solo fecha
                iso_date = iso_date.split('T')[0]
            
            from datetime import datetime
            date_obj = datetime.fromisoformat(iso_date)
            
            # Mapeo de meses en español
            meses = [
                '', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
            ]
            
            dia = date_obj.day
            mes = meses[date_obj.month]
            año = date_obj.year
            
            return f"{dia} de {mes} de {año}"
        except (ValueError, IndexError):
            return iso_date  # Fallback: retornar fecha original


class DebtCollectionProcessor:
    """
    Procesador especializado en COBRANZA
    Responsabilidad: Convertir datos normalizados → Jobs de cobranza
    """
    
    def __init__(self):
        self.use_case = 'debt_collection'
    
    async def create_debtors_from_normalized_data(
        self,
        normalized_debtors: List[Dict[str, Any]],
        batch_id: str
    ) -> List[DebtorModel]:
        """
        Convierte datos normalizados en modelos DebtorModel para la base de datos
        
        Args:
            normalized_debtors: Lista de deudores ya normalizados por país
            batch_id: ID del batch que contendrá estos deudores
        """
        debtors = []
        
        for debtor_data in normalized_debtors:
            # Crear DebtorModel desde los datos normalizados
            debtor = DebtorModel.from_dict(debtor_data)
            debtors.append(debtor)
        
        return debtors
    
    async def create_jobs_from_normalized_data(
        self,
        normalized_debtors: List[Dict[str, Any]],
        account_id: str, 
        batch_id: str,
        config: Dict[str, Any]
    ) -> List[JobModel]:
        """
        Convierte deudores normalizados en jobs de cobranza
        
        Args:
            normalized_debtors: Lista de deudores ya normalizados por país
            account_id: ID de la cuenta multi-tenant
            batch_id: ID del batch que contendrá estos jobs
            config: Configuración específica del caso de uso
        """
        jobs = []
        
        for debtor in normalized_debtors:
            # Calcular días de atraso
            overdue_days = self._calculate_overdue_days(debtor)
            
            # Crear payload específico de cobranza
            payload = DebtCollectionPayload(
                debt_amount=float(debtor.get('monto_total', 0)),
                due_date=debtor.get('fecha_limite', ''),
                company_name=config.get('company_name', debtor.get('origen_empresa', '')),
                overdue_days=overdue_days,
                debt_type='consolidated',  # Siempre consolidado por RUT
                payment_options=config.get('payment_options', ['full_payment', 'installment_plan']),
                additional_info={
                    'cantidad_cupones': debtor.get('cantidad_cupones', 1),
                    'fecha_maxima': debtor.get('fecha_maxima', ''),
                    'rut': debtor.get('rut', ''),
                    'batch_origen': batch_id
                }
            )
            
            # Crear ContactInfo
            phones = self._extract_phones(debtor)
            contact = ContactInfo(
                name=debtor.get('nombre', ''),
                dni=debtor.get('rut', ''),
                phones=phones
            )
            
            # Crear JobModel
            job = JobModel(
                account_id=account_id,
                batch_id=batch_id,
                contact=contact,
                payload=payload,
                status=JobStatus.PENDING,
                deduplication_key=f"{account_id}::{debtor.get('rut', '')}::{batch_id}",
                created_at=datetime.utcnow(),
                max_attempts=config.get('max_attempts', 3)
            )
            
            jobs.append(job)
        
        return jobs
    
    def _calculate_overdue_days(self, debtor: Dict[str, Any]) -> int:
        """Calcula días de atraso basado en fecha_limite"""
        fecha_limite = debtor.get('fecha_limite')
        if not fecha_limite:
            return 0
        
        try:
            # Convertir fecha_limite a datetime
            if isinstance(fecha_limite, str):
                fecha_dt = datetime.fromisoformat(fecha_limite).date()
            else:
                fecha_dt = fecha_limite
            
            # Calcular diferencia con hoy
            today = date.today()
            delta = (today - fecha_dt).days
            
            return max(0, delta)  # No días negativos
            
        except (ValueError, TypeError):
            return 0
    
    def _extract_phones(self, debtor: Dict[str, Any]) -> List[str]:
        """Extrae lista de teléfonos del deudor normalizado"""
        phones = []
        phones_dict = debtor.get('phones', {})
        
        # Prioridad: móvil, fijo, mejor
        if phones_dict.get('mobile_e164'):
            phones.append(phones_dict['mobile_e164'])
        
        if phones_dict.get('landline_e164') and phones_dict['landline_e164'] not in phones:
            phones.append(phones_dict['landline_e164'])
        
        if phones_dict.get('best_e164') and phones_dict['best_e164'] not in phones:
            phones.append(phones_dict['best_e164'])
        
        # Fallback: al menos un teléfono
        if not phones and debtor.get('to_number'):
            phones.append(debtor['to_number'])
        
        return phones
    
    def get_script_template_id(self, country: str = 'CL') -> str:
        """Retorna el template ID para Retell AI según país"""
        templates = {
            'CL': 'chile_debt_collection_v1',
            'AR': 'argentina_debt_collection_v1',
            'MX': 'mexico_debt_collection_v1'
        }
        return templates.get(country, 'default_debt_collection_v1')
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración específica para cobranza"""
        errors = []
        
        if not config.get('company_name'):
            errors.append("company_name es requerido para cobranza")
        
        if not config.get('retell_agent_id'):
            errors.append("retell_agent_id es requerido")
        
        max_attempts = config.get('max_attempts', 3)
        if not isinstance(max_attempts, int) or max_attempts < 1 or max_attempts > 10:
            errors.append("max_attempts debe ser un entero entre 1 y 10")
        
        return errors