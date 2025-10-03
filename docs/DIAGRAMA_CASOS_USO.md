# 👥 Diagrama de Casos de Uso - SpeechAI Backend

```mermaid
graph TB
    %% ===== ACTORES =====
    Admin[👤 Administrador del Sistema]
    Operator[👤 Operador de Llamadas]
    Customer[👤 Cliente/Deudor]
    RetellAI[🤖 Retell AI]
    System[⚙️ Sistema Automatizado]

    %% ===== CASOS DE USO PRINCIPALES =====
    subgraph "📊 Gestión de Datos"
        UC1[Cargar Excel con Contactos]
        UC2[Crear Batch de Llamadas]
        UC3[Validar Formato de Datos]
        UC4[Configurar Variables del Prompt]
    end

    subgraph "📞 Procesamiento de Llamadas"
        UC5[Procesar Job de Llamada]
        UC6[Crear Llamada en Retell AI]
        UC7[Hacer Seguimiento de Estado]
        UC8[Registrar Resultado de Llamada]
        UC9[Gestionar Reintentos]
        UC10[Rotar Números de Teléfono]
    end

    subgraph "🎛️ Control del Sistema"
        UC11[Pausar/Reanudar Batch]
        UC12[Iniciar/Detener Workers]
        UC13[Monitorear Estado del Sistema]
        UC14[Liberar Jobs Colgados]
        UC15[Configurar Parámetros]
    end

    subgraph "📈 Reportes y Análisis"
        UC16[Generar Reporte de Jobs]
        UC17[Exportar Datos a Excel]
        UC18[Analizar Tasas de Éxito]
        UC19[Revisar Costos de Llamadas]
        UC20[Generar Métricas en Tiempo Real]
    end

    subgraph "🔧 Mantenimiento"
        UC21[Realizar Backup de Datos]
        UC22[Limpiar Jobs Antiguos]
        UC23[Actualizar Configuración]
        UC24[Diagnosticar Problemas]
    end

    %% ===== RELACIONES ACTOR-CASO DE USO =====
    
    %% Administrador
    Admin --> UC1
    Admin --> UC2
    Admin --> UC11
    Admin --> UC12
    Admin --> UC13
    Admin --> UC14
    Admin --> UC15
    Admin --> UC16
    Admin --> UC17
    Admin --> UC21
    Admin --> UC22
    Admin --> UC23
    Admin --> UC24

    %% Operador
    Operator --> UC1
    Operator --> UC2
    Operator --> UC11
    Operator --> UC13
    Operator --> UC16
    Operator --> UC17
    Operator --> UC18
    Operator --> UC19
    Operator --> UC20

    %% Sistema Automatizado
    System --> UC3
    System --> UC4
    System --> UC5
    System --> UC6
    System --> UC7
    System --> UC8
    System --> UC9
    System --> UC10
    System --> UC20

    %% Retell AI (Actor Externo)
    RetellAI --> UC6
    RetellAI --> UC7
    RetellAI --> UC8

    %% Cliente (Receptor de llamadas)
    Customer -.-> UC8
    Customer -.-> UC9

    %% ===== DEPENDENCIAS ENTRE CASOS DE USO =====
    UC1 --> UC3 : includes
    UC2 --> UC4 : includes
    UC5 --> UC6 : includes
    UC6 --> UC7 : includes
    UC7 --> UC8 : includes
    UC8 --> UC9 : extends
    UC9 --> UC10 : extends
    UC16 --> UC17 : extends
    UC18 --> UC19 : includes
    UC22 --> UC24 : includes

    %% ===== ESTILOS =====
    classDef actor fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef usecase fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef system fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef external fill:#fff3e0,stroke:#e65100,stroke-width:2px

    class Admin,Operator,Customer actor
    class UC1,UC2,UC3,UC4,UC5,UC6,UC7,UC8,UC9,UC10,UC11,UC12,UC13,UC14,UC15,UC16,UC17,UC18,UC19,UC20,UC21,UC22,UC23,UC24 usecase
    class System system
    class RetellAI external
```

## 📋 Descripción Detallada de Casos de Uso

### 📊 **Gestión de Datos**

#### UC1: Cargar Excel con Contactos
- **Actor**: Administrador, Operador
- **Descripción**: Cargar archivo Excel con información de contactos
- **Precondiciones**: Usuario autenticado, formato Excel válido
- **Flujo Principal**:
  1. Usuario selecciona archivo Excel
  2. Sistema valida formato del archivo
  3. Sistema detecta tipo de caso de uso (cobranza, marketing, etc.)
  4. Sistema procesa y valida datos
  5. Sistema confirma carga exitosa
- **Postcondiciones**: Datos disponibles para crear batch

