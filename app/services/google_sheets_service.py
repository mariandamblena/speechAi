"""
Servicio para procesar datos de Google Sheets
Integra la lógica del workflow de adquisición N8N
"""

import re
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, date
import logging
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """
    Servicio para procesar datos de Google Sheets siguiendo la lógica 
    del workflow de adquisición N8N (Adquisicion_v3.json)
    """
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    def __init__(self):
        self.service = None
        self.cfg = {
            'country': 'CL',
            'defaultAreaCodeCL': '2'
        }
    
    def authenticate(self, credentials_json_path: str, token_path: str = None):
        """Autentica con Google Sheets API"""
        try:
            creds = None
            if token_path:
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_json_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                
                if token_path:
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
            
            self.service = build('sheets', 'v4', credentials=creds)
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Sheets: {e}")
            return False
    
    def _norm_key(self, k: str) -> str:
        """Normaliza claves siguiendo lógica N8N"""
        import unicodedata
        
        result = str(k)
        # Quitar acentos
        result = unicodedata.normalize('NFD', result)
        result = ''.join(c for c in result if unicodedata.category(c) != 'Mn')
        
        # Limpiar espacios y caracteres especiales
        result = re.sub(r'\s+', ' ', result.strip().lower())
        result = re.sub(r'[^\w ]', '', result)
        result = re.sub(r'\s+', ' ', result)
        
        return result
    
    def _norm_rut(self, rut_raw: Any) -> Optional[str]:
        """Normaliza RUT chileno"""
        if rut_raw is None or rut_raw == '':
            return None
        
        # Quitar puntos y guiones
        return str(rut_raw).replace('.', '').replace('-', '').strip().upper()
    
    def _to_number_pesos(self, val: Any) -> float:
        """Convierte a pesos (no centavos) siguiendo lógica N8N"""
        if val is None or val == '':
            return 0.0
        
        if isinstance(val, (int, float)):
            return float(val)
        
        s = str(val).strip()
        s = s.replace(' ', '').replace('$', '').replace('.', '').replace(',', '.')
        
        try:
            n = float(s)
            return n if isinstance(n, (int, float)) and not (n != n) else 0.0  # Check for NaN
        except ValueError:
            return 0.0
    
    def _to_int(self, v: Any, default: int = 0) -> int:
        """Convierte a entero"""
        if v is None or v == '':
            return default
        
        try:
            s = str(v)
            s = re.sub(r'[^\d\-]', '', s)
            n = int(s) if s else default
            return n if isinstance(n, int) and not (n != n) else default
        except ValueError:
            return default
    
    def _split_phones(self, raw: Any) -> List[str]:
        """Genera candidatos de número siguiendo lógica N8N"""
        s = str(raw or '').strip()
        parts = [p for p in re.split(r'\D+', s) if p]  # Separar por no-dígitos
        all_digits = re.sub(r'\D+', '', s)  # Todo pegado
        
        out = set()
        if all_digits:
            out.add(all_digits)
        
        for p in parts:
            out.add(p)
        
        # Pegado de los dos primeros grupos cortos
        if len(parts) >= 2 and len(parts[0]) <= 3:
            out.add(parts[0] + parts[1])
        
        return list(out)
    
    def _norm_cl_phone(self, raw: Any, kind: str = None) -> Optional[str]:
        """
        Normaliza teléfono chileno a formato E.164 (+56XXXXXXXXX)
        kind: 'mobile', 'landline', 'any'/None
        """
        if raw is None or raw == '':
            return None
        
        want_mobile = kind == 'mobile'
        want_landline = kind == 'landline'
        want_any = not want_mobile and not want_landline
        
        parts = self._split_phones(raw)
        
        for n in parts:
            # Quitar país y trunk
            if n.startswith('56'):
                n = n[2:]
            n = re.sub(r'^0+', '', n)  # Quita 0 de trunk (09-, 02-, etc.)
            
            # Heurísticas específicas Chile
            
            # Móviles que llegan como "5699xxxxxxxx" -> tras quitar 56 queda "99xxxxxxxxxx"
            if len(n) == 10 and n.startswith('99'):
                n = n[1:]  # Queda "9xxxxxxxx"
            
            # Móvil legado con 8 dígitos que empieza con 9
            if len(n) == 8 and n[0] == '9':
                n = '9' + n
            
            # Fijo Santiago legado: "2"+"7 dígitos"
            if len(n) == 8 and n[0] == '2' and not n.startswith('22'):
                n = '2' + n
            
            # Normalización general por tipo
            if want_mobile and len(n) == 8 and n[0] != '9':
                n = '9' + n
            
            if (want_landline or want_any) and len(n) in [7, 8] and n[0] != '9':
                n = (self.cfg['defaultAreaCodeCL'] or '2') + n
            
            # Validación final
            if len(n) != 9:
                continue
                
            looks_mobile = n.startswith('9')
            if want_mobile and not looks_mobile:
                continue
            if want_landline and looks_mobile:
                continue
            
            return '+56' + n
        
        return None
    
    def _get_field(self, row: Dict[str, Any], key_index: Dict[str, str], candidates: List[str]) -> Any:
        """Busca campo en row usando candidatos de nombres"""
        for c in candidates:
            nk = self._norm_key(c)
            if nk in key_index:
                return row.get(key_index[nk])
        
        # Búsqueda parcial
        for nk in key_index:
            for c in candidates:
                if self._norm_key(c) in nk:
                    return row.get(key_index[nk])
        
        return None
    
    def _to_iso(self, v: Any) -> Optional[str]:
        """Convierte fechas a YYYY-MM-DD priorizando formato chileno"""
        if v is None or v == '':
            return None
        
        # Excel serial
        if isinstance(v, (int, float)):
            try:
                base = datetime(1899, 12, 30)
                d = base + datetime.timedelta(days=round(float(v)))
                return d.strftime('%Y-%m-%d')
            except (ValueError, OverflowError):
                return None
        
        s = str(v).strip()
        
        # DD/MM/YYYY o DD-MM-YYYY (estándar CL)
        m = re.match(r'^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})$', s)
        if m:
            dd, mm, yyyy = m.groups()
            if len(yyyy) == 2:
                yyyy = '20' + yyyy
            
            try:
                y, M, D = int(yyyy), int(mm), int(dd)
                if 1 <= M <= 12 and 1 <= D <= 31:
                    dt = date(y, M, D)
                    return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # Otros formatos
        try:
            dt = datetime.fromisoformat(s.replace('/', '-'))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            try:
                dt = datetime.strptime(s, '%Y-%m-%d')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        return None
    
    def _add_days_iso(self, iso: str, days: int) -> Optional[str]:
        """Suma días a fecha ISO en UTC"""
        if not iso:
            return None
        
        try:
            dt = datetime.fromisoformat(iso)
            dt += datetime.timedelta(days=days)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return None
    
    def read_sheet_data(self, spreadsheet_id: str, range_name: str = 'Sheet1') -> List[Dict[str, Any]]:
        """Lee datos de Google Sheets"""
        if not self.service:
            raise Exception("Must authenticate first")
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return []
            
            # Primera fila como headers
            headers = values[0]
            rows = []
            
            for row_values in values[1:]:
                # Completar con vacíos si la fila es más corta
                while len(row_values) < len(headers):
                    row_values.append('')
                
                row_dict = {}
                for i, header in enumerate(headers):
                    row_dict[header] = row_values[i] if i < len(row_values) else ''
                
                rows.append(row_dict)
            
            return rows
            
        except Exception as e:
            logger.error(f"Error reading Google Sheets: {e}")
            raise
    
    def process_debt_collection_data(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Procesa datos de cobranza siguiendo la lógica exacta del workflow N8N
        Agrupa por RUT y calcula fechas límite/máxima
        """
        batch_id = f"batch-{datetime.now().strftime('%Y-%m-%d')}"
        by_rut = {}
        
        for i, r in enumerate(rows):
            # Crear índice de claves normalizadas
            key_index = {}
            for k in r.keys():
                key_index[self._norm_key(k)] = k
            
            # Extraer campos principales
            rut = self._norm_rut(self._get_field(r, key_index, ['RUTS', 'RUT']))
            nombre = str(self._get_field(r, key_index, ['Nombre']) or '').strip()
            empresa = str(self._get_field(r, key_index, [
                'Origen Empresa', 'OrigenEmpresa', 'Empresa'
            ]) or '').strip()
            saldo = self._to_number_pesos(self._get_field(r, key_index, [
                'Saldo actualizado', 'Saldo Actualizado', ' Saldo actualizado '
            ]))
            
            # Fechas y días
            fecha_venc = self._to_iso(self._get_field(r, key_index, [
                'FechaVencimiento', 'Fecha Vencimiento', 'Fecha vencimiento',
                'Vencimiento', 'Fecha de Vencimiento'
            ]))
            dias_retr = self._to_int(self._get_field(r, key_index, [
                'diasRetraso',  # Header real confirmado
                'Días de retraso', 'Dias de retraso', 'Días de atraso',
                'Dias de atraso', 'Dias retraso', 'Días retraso',
                'dias_de_retraso', 'diasretraso', 'dias atraso', 'dias_atraso'
            ]), 0)
            
            # Teléfonos
            mob_raw = self._get_field(r, key_index, [
                'Teléfono móvil', 'Telefono movil', 'Teléfono celular', 'Celular'
            ])
            res_raw = self._get_field(r, key_index, [
                'Teléfono Residencial', 'Telefono residencial',
                'Teléfono fijo', 'Telefono fijo'
            ])
            
            mobile = self._norm_cl_phone(mob_raw, 'mobile')
            land = self._norm_cl_phone(res_raw, 'landline') or self._norm_cl_phone(res_raw, 'any')
            best = mobile or land or None
            
            if not rut:
                continue
            
            # Inicializar acumulador por RUT
            if rut not in by_rut:
                by_rut[rut] = {
                    'batch_id': batch_id,
                    'rut': rut,
                    'nombre': nombre,
                    'origen_empresa': empresa or None,
                    'phones': {
                        'raw_mobile': mob_raw or None,
                        'raw_landline': res_raw or None,
                        'mobile_e164': mobile or None,
                        'landline_e164': land or None,
                        'best_e164': best or None
                    },
                    'cantidad_cupones': 0,
                    'monto_total': 0,
                    '_max_base': None,  # {fv: 'YYYY-MM-DD', dias: N}
                    '_min_base': None,  # {fv: 'YYYY-MM-DD', dias: N}
                    'fecha_limite': None,
                    'fecha_maxima': None,
                    'debug': {'max_base': None, 'min_base': None}
                }
            
            acc = by_rut[rut]
            
            # Acumular
            acc['cantidad_cupones'] += 1
            acc['monto_total'] += saldo or 0
            
            # Completar teléfonos si faltan
            if not acc['phones']['mobile_e164'] and mobile:
                acc['phones']['mobile_e164'] = mobile
            if not acc['phones']['landline_e164'] and land:
                acc['phones']['landline_e164'] = land
            if not acc['phones']['best_e164'] and best:
                acc['phones']['best_e164'] = best
            
            # Registrar máximos/mínimos por RUT
            if fecha_venc:
                if not acc['_max_base'] or fecha_venc > acc['_max_base']['fv']:
                    acc['_max_base'] = {'fv': fecha_venc, 'dias': dias_retr}
                    acc['debug']['max_base'] = acc['_max_base']
                
                if not acc['_min_base'] or fecha_venc < acc['_min_base']['fv']:
                    acc['_min_base'] = {'fv': fecha_venc, 'dias': dias_retr}
                    acc['debug']['min_base'] = acc['_min_base']
        
        # Calcular fechas finales
        for rut, acc in by_rut.items():
            if acc['_max_base']:
                add = acc['_max_base']['dias'] + 3
                acc['fecha_limite'] = self._add_days_iso(acc['_max_base']['fv'], add)
            
            if acc['_min_base']:
                add = acc['_min_base']['dias'] + 7
                acc['fecha_maxima'] = self._add_days_iso(acc['_min_base']['fv'], add)
            
            # Limpiar campos internos
            del acc['_max_base']
            del acc['_min_base']
        
        # Generar salida final
        output = []
        for rut, doc in by_rut.items():
            doc['to_number'] = doc['phones']['best_e164'] or None
            doc['key'] = f"{doc['batch_id']}::{rut}"
            doc['created_at'] = datetime.now().isoformat()
            output.append(doc)
        
        return output
    
    def create_call_jobs(self, debtors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Genera jobs de llamadas siguiendo lógica N8N"""
        now_cl = datetime.now().strftime('%A, %B %d, %Y at %I:%M:%S %p CLT')
        
        def parse_rut_like(rut_raw):
            if not rut_raw:
                return {'rut': None, 'rut_fmt': None}
            
            s = str(rut_raw).replace('.', '').replace('-', '').strip().upper()
            if len(s) < 2:
                return {'rut': s, 'rut_fmt': s}
            
            num = s[:-1]
            dv = s[-1]
            return {'rut': num + dv, 'rut_fmt': f"{num}-{dv}"}
        
        def pick_number(doc):
            p = doc.get('phones', {})
            return doc.get('to_number') or p.get('best_e164') or p.get('mobile_e164') or None
        
        jobs = []
        for debtor in debtors:
            rut_data = parse_rut_like(debtor['rut'])
            rut = rut_data['rut'] or debtor['rut']
            
            job = {
                'job_id': f"{debtor['batch_id']}::{rut}",
                'batch_id': debtor['batch_id'],
                
                # Identificación
                'rut': rut,
                'rut_fmt': rut_data['rut_fmt'] or debtor['rut'],
                'nombre': debtor['nombre'] or '',
                'origen_empresa': debtor['origen_empresa'] or '',
                
                # Teléfono destino
                'to_number': pick_number(debtor),
                
                # Variables de negocio (en pesos)
                'cantidad_cupones': int(debtor['cantidad_cupones'] or 0),
                'monto_total': float(debtor['monto_total'] or 0),
                'fecha_limite': str(debtor['fecha_limite'] or ''),
                'fecha_maxima': str(debtor['fecha_maxima'] or ''),
                'fecha_pago_cliente': '',
                
                # Contexto local Chile
                'current_time_America_Santiago': now_cl,
                
                # Control de cola
                'attempts': 0,
                'max_attempts': 3,
                'status': 'pending',
                'created_at': datetime.now().isoformat(),
                'next_try_at': datetime.now().isoformat(),
                'history': []
            }
            
            jobs.append(job)
        
        return jobs