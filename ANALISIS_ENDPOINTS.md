# Análisis de Endpoints Frontend vs Backend

## 📋 Resumen Ejecutivo

Este documento analiza los endpoints que el frontend espera del backend, identifica inconsistencias en la arquitectura y señala funcionalidades incompletas o mal ubicadas.

---

## 🔴 PROBLEMAS PRINCIPALES IDENTIFICADOS

### 1. **Configuraciones de Llamadas en Cuentas (MAL DISEÑO)**

**Problema:** Al crear una cuenta (`CreateAccountModal.tsx`), se están definiendo configuraciones que deberían estar en los batches/campañas:

```typescript
// En CreateAccountRequest (líneas 22-42 de CreateAccountModal.tsx)
settings: {
  allowed_call_hours: {
    start: '09:00',
    end: '18:00'
  },
  timezone: 'America/Santiago',
  retry_settings: {
    max_attempts: 3,
    retry_delay_hours: 24
  }
}
```

**Por qué está mal:**
- ❌ Los horarios de llamada deberían ser por campaña, no por cuenta
- ❌ Los reintentos deberían configurarse por batch/campaña
- ❌ Una cuenta puede tener múltiples campañas con diferentes horarios
- ❌ Esto limita la flexibilidad del sistema

**Solución recomendada:**
- ✅ Mover `allowed_call_hours` a `BatchModel.call_settings`
- ✅ Mover `retry_settings` a `BatchModel.call_settings`
- ✅ Mantener solo configuraciones globales en Account (ej: `max_concurrent_calls`)

---

### 2. **Script Content / Prompt System (NO IMPLEMENTADO)**

**Problema:** El frontend pide `script_content` al crear batches pero NO HAY endpoints para gestionar prompts/scripts:

```typescript
// En CreateBatchRequest (types/index.ts)
export interface CreateBatchRequest {
  script_content: string;  // ← Campo requerido pero sin endpoints de gestión
  // ...
}
```

**Endpoints que NO EXISTEN pero se necesitan:**

```
❌ GET  /api/v1/scripts                    # Listar plantillas de scripts
❌ GET  /api/v1/scripts/{script_id}        # Obtener script específico
❌ POST /api/v1/scripts                    # Crear plantilla de script
❌ PUT  /api/v1/scripts/{script_id}        # Actualizar script
❌ GET  /api/v1/scripts/templates          # Plantillas predefinidas por país/caso de uso
```

**¿Qué se necesita?**
- Sistema de plantillas de prompts por caso de uso
- Variables dinámicas para personalización ({{nombre}}, {{deuda}}, etc.)
- Versionado de scripts
- Pruebas A/B de diferentes scripts

---

## 📊 ENDPOINTS QUE EL FRONTEND ESPERA

### ✅ Endpoints Implementados (Backend existe)

#### **Accounts**
```
✅ POST   /api/v1/accounts                          # Crear cuenta
✅ GET    /api/v1/accounts                          # Listar cuentas
✅ GET    /api/v1/accounts/{id}                     # Obtener cuenta
✅ PUT    /api/v1/accounts/{id}                     # Actualizar cuenta
✅ PUT    /api/v1/accounts/{id}/suspend             # Suspender cuenta
✅ PUT    /api/v1/accounts/{id}/activate            # Activar cuenta
✅ POST   /api/v1/accounts/{id}/topup               # Recargar saldo
✅ GET    /api/v1/accounts/{id}/batches             # Batches de una cuenta
✅ GET    /api/v1/accounts/{id}/transactions        # Transacciones de cuenta
```

#### **Batches**
```
✅ POST   /api/v1/batches                           # Crear batch
✅ GET    /api/v1/batches                           # Listar batches
✅ GET    /api/v1/batches/{id}                      # Obtener batch
✅ GET    /api/v1/batches/{id}/jobs                 # Jobs de un batch
✅ PUT    /api/v1/batches/{id}/pause                # Pausar batch
✅ PUT    /api/v1/batches/{id}/resume               # Reanudar batch
✅ DELETE /api/v1/batches/{id}                      # Eliminar batch
✅ POST   /api/v1/batches/{id}/upload               # Subir CSV al batch
✅ POST   /api/v1/batches/excel/preview             # Preview de Excel
✅ POST   /api/v1/batches/excel/create              # Crear desde Excel
✅ POST   /api/v1/batches/chile/debt_collection     # Chile cobranza
✅ POST   /api/v1/batches/chile/marketing           # Chile marketing
✅ POST   /api/v1/batches/argentina/debt_collection # Argentina cobranza
✅ POST   /api/v1/batches/argentina/marketing       # Argentina marketing
```

