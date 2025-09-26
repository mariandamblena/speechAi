"""
Procesador de Excel genérico que soporta múltiples casos de uso
Reemplaza el procesador específico de cobranza con uno extensible
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from io import BytesIO

from ..domain.abstract.use_case_enums import UseCaseType, DataSourceType
from ..domain.use_case_registry import get_use_case_registry, get_universal_factory
from ..domain.abstract.base_models import BaseJobModel, BaseBatchModel


class UniversalExcelProcessor:
    """
    Procesador universal de Excel que puede manejar cualquier caso de uso
    """
    
    def __init__(self):
        self.registry = get_use_case_registry()
        self.factory = get_universal_factory()
        
        # Normalización común de columnas
        self.column_mappings = {
            # Cobranza
            "rut": ["rut", "identificador", "cedula", "dni", "id"],
            "nombre": ["nombre", "name", "cliente", "deudor", "persona"],
            "telefono": ["telefono", "phone", "celular", "movil", "tel"],
            "deuda": ["deuda", "debt", "monto", "amount", "saldo"],
            "fecha_vencimiento": ["fecha_vencimiento", "due_date", "vencimiento", "limite"],
            "empresa": ["empresa", "company", "acreedor", "cliente_empresa"],
            
            # User Experience
            "customer_id": ["customer_id", "cliente_id", "user_id", "id_cliente"],
            "interaction_type": ["interaction_type", "tipo_interaccion", "tipo"],
            "producto_servicio": ["producto_servicio", "product", "servicio", "item"],
            "fecha_compra": ["fecha_compra", "purchase_date", "compra"],
            "preguntas": ["preguntas", "questions", "survey_questions"],
            "duracion_minutos": ["duracion_minutos", "duration", "tiempo_estimado"],
            
            # Comunes
            "email": ["email", "correo", "mail"],
            "telefono2": ["telefono2", "phone2", "telefono_alternativo"],
            "direccion": ["direccion", "address", "domicilio"]
        }
    
    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normaliza nombres de columnas para mapeo estándar"""
        df_normalized = df.copy()
        
        # Crear mapeo inverso: todas las variantes -> nombre estándar
        reverse_mapping = {}
        for standard_name, variants in self.column_mappings.items():
            for variant in variants:
                reverse_mapping[variant.lower()] = standard_name
        
        # Normalizar nombres de columnas
        new_columns = {}
        for col in df_normalized.columns:
            col_lower = col.lower().strip()
            # Limpiar espacios y caracteres especiales
            col_clean = col_lower.replace(' ', '_').replace('-', '_')
            
            # Buscar mapeo
            standard_name = reverse_mapping.get(col_clean, col_clean)
            new_columns[col] = standard_name
        
        df_normalized = df_normalized.rename(columns=new_columns)
        return df_normalized
    
    def detect_use_case_from_columns(self, columns: List[str]) -> Optional[str]:
        """Intenta detectar el caso de uso basado en las columnas presentes"""
        columns_lower = [col.lower() for col in columns]
        
        # Detectores por caso de uso
        debt_indicators = ["deuda", "debt", "monto", "fecha_vencimiento", "rut"]
        ux_indicators = ["customer_id", "interaction_type", "producto_servicio", "preguntas"]
        
        debt_score = sum(1 for indicator in debt_indicators if any(indicator in col for col in columns_lower))
        ux_score = sum(1 for indicator in ux_indicators if any(indicator in col for col in columns_lower))
        
        if debt_score > ux_score and debt_score >= 2:
            return UseCaseType.DEBT_COLLECTION.value
        elif ux_score >= 2:
            return UseCaseType.USER_EXPERIENCE.value
        
        return None
    
    def validate_excel_for_use_case(
        self, 
        df: pd.DataFrame, 
        use_case: str
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Valida que el Excel tenga las columnas necesarias para el caso de uso
        Retorna: (es_válido, errores, warnings)
        """
        errors = []
        warnings = []
        
        # Obtener columnas requeridas para el caso de uso
        required_columns = self.registry.get_required_columns_for_use_case(use_case)
        if not required_columns:
            errors.append(f"Caso de uso no soportado: {use_case}")
            return False, errors, warnings
        
        # Verificar columnas presentes
        df_columns = [col.lower() for col in df.columns]
        missing_columns = []
        
        for required in required_columns:
            if required not in df_columns:
                missing_columns.append(required)
        
        if missing_columns:
            errors.append(f"Columnas requeridas faltantes: {missing_columns}")
        
        # Verificar que hay datos
        if df.empty:
            errors.append("El archivo Excel está vacío")
        
        # Warnings para columnas adicionales útiles
        if use_case == UseCaseType.DEBT_COLLECTION.value:
            if "telefono2" not in df_columns:
                warnings.append("Considera agregar 'telefono2' para más opciones de contacto")
            if "email" not in df_columns:
                warnings.append("Considera agregar 'email' para contacto alternativo")
        
        return len(errors) == 0, errors, warnings
    
    def process_excel_to_jobs(
        self,
        file_content: bytes,
        use_case: str,
        account_id: str,
        batch_name: str,
        batch_description: str = ""
    ) -> Tuple[BaseBatchModel, List[BaseJobModel], List[str]]:
        """
        Procesa un archivo Excel y crea jobs para el caso de uso especificado
        Retorna: (batch, jobs, errores)
        """
        try:
            # Leer Excel
            df = pd.read_excel(BytesIO(file_content))
            
            # Normalizar columnas
            df = self.normalize_column_names(df)
            
            # Auto-detectar caso de uso si no se especifica
            if not use_case or use_case == "auto":
                detected_use_case = self.detect_use_case_from_columns(df.columns.tolist())
                if detected_use_case:
                    use_case = detected_use_case
                else:
                    return None, [], ["No se pudo detectar automáticamente el caso de uso. Especifica uno manualmente."]
            
            # Validar Excel para el caso de uso
            is_valid, errors, warnings = self.validate_excel_for_use_case(df, use_case)
            if not is_valid:
                return None, [], errors
            
            # Crear batch
            batch_class = self.registry.get_batch_class(use_case)
            if not batch_class:
                return None, [], [f"No se pudo crear batch para caso de uso: {use_case}"]
            
            batch = batch_class(
                _id="",  # Se auto-genera
                account_id=account_id,
                use_case=use_case,
                name=batch_name,
                description=batch_description or f"Batch de {use_case}",
                total_jobs=len(df)
            )
            
            # Crear jobs
            jobs = []
            processing_errors = []
            
            for index, row in df.iterrows():
                try:
                    # Convertir fila a diccionario
                    row_data = row.to_dict()
                    
                    # Validar datos de la fila
                    row_errors = self.factory.validate_data_for_use_case(use_case, row_data)
                    if row_errors:
                        processing_errors.append(f"Fila {index + 2}: {'; '.join(row_errors)}")
                        continue
                    
                    # Crear job
                    job = self.factory.create_job_from_data(
                        use_case=use_case,
                        row_data=row_data,
                        batch_id=batch._id,
                        account_id=account_id
                    )
                    
                    if job:
                        jobs.append(job)
                    else:
                        processing_errors.append(f"Fila {index + 2}: No se pudo crear job")
                        
                except Exception as e:
                    processing_errors.append(f"Fila {index + 2}: Error procesando - {str(e)}")
            
            # Actualizar estadísticas del batch
            batch.total_jobs = len(jobs)
            
            return batch, jobs, processing_errors + warnings
            
        except Exception as e:
            return None, [], [f"Error procesando Excel: {str(e)}"]
    
    def get_excel_template_for_use_case(self, use_case: str) -> pd.DataFrame:
        """Genera template Excel para un caso de uso específico"""
        required_columns = self.registry.get_required_columns_for_use_case(use_case)
        
        if not required_columns:
            raise ValueError(f"Caso de uso no soportado: {use_case}")
        
        # Crear DataFrame vacío con las columnas requeridas
        template_data = {col: [] for col in required_columns}
        
        # Agregar columnas opcionales comunes
        optional_columns = ["telefono2", "email", "direccion", "observaciones"]
        for col in optional_columns:
            if col not in template_data:
                template_data[col] = []
        
        # Agregar filas de ejemplo según el caso de uso
        if use_case == UseCaseType.DEBT_COLLECTION.value:
            example_row = {
                "nombre": "Juan Pérez",
                "rut": "12345678-9",
                "telefono": "+56912345678",
                "deuda": 150000,
                "fecha_vencimiento": "2024-01-15",
                "empresa": "Empresa ABC",
                "telefono2": "+56987654321",
                "email": "juan.perez@example.com"
            }
        elif use_case == UseCaseType.USER_EXPERIENCE.value:
            example_row = {
                "nombre": "María González",
                "customer_id": "CUST001",
                "telefono": "+56912345678",
                "interaction_type": "post_purchase",
                "producto_servicio": "Smartphone XYZ",
                "fecha_compra": "2024-01-10",
                "email": "maria.gonzalez@example.com"
            }
        else:
            example_row = {}
        
        # Añadir ejemplo a todas las columnas
        for col in template_data:
            template_data[col] = [example_row.get(col, "")]
        
        return pd.DataFrame(template_data)
    
    def get_supported_use_cases(self) -> Dict[str, Dict[str, Any]]:
        """Retorna información sobre todos los casos de uso soportados"""
        use_cases_info = {}
        
        for use_case in self.registry.get_available_use_cases():
            required_cols = self.registry.get_required_columns_for_use_case(use_case)
            
            use_cases_info[use_case] = {
                "name": use_case.replace("_", " ").title(),
                "description": self._get_use_case_description(use_case),
                "required_columns": required_cols,
                "example_template": self.get_excel_template_for_use_case(use_case).to_dict('records')[0] if required_cols else {}
            }
        
        return use_cases_info
    
    def _get_use_case_description(self, use_case: str) -> str:
        """Obtiene descripción de un caso de uso"""
        descriptions = {
            UseCaseType.DEBT_COLLECTION.value: "Gestión y seguimiento de cobranzas de deuda",
            UseCaseType.USER_EXPERIENCE.value: "Llamadas de experiencia de usuario y feedback",
            UseCaseType.SURVEY.value: "Encuestas y recolección de datos",
            UseCaseType.REMINDER.value: "Recordatorios y notificaciones",
            UseCaseType.NOTIFICATION.value: "Notificaciones informativas"
        }
        return descriptions.get(use_case, "Caso de uso personalizado")