#### UC2: Crear Batch de Llamadas
- **Actor**: Administrador, Operador
- **Descripción**: Crear lote de trabajos de llamadas
- **Flujo Principal**:
  1. Usuario define parámetros del batch
  2. Sistema valida configuración
  3. Sistema crea jobs individuales
  4. Sistema asigna prioridades
  5. Sistema activa batch para procesamiento

### 📞 **Procesamiento de Llamadas**

#### UC5: Procesar Job de Llamada
- **Actor**: Sistema Automatizado
- **Descripción**: Worker procesa un job individual
- **Flujo Principal**:
  1. Worker reserva job disponible
  2. Worker extrae información del contacto
  3. Worker prepara variables del prompt
  4. Worker solicita creación de llamada
  5. Worker inicia seguimiento de estado

#### UC6: Crear Llamada en Retell AI
- **Actor**: Sistema, Retell AI
- **Descripción**: Crear llamada automática via API
- **Flujo Principal**:
  1. Sistema prepara payload de llamada
  2. Sistema envía request a Retell AI
  3. Retell AI valida parámetros
  4. Retell AI inicia llamada
  5. Retell AI retorna call_id

#### UC9: Gestionar Reintentos
- **Actor**: Sistema Automatizado
- **Descripción**: Manejar reintentos automáticos
- **Flujo Principal**:
  1. Sistema detecta fallo en llamada
  2. Sistema evalúa si debe reintentar
  3. Sistema programa próximo intento
  4. Sistema actualiza contador de intentos
  5. Sistema libera job para reintento

### 🎛️ **Control del Sistema**

#### UC11: Pausar/Reanudar Batch
- **Actor**: Administrador, Operador
- **Descripción**: Control de ejecución de batches
- **Flujo Principal**:
  1. Usuario selecciona batch activo
  2. Usuario solicita pausa/reanudación
  3. Sistema actualiza estado del batch
  4. Sistema notifica a workers
  5. Sistema confirma cambio de estado

#### UC12: Iniciar/Detener Workers
- **Actor**: Administrador
- **Descripción**: Control del pool de workers
- **Flujo Principal**:
  1. Administrador configura número de workers
  2. Sistema valida recursos disponibles
  3. Sistema inicia/detiene threads de workers
  4. Sistema confirma estado de workers
  5. Sistema actualiza métricas

### 📈 **Reportes y Análisis**

#### UC16: Generar Reporte de Jobs
- **Actor**: Administrador, Operador
- **Descripción**: Crear reporte detallado del sistema
- **Flujo Principal**:
  1. Usuario selecciona parámetros del reporte
  2. Sistema consulta base de datos
  3. Sistema procesa estadísticas
  4. Sistema genera reporte en formato solicitado
  5. Sistema entrega archivo de reporte

#### UC18: Analizar Tasas de Éxito
- **Actor**: Operador
- **Descripción**: Análisis de rendimiento del sistema
- **Flujo Principal**:
  1. Sistema calcula métricas de éxito
  2. Sistema segmenta por batch, fecha, tipo
  3. Sistema identifica patrones
  4. Sistema genera visualizaciones
  5. Sistema presenta análisis

### 🔧 **Mantenimiento**

#### UC22: Limpiar Jobs Antiguos
- **Actor**: Administrador
- **Descripción**: Mantenimiento de base de datos
- **Flujo Principal**:
  1. Sistema identifica jobs antiguos
  2. Sistema valida que sean eliminables
  3. Sistema respalda datos críticos
  4. Sistema elimina registros antiguos
  5. Sistema optimiza índices

---

## 🔄 Flujos de Excepción Comunes

### ❌ **Excepciones de Llamadas**
- **Número ocupado**: Reintento con delay
- **No contesta**: Reintento con delay mayor
- **Número inválido**: Cambio a siguiente teléfono
- **Error de API**: Reintento con backoff exponencial

### ❌ **Excepciones del Sistema**
- **Worker desconectado**: Liberación automática de jobs
- **Base de datos inaccesible**: Modo de espera y reconexión
- **Archivo Excel inválido**: Reporte de errores específicos
- **Falta de créditos**: Suspensión automática de batch

### ❌ **Excepciones de Configuración**
- **Credenciales inválidas**: Bloqueo de operaciones
- **Parámetros incorrectos**: Validación y notificación
- **Límites excedidos**: Throttling automático

---

## 🎯 **Métricas de Casos de Uso**

| Caso de Uso | Frecuencia | Criticidad | Actores Principales |
|-------------|------------|------------|-------------------|
| UC5: Procesar Job | Muy Alta | Crítica | Sistema |
| UC6: Crear Llamada | Muy Alta | Crítica | Sistema, Retell AI |
| UC7: Seguimiento Estado | Muy Alta | Crítica | Sistema |
| UC1: Cargar Excel | Media | Alta | Operador |
| UC11: Control Batch | Media | Alta | Administrador |
| UC16: Generar Reporte | Baja | Media | Operador |
| UC22: Limpiar Jobs | Muy Baja | Baja | Administrador |