#### **Jobs**
```
✅ GET    /api/v1/jobs                              # Listar jobs
✅ GET    /api/v1/jobs/{id}                         # Obtener job
✅ PUT    /api/v1/jobs/{id}/retry                   # Reintentar job
✅ DELETE /api/v1/jobs/{id}                         # Cancelar job
```

#### **Dashboard**
```
✅ GET    /api/v1/dashboard/stats                   # Estadísticas dashboard
✅ GET    /api/v1/calls/history                     # Historial de llamadas
```

#### **Health**
```
✅ GET    /health                                   # Health check
```

---

### ❌ Endpoints que Frontend Espera pero NO EXISTEN

#### **Account Stats (parcial)**
```
❌ GET /api/v1/accounts/{id}/balance     # Balance detallado
❌ GET /api/v1/accounts/{id}/stats       # Estadísticas de cuenta
```

#### **Batch Management (parcial)**
```
❌ GET  /api/v1/batches/{id}/summary     # Resumen detallado del batch
❌ GET  /api/v1/batches/{id}/status      # Estado en tiempo real
❌ POST /api/v1/batches/{id}/cancel      # Cancelar batch (no confundir con pause)
```

#### **Scripts/Prompts (CRÍTICO - NO EXISTE)**
```
❌ GET  /api/v1/scripts                  # Listar scripts disponibles
❌ GET  /api/v1/scripts/{id}             # Obtener script específico
❌ POST /api/v1/scripts                  # Crear nuevo script
❌ PUT  /api/v1/scripts/{id}             # Actualizar script
❌ GET  /api/v1/scripts/templates        # Plantillas predefinidas
❌ GET  /api/v1/use-cases                # Casos de uso disponibles
```

#### **Reports (PLACEHOLDER)**
```
❌ GET  /api/v1/reports                  # Listar reportes
❌ POST /api/v1/reports/generate         # Generar reporte
```

**Nota:** Los endpoints de reports están como placeholder en el frontend:
```typescript
export const useReports = () => {
  return useQuery({
    queryKey: ['reports'],
    queryFn: async () => {
      return {
        reports: [],
        message: 'Reports endpoint not implemented yet',
      };
    },
  });
};
```

---

## 🎯 RECOMENDACIONES DE ARQUITECTURA

### **1. Separar Configuraciones de Cuenta vs Campaña**

#### Configuraciones de CUENTA (globales, límites)
```typescript
interface AccountSettings {
  max_concurrent_calls: number;      // Límite técnico
  timezone: string;                  // Zona horaria de la cuenta
  api_rate_limit?: number;           // Límite de API
  notification_email?: string;       // Email para notificaciones
}
```

#### Configuraciones de BATCH/CAMPAÑA (por campaña)
```typescript
interface BatchCallSettings {
  max_call_duration: number;         // Duración máxima por llamada
  ring_timeout: number;              // Timeout de ring
  max_attempts: number;              // Reintentos por contacto
  retry_delay_hours: number;         // Delay entre reintentos
  allowed_hours: {                   // Horarios permitidos
    start: string;
    end: string;
  };
  days_of_week: number[];            // Días permitidos
  timezone: string;                  // Puede sobrescribir el de la cuenta
}
```

### **2. Sistema de Scripts/Prompts**

Implementar un sistema completo de gestión de prompts:

```typescript
interface ScriptTemplate {
  _id: string;
  template_id: string;
  name: string;
  description: string;
  country: 'chile' | 'argentina' | 'peru' | 'generic';
  use_case: 'debt_collection' | 'marketing' | 'surveys' | 'custom';
  content: string;                    // Contenido con variables {{variable}}
  variables: ScriptVariable[];        // Variables disponibles
  voice_settings_default: VoiceSettings;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ScriptVariable {
  name: string;                       // Ej: "nombre", "deuda"
  type: 'string' | 'number' | 'date';
  required: boolean;
  default_value?: any;
}
```

