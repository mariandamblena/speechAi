# 🏗️ ARQUITECTURA DEL DOMINIO - SPEECHAI BACKEND

## 📋 **EXPLICACIÓN COMPLETA DE LOS ARCHIVOS DE DOMAIN**

La carpeta `domain/` implementa los principios de **Domain-Driven Design (DDD)** y contiene el **corazón de la lógica de negocio** del sistema. Está diseñada para ser **extensible** y **mantenible**.

---

## 🗂️ **ESTRUCTURA DEL DOMAIN**

```
domain/
├── enums.py                    # Estados y tipos del sistema
├── models.py                   # Entidades principales del negocio  
├── use_case_registry.py        # Registro de casos de uso
├── abstract/                   # Clases base y contratos
│   ├── base_models.py          # Modelos abstractos
│   └── use_case_enums.py       # Enums para casos de uso
└── use_cases/                  # Implementaciones específicas
    ├── debt_collection.py      # Cobranza de deudas
    └── user_experience.py      # Experiencia de usuario
```

---

## 🔧 **ARCHIVOS PRINCIPALES**

### **1. 📊 `enums.py` - Estados y Tipos del Sistema**

Define las **constantes y estados** que maneja el sistema:

```python
class JobStatus(Enum):
    """Estados del ciclo de vida de un job"""
    PENDING = "pending"        # ← Esperando ser procesado
    IN_PROGRESS = "in_progress" # ← Siendo ejecutado por worker
    COMPLETED = "completed"     # ← Llamada exitosa
    FAILED = "failed"          # ← Falló definitivamente
    SUSPENDED = "suspended"     # ← Suspendido (sin balance)

class PlanType(Enum):
    """Modelos de negocio SaaS"""
    MINUTES_BASED = "minutes_based"  # ← Pago por minutos
    CREDIT_BASED = "credit_based"    # ← Prepago con créditos
    UNLIMITED = "unlimited"          # ← Plan ilimitado

class AccountStatus(Enum):
    """Estados de cuenta multi-tenant"""
    ACTIVE = "active"              # ← Puede hacer llamadas
    SUSPENDED = "suspended"        # ← Cuenta suspendida
    EXPIRED = "expired"           # ← Plan expirado
```

**Importancia**: Centraliza todos los estados válidos del sistema, evita "magic strings" y facilita la evolución.

### **2. 🎯 `models.py` - Entidades del Negocio**

Contiene los **modelos principales** que representan conceptos del mundo real:

#### **🔹 JobModel - La Entidad Central**
```python
@dataclass
class JobModel:
    """Representa una llamada individual a realizar"""
    
    # Identificación y contexto
    job_id: str                    # ← ID único
    account_id: str               # ← Cliente multi-tenant
    batch_id: str                 # ← Lote al que pertenece
    
    # Información de contacto
    contact: ContactInfo          # ← A quién llamar
    payload: CallPayload          # ← Qué decir
    
    # Control de ejecución
    status: JobStatus             # ← Estado actual
    attempts: int = 0             # ← Intentos realizados
    max_attempts: int = 3         # ← Límite de intentos
    
    # Integración con Retell AI
    call_id: Optional[str]        # ← ID de Retell
    call_result: Dict[str, Any]   # ← Resultado completo
```

**Características clave**:
- ✅ **Anti-duplicación**: `deduplication_key` previene duplicados
- ✅ **Multi-teléfono**: Intenta múltiples números automáticamente
- ✅ **Costos**: Control granular de reservas y consumo
- ✅ **Retell Integration**: Mapeo completo a contexto de IA

#### **🔹 AccountModel - Multi-tenancy y Facturación**
```python
@dataclass
class AccountModel:
    """Representa una cuenta de cliente"""
    
    # Identificación
    account_id: str               # ← ID único del cliente
    account_name: str             # ← Nombre del cliente
    plan_type: PlanType           # ← Modelo de facturación
    
    # Balance de minutos (plan por minutos)
    minutes_purchased: float      # ← Minutos comprados
    minutes_used: float           # ← Minutos ya consumidos
    minutes_reserved: float       # ← Reservados para llamadas activas
    
    # Balance de créditos (plan prepago)
    credit_balance: float         # ← Saldo disponible
    credit_reserved: float        # ← Reservado para llamadas activas
    
    # Límites operacionales
    max_concurrent_calls: int = 3    # ← Llamadas simultáneas
    daily_call_limit: int = 1000     # ← Límite diario
```

**Funcionalidades inteligentes**:
```python
# Verificaciones automáticas
def can_make_calls(self) -> bool:
    """¿Puede hacer llamadas?"""
    return (
        self.status == AccountStatus.ACTIVE and
        self.has_sufficient_balance and
        self.calls_today < self.daily_call_limit
    )

# Gestión de reservas
def reserve_funds(self, estimated_minutes: float) -> bool:
    """Reserva fondos antes de la llamada"""
    
def consume_funds(self, actual_minutes: float) -> None:
    """Consume fondos después de la llamada"""
```

