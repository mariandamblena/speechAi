"""
Utilidades para procesamiento de archivos Excel de deudores
Implementa la lógica del workflow Adquisicion_v3 en Python
Soporte multi-país: Chile (CL) y Argentina (AR)
"""

import re
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Union
from io import BytesIO

# Importar normalizadores centralizados
from utils.normalizers import (
    normalize_phone_cl,
    normalize_phone_ar,
    normalize_date,
    normalize_rut,
    format_rut,
    normalize_key,
    add_days_iso,
    to_number_pesos,
    to_int,
    to_float
)


class ChileanDataNormalizer:
    """Normalizador de datos específicos de Chile (RUT, teléfonos, fechas)"""
    
    CFG = {
        'country': 'CL',
        'default_area_code_cl': '2'
    }
    
    @staticmethod
    def normalize_key(key: str) -> str:
        """Normaliza nombres de columnas para búsqueda flexible"""
        if not key:
            return ""
        
        # Normalizar acentos
        import unicodedata
        key = unicodedata.normalize('NFD', key)
        key = ''.join(char for char in key if unicodedata.category(char) != 'Mn')
        
        # Limpiar espacios y caracteres especiales
        key = re.sub(r'\s+', ' ', key.strip().lower())
        key = re.sub(r'[^\w ]', '', key)
        key = re.sub(r'\s+', ' ', key)
        
        return key
    
    @staticmethod
    def normalize_rut(rut_raw: Any) -> Optional[str]:
        """Normaliza RUT chileno (quita puntos y guiones)"""
        if rut_raw is None or rut_raw == '':
            return None
        
        # Quitar puntos y guiones
        rut_clean = str(rut_raw).replace('.', '').replace('-', '').strip().upper()
        return rut_clean if rut_clean else None
    
    @staticmethod
    def format_rut(rut_clean: str) -> str:
        """Formatea RUT para mostrar (12.345.678-9)"""
        if not rut_clean or len(rut_clean) < 2:
            return rut_clean
        
        num = rut_clean[:-1]
        dv = rut_clean[-1]
        
        # Agregar puntos cada 3 dígitos desde la derecha
        formatted_num = ""
        for i, digit in enumerate(reversed(num)):
            if i > 0 and i % 3 == 0:
                formatted_num = "." + formatted_num
            formatted_num = digit + formatted_num
        
        return f"{formatted_num}-{dv}"
    
    @staticmethod
    def to_number_pesos(val: Any) -> float:
        """Convierte valores a pesos (no centavos), maneja NaN de pandas"""
        if val is None or val == '':
            return 0.0
        
        # Manejar NaN de pandas específicamente
        if pd.isna(val):
            return 0.0
        
        if isinstance(val, (int, float)):
            # Verificar si es infinito o NaN
            if pd.isna(val) or val == float('inf') or val == float('-inf'):
                return 0.0
            return float(val)
        
        # Limpiar string
        s = str(val).strip()
        if not s or s.lower() in ['nan', 'null', 'none']:
            return 0.0
            
        s = re.sub(r'[\s$]', '', s)  # Quitar espacios y símbolo $
        s = s.replace('.', '').replace(',', '.')  # Formato chileno: 1.234.567,89 -> 1234567.89
        
        try:
            result = float(s)
            # Verificar si el resultado es válido
            if pd.isna(result) or result == float('inf') or result == float('-inf'):
                return 0.0
            return result
        except ValueError:
            return 0.0
    
    @staticmethod
    def to_int(val: Any, default: int = 0) -> int:
        """Convierte a entero con valor por defecto, maneja NaN de pandas"""
        if val is None or val == '':
            return default
        
        # Manejar NaN de pandas
        if pd.isna(val):
            return default
        
        try:
            # Si ya es numérico, convertir directamente
            if isinstance(val, (int, float)):
                if pd.isna(val) or val == float('inf') or val == float('-inf'):
                    return default
                return int(val)
            
            # Quitar caracteres no numéricos excepto el signo
            clean_val = re.sub(r'[^\d\-]', '', str(val))
            return int(clean_val) if clean_val else default
        except ValueError:
            return default
            return default
    
    @staticmethod
    def split_phones(raw: str) -> List[str]:
        """Genera candidatos de números telefónicos"""
        s = str(raw or '').strip()
        
        # Separar por caracteres no numéricos
        parts = [p for p in re.split(r'\D+', s) if p]
        
        # Todo pegado (solo dígitos)
        all_digits = re.sub(r'\D+', '', s)
        
        candidates = set()
        if all_digits:
            candidates.add(all_digits)
        
        for part in parts:
            candidates.add(part)
        
        # Pegar los dos primeros grupos si el primero es corto (código de área)
        if len(parts) >= 2 and len(parts[0]) <= 3:
            candidates.add(parts[0] + parts[1])
        
        return list(candidates)
    
    @classmethod
    def normalize_cl_phone(cls, raw: Any, kind: Optional[str] = None) -> Optional[str]:
        """
        Normaliza teléfonos chilenos a formato E.164 (+56XXXXXXXXX)
        
        Args:
            raw: número crudo
            kind: 'mobile', 'landline', o None para cualquiera
        
        Returns:
            Número normalizado o None
        """
        if raw is None or raw == '':
            return None
        
        want_mobile = kind == 'mobile'
        want_landline = kind == 'landline'
        want_any = not want_mobile and not want_landline
        
        candidates = cls.split_phones(str(raw))
        
        for n in candidates:
            # Quitar código país
            if n.startswith('56'):
                n = n[2:]
            
            # Quitar trunk (0 inicial)
            n = re.sub(r'^0+', '', n)
            
            # Heurísticas para errores frecuentes
            
            # Móviles que llegan como "99xxxxxxxx" (10 dígitos)
            if len(n) == 10 and n.startswith('99'):
                n = n[1:]  # Quitar el 9 extra
            
            # Móvil legado con 8 dígitos que empieza con 9 -> anteponer 9
            if len(n) == 8 and n[0] == '9':
                n = '9' + n
            
            # Fijo Santiago legado: "2" + 7 dígitos -> anteponer otro '2'
            if len(n) == 8 and n[0] == '2' and not n.startswith('22'):
                n = '2' + n
            
            # Normalización por tipo deseado
            if want_mobile and len(n) == 8 and n[0] != '9':
                n = '9' + n
            
            if (want_landline or want_any) and len(n) in [7, 8] and n[0] != '9':
                n = (cls.CFG['default_area_code_cl'] or '2') + n
            
            # Validación final
            if len(n) != 9:
                continue
            
            looks_mobile = n.startswith('9')
            if want_mobile and not looks_mobile:
                continue
            if want_landline and looks_mobile:
                continue
            
            return f'+56{n}'
        
        return None
    
    @staticmethod
    def to_iso_date(val: Any) -> Optional[str]:
        """Convierte fechas a formato ISO (YYYY-MM-DD), priorizando formato chileno"""
        if val is None or val == '':
            return None
        
        # Manejar NaN de pandas
        if pd.isna(val):
            return None
        
        # Excel serial number
        if isinstance(val, (int, float)):
            # Verificar si es un valor válido
            if pd.isna(val) or val == float('inf') or val == float('-inf'):
                return None
            try:
                # Excel usa 1900-01-01 como época, pero tiene bug del año 1900
                base = datetime(1899, 12, 30)
                date_obj = base + timedelta(days=int(val))
                return date_obj.strftime('%Y-%m-%d')
            except (ValueError, OverflowError):
                return None
        
        s = str(val).strip()
        if not s or s.lower() in ['nan', 'null', 'none']:
            return None
        
        # Formato chileno: DD/MM/YYYY o DD-MM-YYYY
        match = re.match(r'^(\d{1,2})[\\/\-](\d{1,2})[\\/\-](\d{2,4})$', s)
        if match:
            dd, mm, yyyy = match.groups()
            
            # Año de 2 dígitos -> asume 20xx
            if len(yyyy) == 2:
                yyyy = '20' + yyyy
            
            try:
                y, m, d = int(yyyy), int(mm), int(dd)
                if 1 <= m <= 12 and 1 <= d <= 31:
                    date_obj = datetime(y, m, d)
                    return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # Intentar parsing directo
        try:
            date_obj = pd.to_datetime(s)
            return date_obj.strftime('%Y-%m-%d')
        except:
            pass
        
        return None
    
    @staticmethod
    def add_days_iso(iso_date: str, days: int) -> Optional[str]:
        """Suma días a una fecha ISO"""
        if not iso_date:
            return None
        
        try:
            date_obj = datetime.strptime(iso_date, '%Y-%m-%d')
            new_date = date_obj + timedelta(days=days)
            return new_date.strftime('%Y-%m-%d')
        except ValueError:
            return None