**Endpoints necesarios:**
```
POST   /api/v1/scripts/templates                    # Crear plantilla
GET    /api/v1/scripts/templates                    # Listar plantillas
GET    /api/v1/scripts/templates/{id}               # Obtener plantilla
PUT    /api/v1/scripts/templates/{id}               # Actualizar plantilla
DELETE /api/v1/scripts/templates/{id}               # Eliminar plantilla
GET    /api/v1/scripts/templates/by-use-case/{use_case}  # Por caso de uso
POST   /api/v1/scripts/render                       # Renderizar con variables
```

### **3. Mejorar el Wizard de Creación de Batch**

El wizard actual está incompleto. Necesita:

**Paso 1: Seleccionar Cuenta y Caso de Uso**
- Seleccionar cuenta
- Seleccionar país (Chile, Argentina, Perú)
- Seleccionar caso de uso (Cobranza, Marketing, Encuestas)

**Paso 2: Configurar Script**
- Seleccionar plantilla de script o crear custom
- Configurar variables dinámicas
- Preview del script con datos de ejemplo
- Configuración de voz (idioma, velocidad, tono)

**Paso 3: Subir Contactos**
- Upload Excel/CSV
- Mapeo automático de columnas
- Validación de datos
- Preview de contactos

**Paso 4: Configuración de Llamadas**
- Horarios permitidos
- Días de la semana
- Reintentos y delays
- Duración máxima

**Paso 5: Programación**
- Inicio inmediato
- Programar fecha/hora
- Configurar recurrencia

**Paso 6: Revisión y Confirmación**
- Resumen de todo
- Costo estimado
- Confirmar y crear

---

## 🔧 ACCIONES INMEDIATAS RECOMENDADAS

### **Prioridad ALTA 🔴**

1. **Mover configuraciones de llamada a Batches**
   - Quitar `call_settings` de `AccountModel`
   - Asegurarse que `BatchModel.call_settings` sea la fuente de verdad
   - Actualizar `CreateAccountModal` para no pedir estos datos

2. **Implementar sistema de Scripts/Prompts**
   - Crear modelo `ScriptTemplate` en backend
   - Implementar CRUD de scripts
   - Crear endpoint de renderizado de variables
   - Agregar plantillas predefinidas por país/caso de uso

3. **Completar endpoints faltantes críticos**
   - `/accounts/{id}/balance` - Balance detallado
   - `/accounts/{id}/stats` - Estadísticas
   - `/batches/{id}/summary` - Resumen completo
   - `/batches/{id}/status` - Estado en tiempo real

### **Prioridad MEDIA 🟡**

4. **Mejorar el Wizard de Batches**
   - Integrar selector de scripts/plantillas
   - Agregar preview de script con variables
   - Mejorar validación de Excel/CSV
   - Agregar estimación de costos

5. **Sistema de Reportes**
   - Implementar generación de reportes
   - Exportar a CSV/Excel
   - Reportes por cuenta, batch, período
   - Métricas de rendimiento

### **Prioridad BAJA 🟢**

6. **Optimizaciones**
   - WebSocket para actualizaciones en tiempo real
   - Cache de scripts/plantillas
   - Compresión de archivos Excel grandes
   - Batch de validación de números telefónicos

---

## 📝 EJEMPLOS DE USO CORRECTO

### **Crear Cuenta (simplificado)**
```typescript
// CORRECTO - Sin configuraciones de llamada
const accountData = {
  account_name: "Empresa ABC",
  contact_name: "Juan Pérez",
  contact_email: "juan@empresa.com",
  contact_phone: "+56912345678",
  plan_type: "credit_based",
  initial_credits: 1000,
  features: {
    max_concurrent_calls: 5,
    voice_cloning: false,
    advanced_analytics: true
  }
  // NO incluir allowed_call_hours, retry_settings aquí
};
```