#### **🔹 DebtorModel - Lógica de Adquisición**
```python
@dataclass
class DebtorModel:
    """Deudor consolidado (workflow N8N Adquisicion_v3)"""
    
    # Identificación chilena
    rut: str                      # ← RUT sin formato
    rut_fmt: str                  # ← RUT formateado (12.345.678-9)
    nombre: str                   # ← Nombre completo
    
    # Teléfonos normalizados
    phones: Dict[str, str] = {
        "mobile_e164": "+56912345678",    # ← Móvil internacional
        "landline_e164": "+56221234567",  # ← Fijo internacional
        "best_e164": "+56912345678"       # ← Mejor opción
    }
    
    # Consolidación por RUT
    cantidad_cupones: int         # ← Total de deudas
    monto_total: float            # ← Suma de todos los montos
    
    # Fechas calculadas automáticamente
    fecha_limite: str             # ← Fecha límite calculada
    fecha_maxima: str             # ← Fecha máxima calculada
```

**Por qué es importante**: Implementa la **lógica compleja de agrupación por RUT** que convierte 2,015 filas Excel en 1,924 deudores únicos.

#### **🔹 ContactInfo y CallPayload - Composición**
```python
@dataclass
class ContactInfo:
    """Información de contacto"""
    name: str
    dni: str                      # ← RUT, CUIT, etc. (genérico)
    phones: List[str]             # ← Múltiples teléfonos
    next_phone_index: int = 0     # ← Cual probar siguiente
    
    @property
    def current_phone(self) -> str:
        """Teléfono actual a usar"""

@dataclass  
class CallPayload:
    """Contexto de la conversación"""
    debt_amount: float
    due_date: str
    company_name: str
    
    def to_retell_context(self) -> Dict[str, str]:
        """Convierte a variables para Retell AI"""
        return {
            "monto_total": str(self.debt_amount),
            "fecha_limite": self.due_date,
            "empresa": self.company_name
        }
```

---

## 🏗️ **ARQUITECTURA EXTENSIBLE**

### **3. 🔧 `abstract/base_models.py` - Contratos Base**

Define **interfaces abstractas** para nuevos casos de uso:

```python
@dataclass
class BaseJobPayload(ABC):
    """Contrato para payloads de cualquier caso de uso"""
    
    @abstractmethod
    def to_retell_context(self) -> Dict[str, str]:
        """DEBE convertir a contexto de Retell"""
        
    @abstractmethod
    def get_script_template_id(self) -> str:
        """DEBE retornar ID del script de IA"""
        
    @abstractmethod
    def validate(self) -> List[str]:
        """DEBE validar los datos"""

@dataclass
class BaseJobModel(ABC):
    """Contrato base para jobs de cualquier tipo"""
    account_id: str
    use_case: str                 # ← 'cobranza', 'marketing', etc.
    contact: BaseContactInfo
    payload: BaseJobPayload
```

**Ventaja**: Permite agregar nuevos casos de uso (marketing, encuestas, etc.) sin modificar código existente.

### **4. 🎯 `use_cases/debt_collection.py` - Implementación Específica**

Implementa la **lógica específica de cobranza**:

```python
@dataclass
class DebtCollectionPayload(BaseJobPayload):
    """Payload específico para cobranza"""
    debt_amount: float
    due_date: str
    company_name: str
    days_overdue: int = 0         # ← Específico de cobranza
    
    def to_retell_context(self) -> Dict[str, str]:
        """Contexto específico para IA de cobranza"""
        return {
            "tipo_llamada": "cobranza",
            "monto_total": str(self.debt_amount),
            "dias_vencidos": str(self.days_overdue),
            "empresa": self.company_name
        }
    
    def validate(self) -> List[str]:
        """Validaciones específicas de cobranza"""
        errors = []
        if self.debt_amount <= 0:
            errors.append("Monto debe ser mayor a 0")
        return errors
```

### **5. 🎨 `use_cases/user_experience.py` - Otro Caso de Uso**

```python
@dataclass
class UserExperiencePayload(BaseJobPayload):
    """Payload para encuestas de experiencia"""
    customer_id: str
    product_or_service: str
    satisfaction_target: str      # ← "nps", "satisfaction", etc.
    survey_questions: List[str]
    
    def to_retell_context(self) -> Dict[str, str]:
        """Contexto específico para IA de UX"""
        return {
            "tipo_llamada": "experiencia_usuario",
            "cliente_id": self.customer_id,
            "producto_servicio": self.product_or_service,
            "preguntas_encuesta": "|".join(self.survey_questions)
        }
```

### **6. 🔄 `use_case_registry.py` - Factory Pattern**

