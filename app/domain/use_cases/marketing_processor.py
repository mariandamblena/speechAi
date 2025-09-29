"""
Procesador de casos de uso: MARKETING
Convierte datos normalizados → Jobs de marketing con contexto específico para Retell AI
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from ..models import JobModel, ContactInfo, BasePayload, DebtorModel
from ..enums import JobStatus


@dataclass  
class MarketingPayload(BasePayload):
    """Payload especializado para marketing"""
    
    # Campos específicos de marketing
    offer_description: str = ""
    discount_percentage: float = 0.0
    product_category: str = ""
    customer_segment: str = 'general'  # 'premium', 'standard', 'basic'
    campaign_type: str = 'promotional'  # 'promotional', 'retention', 'upsell'
    call_to_action: str = 'learn_more'  # 'learn_more', 'buy_now', 'schedule_demo'
    
    # Campos específicos de marketing (no de deuda)
    offer_value: float = 0.0  # Valor de la oferta
    offer_expires: str = ""   # Fecha de expiración de la oferta
    
    def to_retell_context(self) -> Dict[str, str]:
        """Contexto específico para IA de marketing"""
        context = super().to_retell_context()
        
        # Agregar contexto específico de marketing
        marketing_context = {
            'tipo_llamada': 'marketing',
            'descripcion_oferta': self.offer_description,
            'descuento_porcentaje': str(self.discount_percentage),
            'categoria_producto': self.product_category,
            'segmento_cliente': self.customer_segment,
            'tipo_campana': self.campaign_type,
            'llamada_accion': self.call_to_action,
            'valor_oferta': str(self.offer_value),
            'oferta_expira': self.offer_expires,
            'urgencia': 'alta' if self.discount_percentage > 50 else 'media'
        }
        
        return {**context, **marketing_context}


class MarketingProcessor:
    """
    Procesador especializado en MARKETING
    Responsabilidad: Convertir datos normalizados → Jobs de marketing
    """
    
    def __init__(self):
        self.use_case = 'marketing'
    
    async def create_debtors_from_normalized_data(
        self,
        normalized_contacts: List[Dict[str, Any]],
        batch_id: str
    ) -> List[DebtorModel]:
        """
        Convierte datos normalizados en modelos DebtorModel para la base de datos
        (Para marketing, los "deudores" son realmente contactos/prospects)
        
        Args:
            normalized_contacts: Lista de contactos ya normalizados por país
            batch_id: ID del batch que contendrá estos contactos
        """
        debtors = []
        
        for contact_data in normalized_contacts:
            # Para marketing, adaptamos el formato para DebtorModel
            # Crear DebtorModel desde los datos normalizados
            debtor = DebtorModel.from_dict(contact_data)
            debtors.append(debtor)
        
        return debtors
    
    async def create_jobs_from_normalized_data(
        self,
        normalized_contacts: List[Dict[str, Any]],
        account_id: str,
        batch_id: str, 
        config: Dict[str, Any]
    ) -> List[JobModel]:
        """
        Convierte contactos normalizados en jobs de marketing
        
        Args:
            normalized_contacts: Lista de contactos ya normalizados por país
            account_id: ID de la cuenta multi-tenant
            batch_id: ID del batch que contendrá estos jobs
            config: Configuración específica del caso de uso
        """
        jobs = []
        
        for contact in normalized_contacts:
            # Determinar segmento del cliente
            customer_segment = self._determine_customer_segment(contact, config)
            
            # Crear payload específico de marketing
            payload = MarketingPayload(
                company_name=config.get('company_name', ''),
                offer_description=config['offer_description'],
                discount_percentage=config.get('discount_percentage', 0.0),
                product_category=config.get('product_category', 'general'),
                customer_segment=customer_segment,
                campaign_type=config.get('campaign_type', 'promotional'),
                call_to_action=config.get('call_to_action', 'learn_more'),
                offer_value=config.get('offer_value', 0.0),
                offer_expires=config.get('offer_expires', ''),
                additional_info={
                    'campaign_id': config.get('campaign_id', batch_id),
                    'source': 'automated_call',
                    'batch_origen': batch_id
                }
            )
            
            # Crear ContactInfo
            phones = self._extract_phones(contact)
            contact_info = ContactInfo(
                name=contact.get('nombre', contact.get('name', '')),
                dni=contact.get('rut', contact.get('dni', '')),
                phones=phones
            )
            
            # Crear JobModel
            job = JobModel(
                account_id=account_id,
                batch_id=batch_id,
                contact=contact_info,
                payload=payload,
                status=JobStatus.PENDING,
                deduplication_key=f"{account_id}::{contact.get('rut', contact.get('dni', ''))}::{batch_id}",
                created_at=datetime.utcnow(),
                max_attempts=config.get('max_attempts', 2)  # Marketing: menos intentos
            )
            
            jobs.append(job)
        
        return jobs
    
    def _determine_customer_segment(self, contact: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Determina el segmento del cliente para personalizar la oferta"""
        
        # Lógica de segmentación personalizable
        segmentation_rules = config.get('segmentation_rules', {})
        
        # Segmentación por monto (para clientes existentes)
        if 'monto_total' in contact:
            monto = float(contact.get('monto_total', 0))
            if monto > segmentation_rules.get('premium_threshold', 100000):
                return 'premium'
            elif monto > segmentation_rules.get('standard_threshold', 50000):
                return 'standard'
            else:
                return 'basic'
        
        # Segmentación por cantidad de productos/cupones
        if 'cantidad_cupones' in contact:
            cantidad = int(contact.get('cantidad_cupones', 0))
            if cantidad > 5:
                return 'premium'
            elif cantidad > 2:
                return 'standard'
        
        # Default
        return config.get('default_segment', 'general')
    
    def _extract_phones(self, contact: Dict[str, Any]) -> List[str]:
        """Extrae lista de teléfonos del contacto normalizado"""
        phones = []
        
        # Si tiene estructura de phones (como deudores)
        if 'phones' in contact:
            phones_dict = contact['phones']
            if phones_dict.get('mobile_e164'):
                phones.append(phones_dict['mobile_e164'])
            if phones_dict.get('landline_e164') and phones_dict['landline_e164'] not in phones:
                phones.append(phones_dict['landline_e164'])
        
        # Si tiene teléfonos directos
        elif 'telefono' in contact or 'phone' in contact:
            phone = contact.get('telefono') or contact.get('phone')
            if phone:
                phones.append(str(phone))
        
        # Fallback
        if not phones and contact.get('to_number'):
            phones.append(contact['to_number'])
        
        return phones
    
    def get_script_template_id(self, country: str = 'CL', campaign_type: str = 'promotional') -> str:
        """Retorna el template ID para Retell AI según país y tipo de campaña"""
        templates = {
            'CL': {
                'promotional': 'chile_marketing_promotional_v1',
                'retention': 'chile_marketing_retention_v1', 
                'upsell': 'chile_marketing_upsell_v1'
            },
            'AR': {
                'promotional': 'argentina_marketing_promotional_v1',
                'retention': 'argentina_marketing_retention_v1',
                'upsell': 'argentina_marketing_upsell_v1'
            }
        }
        
        country_templates = templates.get(country, templates['CL'])
        return country_templates.get(campaign_type, 'default_marketing_v1')
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Valida configuración específica para marketing"""
        errors = []
        
        required_fields = ['company_name', 'offer_description', 'retell_agent_id']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"{field} es requerido para marketing")
        
        # Validar descuento
        discount = config.get('discount_percentage', 0)
        if not isinstance(discount, (int, float)) or discount < 0 or discount > 100:
            errors.append("discount_percentage debe ser un número entre 0 y 100")
        
        # Validar segmento
        valid_segments = ['general', 'premium', 'standard', 'basic']
        default_segment = config.get('default_segment', 'general')
        if default_segment not in valid_segments:
            errors.append(f"default_segment debe ser uno de: {valid_segments}")
        
        return errors