### **Crear Batch con Configuraciones**
```typescript
// CORRECTO - Configuraciones en el batch
const batchData = {
  account_id: "acc_123",
  name: "Campaña Cobranza Octubre",
  script_template_id: "template_chile_debt_001",  // Nueva
  script_variables: {                              // Nueva
    company_name: "Empresa ABC",
    contact_email: "cobranza@empresa.com"
  },
  call_settings: {
    max_call_duration: 300,
    ring_timeout: 30,
    max_attempts: 3,
    retry_delay_hours: 24,
    allowed_hours: {
      start: "09:00",
      end: "18:00"
    },
    days_of_week: [1, 2, 3, 4, 5],
    timezone: "America/Santiago"
  },
  // ... resto de configuración
};
```

---

## 🎨 MOCKUP DE NUEVA UI PARA SCRIPTS

### **Selector de Script (nueva pantalla)**
```
┌─────────────────────────────────────────────────┐
│  Seleccionar Script para la Campaña            │
├─────────────────────────────────────────────────┤
│                                                 │
│  País: [Chile ▼]  Caso de Uso: [Cobranza ▼]   │
│                                                 │
│  Plantillas Disponibles:                        │
│  ┌─────────────────────────────────────────┐   │
│  │ ☑ Script Cobranza Formal Chile          │   │
│  │   Tono profesional, menciona datos...   │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │ ☐ Script Cobranza Amigable Chile        │   │
│  │   Tono conversacional, empático...      │   │
│  └─────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────┐   │
│  │ ☐ Custom (crear propio)                 │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  [Vista Previa] [Editar] [Siguiente →]         │
└─────────────────────────────────────────────────┘
```

### **Editor de Script con Variables**
```
┌─────────────────────────────────────────────────┐
│  Editar Script                                  │
├─────────────────────────────────────────────────┤
│  Contenido:                                     │
│  ┌─────────────────────────────────────────┐   │
│  │ Hola {{nombre}}, le llamo de            │   │
│  │ {{company_name}}. Tenemos registrado    │   │
│  │ que tiene una deuda pendiente de        │   │
│  │ {{debt_amount}} pesos con vencimiento   │   │
│  │ al {{due_date}}. ¿Podría confirmar...   │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  Variables Disponibles:                         │
│  • {{nombre}} - Nombre del contacto            │
│  • {{company_name}} - Nombre de la empresa     │
│  • {{debt_amount}} - Monto de deuda            │
│  • {{due_date}} - Fecha de vencimiento         │
│  [+ Agregar variable]                           │
│                                                 │
│  Vista Previa con Datos de Ejemplo:            │
│  ┌─────────────────────────────────────────┐   │
│  │ Hola Juan Pérez, le llamo de Empresa   │   │
│  │ ABC. Tenemos registrado que tiene una   │   │
│  │ deuda pendiente de $150.000 pesos con   │   │
│  │ vencimiento al 30/10/2025...            │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
│  [🔊 Probar Audio] [Guardar] [Siguiente →]     │
└─────────────────────────────────────────────────┘
```

---

## 📚 DOCUMENTACIÓN ADICIONAL NECESARIA

Para el backend, crear documentación de:

1. **API de Scripts/Prompts**
   - Cómo crear plantillas
   - Sistema de variables
   - Versionado de scripts

2. **Guía de Migración**
   - Mover configuraciones de Account a Batch
   - Actualizar modelos existentes
   - Scripts de migración de datos

3. **Best Practices**
   - Cuándo usar configuraciones de cuenta vs batch
   - Cómo estructurar scripts eficientes
   - Límites y restricciones

---

## 🏁 CONCLUSIÓN

### Problemas Principales:
1. ❌ Configuraciones de llamadas mal ubicadas (en Account en vez de Batch)
2. ❌ Sistema de Scripts/Prompts completamente ausente
3. ❌ Varios endpoints críticos faltantes
4. ❌ Wizard de creación de batches incompleto

### Solución:
1. ✅ Refactorizar modelo de datos (Account vs Batch settings)
2. ✅ Implementar sistema completo de Scripts/Prompts
3. ✅ Completar endpoints faltantes
4. ✅ Mejorar UX del wizard de batches

### Impacto:
- **Sin cambios:** Sistema poco flexible, difícil de mantener
- **Con cambios:** Sistema modular, escalable y user-friendly