Centraliza y registra todos los casos de uso:

```python
class UseCaseRegistry:
    """Registry que conoce todos los casos de uso disponibles"""
    
    def __init__(self):
        self._job_classes = {}
        self._processors = {}
        
        # Auto-registro de casos de uso
        self.register_use_case(
            use_case="debt_collection",
            job_class=DebtCollectionJob,
            processor_class=DebtCollectionProcessor
        )
        
        self.register_use_case(
            use_case="user_experience", 
            job_class=UserExperienceJob,
            processor_class=UserExperienceProcessor
        )
    
    def create_job(self, use_case: str, data: Dict) -> BaseJobModel:
        """Factory method que crea el job correcto según el caso de uso"""
        job_class = self._job_classes[use_case]
        return job_class.from_dict(data)
```

---

## 🎯 **BENEFICIOS DE ESTA ARQUITECTURA**

### **✅ Extensibilidad**
```python
# Agregar nuevo caso de uso es simple:
@dataclass
class MarketingPayload(BaseJobPayload):
    offer_description: str
    discount_percentage: float
    
    def to_retell_context(self) -> Dict[str, str]:
        return {
            "tipo_llamada": "marketing",
            "oferta": self.offer_description,
            "descuento": str(self.discount_percentage)
        }

# El registry lo detecta automáticamente
registry.register_use_case("marketing", MarketingJob, MarketingProcessor)
```

### **✅ Separación de Responsabilidades**
- **`enums.py`**: Estados y constantes del sistema
- **`models.py`**: Entidades core del negocio (cuenta, job, batch)
- **`use_cases/`**: Lógica específica por industria/caso
- **`abstract/`**: Contratos y interfaces

### **✅ Multi-tenant y Multi-caso de uso**
```python
# Un solo sistema maneja múltiples clientes y casos de uso
jobs_queue = [
    JobModel(account_id="empresa_a", use_case="debt_collection"),
    JobModel(account_id="empresa_b", use_case="user_experience"),
    JobModel(account_id="empresa_c", use_case="marketing")
]
```

### **✅ Integración con IA Modular**
```python
# Cada caso de uso define su contexto específico
debt_context = debt_payload.to_retell_context()
# → {"tipo_llamada": "cobranza", "monto_total": "150000"}

ux_context = ux_payload.to_retell_context() 
# → {"tipo_llamada": "experiencia_usuario", "producto": "Tarjeta Premium"}
```

---

## 🚀 **CASOS DE USO ACTUALES**

### **🏦 Cobranza (Implementado al 100%)**
- ✅ Normalización de datos chilenos
- ✅ Agrupación por RUT
- ✅ Múltiples teléfonos por deudor
- ✅ Cálculo automático de fechas
- ✅ 1,924 registros reales funcionando

### **🎯 User Experience (Base implementada)**
- ✅ Framework completo para encuestas
- ✅ Preguntas dinámicas
- ✅ Segmentación por producto/servicio
- ⚠️ Pendiente: Templates de conversación

### **📈 Marketing (Framework listo)**
- ✅ Estructura base preparada
- ✅ Variables para ofertas y descuentos
- ⚠️ Pendiente: Implementación específica

---

## 🔮 **EXPANSIÓN FUTURA FÁCIL**

Con esta arquitectura, agregar **Argentina** sería:

```python
# 1. Nuevo enum
class CountryType(Enum):
    CHILE = "CL"
    ARGENTINA = "AR"    # ← Nuevo

# 2. Nueva implementación
@dataclass  
class ArgentinaDebtPayload(BaseJobPayload):
    cuit: str          # ← En lugar de RUT
    debt_amount_ars: float  # ← Pesos argentinos
    
    def to_retell_context(self) -> Dict[str, str]:
        return {
            "tipo_llamada": "cobranza",
            "monto_total": f"{self.debt_amount_ars:,.0f} pesos",
            "cuit": self.cuit,
            "moneda": "pesos argentinos"
        }

# 3. Auto-registro
registry.register_use_case("debt_collection_argentina", ArgentinaDebtJob)
```

**La arquitectura actual está preparada para esta expansión sin modificaciones mayores.**

---

## 🏆 **CONCLUSIÓN**

Los archivos de domain implementan una **arquitectura empresarial sólida**:

1. **🎯 Extensible**: Nuevos casos de uso sin tocar código existente
2. **🏗️ Mantenible**: Responsabilidades claras y separadas  
3. **🚀 Escalable**: Multi-tenant y multi-país desde el diseño
4. **🤖 IA-Ready**: Integración nativa con conversaciones personalizadas
5. **💰 SaaS-Native**: Modelos de facturación y control de costos integrados

**Esta es la base sólida que permite que tu SaaS escale de Chile a toda LATAM con confianza técnica.** 🌎