class ExcelDebtorProcessor:
    """Procesador principal de archivos Excel de deudores - Multi-país"""
    
    def __init__(self, country: str = "CL"):
        """
        Inicializa el procesador
        
        Args:
            country: Código ISO del país ("CL" para Chile, "AR" para Argentina)
        """
        self.country = country.upper()
        self.normalizer = ChileanDataNormalizer()  # Mantenemos para compatibilidad
        
        # Seleccionar función de normalización de teléfonos según país
        if self.country == "AR":
            self.normalize_phone = normalize_phone_ar
        else:  # Default: CL
            self.normalize_phone = normalize_phone_cl
    
    def get_field_value(self, row: pd.Series, key_candidates: List[str]) -> Any:
        """
        Busca un campo en la fila usando candidatos de nombres de columnas
        Implementa búsqueda flexible similar al workflow original
        """
        # Crear índice normalizado de columnas
        key_index = {}
        for col in row.index:
            normalized_col = normalize_key(col)
            key_index[normalized_col] = col
        
        # Buscar por candidatos exactos
        for candidate in key_candidates:
            normalized_candidate = normalize_key(candidate)
            if normalized_candidate in key_index:
                value = row[key_index[normalized_candidate]]
                # Retornar None si es NaN de pandas
                return None if pd.isna(value) else value
        
        # Buscar por inclusión parcial
        for normalized_col, original_col in key_index.items():
            for candidate in key_candidates:
                normalized_candidate = self.normalizer.normalize_key(candidate)
                if normalized_candidate in normalized_col:
                    value = row[original_col]
                    # Retornar None si es NaN de pandas
                    return None if pd.isna(value) else value
        
        return None
    
    def process_excel_data(self, file_content: bytes, account_id: str) -> Dict[str, Any]:
        """
        Procesa archivo Excel y devuelve deudores consolidados por RUT
        Implementa la lógica completa del workflow Adquisicion_v3
        """
        try:
            # Leer Excel
            df = pd.read_excel(BytesIO(file_content))
            
            # Limpiar DataFrame: reemplazar NaN con None/valores por defecto
            df = df.where(pd.notnull(df), None)
            
            # Generar batch_id único con microsegundos para evitar colisiones
            batch_id = f"batch-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-{datetime.now().microsecond}"
            
            # Agrupar por RUT
            debtors_by_rut = {}
            
            for _, row in df.iterrows():
                # Extraer campos usando búsqueda flexible
                rut_raw = self.get_field_value(row, ['RUTS', 'RUT', 'Rut'])
                nombre = str(self.get_field_value(row, ['Nombre', 'nombre']) or '').strip()
                empresa = str(self.get_field_value(row, [
                    'Origen Empresa', 'OrigenEmpresa', 'Empresa', 'origen_empresa'
                ]) or '').strip()
                
                saldo = to_number_pesos(
                    self.get_field_value(row, [
                        'Saldo actualizado', 'Saldo Actualizado', ' Saldo actualizado ', 'saldo'
                    ])
                )
                
                # Fechas y días de retraso
                fecha_venc = normalize_date(
                    self.get_field_value(row, [
                        'FechaVencimiento', 'Fecha Vencimiento', 'Fecha vencimiento',
                        'Vencimiento', 'Fecha de Vencimiento'
                    ])
                )
                
                dias_retraso = to_int(
                    self.get_field_value(row, [
                        'diasRetraso', 'Días de retraso', 'Dias de retraso',
                        'Días de atraso', 'Dias de atraso', 'Dias retraso',
                        'Días retraso', 'dias_de_retraso', 'diasretraso'
                    ]), 0
                )
                
                # Teléfonos
                mobile_raw = self.get_field_value(row, [
                    'Teléfono móvil', 'Telefono movil', 'Teléfono celular', 'Celular'
                ])
                landline_raw = self.get_field_value(row, [
                    'Teléfono Residencial', 'Telefono residencial', 
                    'Teléfono fijo', 'Telefono fijo'
                ])
                
                # Normalizar RUT
                rut = normalize_rut(rut_raw)
                if not rut:
                    continue  # Saltar filas sin RUT válido
                
                # Normalizar teléfonos según país
                mobile_e164 = self.normalize_phone(mobile_raw, 'mobile')
                landline_e164 = (
                    self.normalize_phone(landline_raw, 'landline') or
                    self.normalize_phone(landline_raw, 'any')
                )
                best_e164 = mobile_e164 or landline_e164
                
                # Inicializar o actualizar deudor por RUT
                if rut not in debtors_by_rut:
                    debtors_by_rut[rut] = {
                        'batch_id': batch_id,
                        'rut': rut,
                        'rut_fmt': format_rut(rut),
                        'nombre': nombre,
                        'origen_empresa': empresa or None,
                        'phones': {
                            'raw_mobile': mobile_raw,
                            'raw_landline': landline_raw,
                            'mobile_e164': mobile_e164,
                            'landline_e164': landline_e164,
                            'best_e164': best_e164
                        },
                        'cantidad_cupones': 0,
                        'monto_total': 0.0,
                        '_max_base': None,  # {fecha_venc, dias_retraso}
                        '_min_base': None,  # {fecha_venc, dias_retraso}
                        'fecha_limite': None,
                        'fecha_maxima': None
                    }
                
                debtor = debtors_by_rut[rut]
                
                # Acumular datos
                debtor['cantidad_cupones'] += 1
                debtor['monto_total'] += saldo
                
                # Completar teléfonos si faltan
                if not debtor['phones']['mobile_e164'] and mobile_e164:
                    debtor['phones']['mobile_e164'] = mobile_e164
                if not debtor['phones']['landline_e164'] and landline_e164:
                    debtor['phones']['landline_e164'] = landline_e164
                if not debtor['phones']['best_e164'] and best_e164:
                    debtor['phones']['best_e164'] = best_e164
                
                # Calcular fechas límite (fecha máxima para límite, fecha mínima para máxima)
                if fecha_venc:
                    # Fecha límite = fecha_vencimiento MÁS GRANDE + dias_retraso + 3
                    if not debtor['_max_base'] or fecha_venc > debtor['_max_base']['fecha_venc']:
                        debtor['_max_base'] = {
                            'fecha_venc': fecha_venc,
                            'dias_retraso': dias_retraso
                        }
                    
                    # Fecha máxima = fecha_vencimiento MÁS CHICA + dias_retraso + 7
                    if not debtor['_min_base'] or fecha_venc < debtor['_min_base']['fecha_venc']:
                        debtor['_min_base'] = {
                            'fecha_venc': fecha_venc,
                            'dias_retraso': dias_retraso
                        }
            
            # Calcular fechas finales
            for rut, debtor in debtors_by_rut.items():
                if debtor['_max_base']:
                    base_date = debtor['_max_base']['fecha_venc']
                    days_to_add = debtor['_max_base']['dias_retraso'] + 3
                    debtor['fecha_limite'] = add_days_iso(base_date, days_to_add)
                
                if debtor['_min_base']:
                    base_date = debtor['_min_base']['fecha_venc']
                    days_to_add = debtor['_min_base']['dias_retraso'] + 7
                    debtor['fecha_maxima'] = add_days_iso(base_date, days_to_add)
                
                # Limpiar campos temporales
                del debtor['_max_base']
                del debtor['_min_base']
                
                # Asignar campos finales
                debtor['to_number'] = debtor['phones']['best_e164']
                debtor['key'] = f"{batch_id}::{rut}"
                debtor['created_at'] = datetime.utcnow()
            
            # Limpiar todos los deudores de valores NaN residuales
            clean_debtors = []
            for debtor in debtors_by_rut.values():
                clean_debtor = self._clean_nan_values(debtor)
                clean_debtors.append(clean_debtor)
            
            return {
                'batch_id': batch_id,
                'account_id': account_id,
                'total_debtors': len(debtors_by_rut),
                'debtors': clean_debtors
            }
            
        except Exception as e:
            raise ValueError(f"Error procesando archivo Excel: {str(e)}")
    
    def _clean_nan_values(self, data: Any) -> Any:
        """
        Limpia recursivamente valores NaN de cualquier estructura de datos
        para evitar errores de serialización JSON
        """
        if isinstance(data, dict):
            return {k: self._clean_nan_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_nan_values(item) for item in data]
        elif pd.isna(data):
            return None
        elif isinstance(data, float):
            if data == float('inf') or data == float('-inf'):
                return None
            return data
        else:
            return data