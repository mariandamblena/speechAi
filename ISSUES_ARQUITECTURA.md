# 🚨 Issues Críticos de Arquitectura

## 📋 Resumen Ejecutivo

Este documento analiza los endpoints que el frontend espera del backend, identifica inconsistencias en la arquitectura y señala funcionalidades incompletas o mal ubicadas.

---

## 🔴 PROBLEMAS PRINCIPALES IDENTIFICADOS

> **NOTA:** El Problema #2 (Sistema de Scripts/Prompts) está marcado como NO PRIORITARIO y se trabajará en el futuro.
> **PRIORIDAD ACTUAL:** Problemas #1 y #3

### 1. **Configuraciones de Llamadas en Cuentas (MAL DISEÑO)** ⚠️ PRIORITARIO

```
ACTUAL (INCORRECTO):
┌─────────────────────────┐
│   ACCOUNT (Cuenta)      │
│ ─────────────────────── │
│ • allowed_call_hours ❌ │
│ • timezone ❌           │
│ • retry_settings ❌     │
│ • max_concurrent_calls✅│
└─────────────────────────┘
        │
        ├── Batch A (09:00-18:00) → No puede cambiar horarios
        ├── Batch B (10:00-20:00) → No puede cambiar horarios
        └── Batch C (08:00-12:00) → No puede cambiar horarios

DEBERÍA SER:
┌─────────────────────────┐
│   ACCOUNT (Cuenta)      │
│ ─────────────────────── │
│ • max_concurrent_calls✅│
│ • timezone (default) ✅ │
└─────────────────────────┘
        │
        ├── Batch A: 09:00-18:00, 3 reintentos ✅
        ├── Batch B: 10:00-20:00, 5 reintentos ✅
        └── Batch C: 08:00-12:00, 2 reintentos ✅
```

**Por qué es importante:**
- Una empresa puede necesitar diferentes horarios para diferentes campañas
- Cobranza urgente: 09:00-20:00, 5 reintentos
- Marketing: 10:00-18:00, 2 reintentos
- Encuestas: 11:00-16:00, 1 intento

---

### 🎯 RECOMENDACIONES DE ARQUITECTURA

> **NOTA:** Las recomendaciones del Sistema de Scripts (#2) se mantendrán para referencia futura pero NO se implementarán ahora.

### **1. Separar Configuraciones de Cuenta vs Campaña** ⚠️ PRIORITARIO

```
ACTUAL (INCORRECTO):
┌──────────────────────────────────────┐
│ CreateBatchModal                     │
│ ──────────────────────────────────── │
│ Script Content:                      │
│ ┌──────────────────────────────────┐ │
│ │ [textarea vacío]                 │ │
│ │ Usuario tiene que escribir TODO  │ │
│ │ el script desde cero cada vez... │ │
│ └──────────────────────────────────┘ │
│                                      │
│ ❌ No hay plantillas                 │
│ ❌ No hay variables dinámicas        │
│ ❌ No hay reutilización              │
└──────────────────────────────────────┘

DEBERÍA SER:
┌──────────────────────────────────────┐
│ ScriptSelector                       │
│ ──────────────────────────────────── │
│ País: [Chile ▼] Caso: [Cobranza ▼]  │
│                                      │
│ Plantillas Disponibles:              │
│ ☑ Script Cobranza Formal             │
│ ☐ Script Cobranza Amigable           │
│ ☐ Script Marketing                   │
│ ☐ Custom                             │
│                                      │
│ Vista Previa:                        │
│ ┌──────────────────────────────────┐ │
│ │ Hola {{nombre}}, le llamo de     │ │
│ │ {{empresa}}. Registramos deuda   │ │
│ │ de {{monto}} vencida al {{fecha}}│ │
│ └──────────────────────────────────┘ │
│                                      │
│ ✅ Plantillas reutilizables          │
│ ✅ Variables dinámicas               │
│ ✅ Versionado                        │
└──────────────────────────────────────┘
```

---

### ❌ Endpoints que Frontend Espera pero NO EXISTEN ⚠️ PRIORITARIO

#### **Account Stats (parcial)** ⚠️ PRIORITARIO

```
ENDPOINTS IMPLEMENTADOS:
✅ POST   /accounts
✅ GET    /accounts
✅ POST   /batches
✅ GET    /batches
✅ GET    /jobs

ENDPOINTS QUE FRONTEND LLAMA PERO NO EXISTEN:
❌ GET    /accounts/{id}/balance      ← Frontend lo pide
❌ GET    /accounts/{id}/stats        ← Frontend lo pide
❌ GET    /batches/{id}/summary       ← Frontend lo pide
❌ GET    /batches/{id}/status        ← Frontend lo pide, polling cada 5s
❌ POST   /batches/{id}/cancel        ← Diferente a pause

ENDPOINTS QUE NECESITAMOS PARA SCRIPTS:
❌ GET    /scripts/templates          ← No existe sistema
❌ POST   /scripts                    ← No existe sistema
❌ GET    /scripts/{id}               ← No existe sistema
❌ POST   /scripts/render             ← Renderizar variables
```

---

## 📊 Flujo de Creación de Batch (Actual vs Ideal)

### ACTUAL (Problemático):

```
1. Abrir CreateBatchModal
   └─> Usuario debe escribir script completo manualmente
   └─> Usuario define horarios (aunque ya los definió en Account)
   └─> Sube Excel
   └─> Crear

❌ Mucho trabajo manual
❌ No reutilización
❌ Propenso a errores
❌ Configuraciones duplicadas
```

### IDEAL (Recomendado):

```
**Paso 1: Seleccionar Cuenta y Caso de Uso**
- Seleccionar cuenta
- Nombre de la campaña
- Descripción

**Paso 2: Configurar Script** _(mantener como está - textarea simple)_
- Campo de texto para script_content
- Configuración de voz (idioma, velocidad, tono)

**Paso 3: Subir Contactos**

6. Configurar Llamadas (POR BATCH)
   └─> Horarios permitidos
   └─> Días de semana
   └─> Reintentos
   └─> (puede sobrescribir defaults de Account)

7. Programar
   └─> Inmediato / Programado / Recurrente

8. Revisión y Confirmación
   └─> Resumen completo
   └─> Costo estimado
   └─> Crear

✅ Workflow completo
✅ Reutilización de plantillas
✅ Menos errores
✅ Mejor UX
```

---

## 🎯 Tabla de Decisión: ¿Dónde va cada configuración?

| Configuración | ¿En Account? | ¿En Batch? | Razón |
|--------------|--------------|------------|-------|
| `max_concurrent_calls` | ✅ SÍ | ❌ NO | Límite técnico de la cuenta |
| `allowed_call_hours` | ❌ NO | ✅ SÍ | Varía por campaña |
| `days_of_week` | ❌ NO | ✅ SÍ | Varía por campaña |
| `max_attempts` | ❌ NO | ✅ SÍ | Varía por campaña |
| `retry_delay_hours` | ❌ NO | ✅ SÍ | Varía por campaña |
| `timezone` (default) | ✅ SÍ | ⚠️ OPCIONAL | Account tiene default, Batch puede sobrescribir |
| `script_content` | ❌ NO | ✅ SÍ | Específico de campaña |
| `voice_settings` | ❌ NO | ✅ SÍ | Varía por campaña |
| `priority` | ❌ NO | ✅ SÍ | Varía por campaña |
| `schedule_type` | ❌ NO | ✅ SÍ | Específico de campaña |

---

## 🔧 Cambios Necesarios en el Código

### 1. Refactorizar `CreateAccountModal.tsx`

**ANTES (líneas 118-172):**
```tsx
<div className="space-y-4">
  <h3 className="text-lg font-medium text-gray-900">Configuraciones de Llamadas</h3>
  
  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
    <Input
      label="Hora de Inicio"
      type="time"
      value={formData.settings.allowed_call_hours.start}
      onChange={(e) => handleTimeChange('start', e.target.value)}
    />
    {/* ... más configuraciones de llamadas ... */}
  </div>
</div>
```

**DESPUÉS:**
```tsx
<div className="space-y-4">
  <h3 className="text-lg font-medium text-gray-900">Configuraciones de Cuenta</h3>
  
  <Input
    label="Zona Horaria por Defecto"
    select
    value={formData.settings.timezone}
    onChange={(e) => handleSettingChange('timezone', e.target.value)}
  >
    <option value="America/Santiago">Santiago (GMT-3)</option>
    <option value="America/Argentina/Buenos_Aires">Buenos Aires (GMT-3)</option>
  </Input>
  
  <p className="text-sm text-gray-500">
    ℹ️ Los horarios de llamada, días de la semana y reintentos se configuran 
    en cada campaña/batch individualmente.
  </p>
</div>
```

### 2. Agregar `ScriptSelector` Component

**Nuevo componente:** `src/components/scripts/ScriptSelector.tsx`

```tsx
interface ScriptSelectorProps {
  country: 'chile' | 'argentina';
  useCase: 'debt_collection' | 'marketing';
  onScriptSelect: (script: ScriptTemplate) => void;
}

export const ScriptSelector: React.FC<ScriptSelectorProps> = ({
  country,
  useCase,
  onScriptSelect
}) => {
  const { data: templates } = useScriptTemplates(country, useCase);
  
  return (
    <div className="space-y-4">
      <h3>Seleccionar Script</h3>
      
      {templates?.map(template => (
        <div key={template.id} className="border rounded-lg p-4">
          <h4>{template.name}</h4>
          <p>{template.description}</p>
          <Button onClick={() => onScriptSelect(template)}>
            Usar esta plantilla
          </Button>
        </div>
      ))}
      
      <Button variant="secondary" onClick={/* crear custom */}>
        Crear script personalizado
      </Button>
    </div>
  );
};
```

### 3. Actualizar `CreateBatchModal.tsx`

Agregar paso de selección de script antes de configurar llamadas:

```tsx
const steps = [
  { title: 'Información Básica', description: 'Cuenta y nombre' },
  { title: 'Script', description: 'Seleccionar o crear script' },  // ← NUEVO
  { title: 'Contactos', description: 'Cargar datos desde Excel' },
  { title: 'Configuración de Llamadas', description: 'Horarios y reintentos' }, // ← Ahora aquí
  { title: 'Programación', description: 'Cuándo ejecutar' }
];
```

---

## 🎨 Mockup de Nuevas Pantallas

### Pantalla: Script Template Manager

```
┌─────────────────────────────────────────────────────────────────┐
│  Gestión de Plantillas de Scripts                    [+ Nueva]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Filtros: País: [Todos ▼]  Caso de Uso: [Todos ▼]  [🔍 Buscar]│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 📄 Cobranza Formal - Chile                    [✏️ Editar]  ││
│  │ ─────────────────────────────────────────────────────────  ││
│  │ Tono profesional para recordatorio de pagos pendientes.   ││
│  │ Variables: nombre, empresa, deuda, fecha_vencimiento      ││
│  │ Usado en: 45 campañas                                     ││
│  │ [👁️ Ver] [📋 Duplicar] [🗑️ Eliminar]                      ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 📄 Cobranza Amigable - Chile                 [✏️ Editar]   ││
│  │ ─────────────────────────────────────────────────────────  ││
│  │ Tono conversacional y empático para facilitar el pago.    ││
│  │ Variables: nombre, empresa, deuda, opciones_pago          ││
│  │ Usado en: 23 campañas                                     ││
│  │ [👁️ Ver] [📋 Duplicar] [🗑️ Eliminar]                      ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐│
│  │ 📄 Marketing Promocional - Argentina         [✏️ Editar]   ││
│  │ ─────────────────────────────────────────────────────────  ││
│  │ Script para ofrecer productos o servicios.                ││
│  │ Variables: nombre, producto, descuento, vigencia          ││
│  │ Usado en: 12 campañas                                     ││
│  │ [👁️ Ver] [📋 Duplicar] [🗑️ Eliminar]                      ││
│  └────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Pantalla: Editor de Script

```
┌─────────────────────────────────────────────────────────────────┐
│  Editar Plantilla: Cobranza Formal - Chile          [Guardar]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Información Básica:                                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Nombre: [Cobranza Formal - Chile                        ]│  │
│  │ País:   [Chile ▼]                                        │  │
│  │ Caso:   [Cobranza ▼]                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Contenido del Script:                                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Buenos días, mi nombre es Ana y llamo de {{empresa}}.    │  │
│  │ ¿Hablo con {{nombre}}?                                   │  │
│  │                                                           │  │
│  │ Le contacto porque tenemos registrada una deuda          │  │
│  │ pendiente de {{deuda}} pesos, con vencimiento al         │  │
│  │ {{fecha_vencimiento}}. ¿Podría confirmar si recibió      │  │
│  │ la información de esta deuda?                            │  │
│  │                                                           │  │
│  │ [Insertar Variable ▼]                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Variables Disponibles:                                         │
│  • {{nombre}} - Nombre del contacto                            │
│  • {{empresa}} - Nombre de la empresa                          │
│  • {{deuda}} - Monto de la deuda                               │
│  • {{fecha_vencimiento}} - Fecha de vencimiento                │
│  [+ Agregar variable personalizada]                             │
│                                                                  │
│  Configuración de Voz:                                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Idioma:    [Español Chile ▼]                            │  │
│  │ Velocidad: [─────●────] 1.0x                            │  │
│  │ Tono:      [─────●────] Normal                          │  │
│  │ Volumen:   [───────●──] 0.8                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Vista Previa con Datos de Ejemplo:                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Buenos días, mi nombre es Ana y llamo de Empresa ABC.    │  │
│  │ ¿Hablo con Juan Pérez?                                   │  │
│  │                                                           │  │
│  │ Le contacto porque tenemos registrada una deuda          │  │
│  │ pendiente de $150.000 pesos, con vencimiento al          │  │
│  │ 30/10/2025. ¿Podría confirmar si recibió la información  │  │
│  │ de esta deuda?                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  [🔊 Escuchar Preview]  [Cancelar]  [Guardar Plantilla]        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Checklist de Implementación

### Backend

- [ ] **Modelos de Scripts**
  - [ ] Crear modelo `ScriptTemplate`
  - [ ] Agregar campos: name, content, variables, country, use_case
  - [ ] Migrar datos existentes

- [ ] **Endpoints de Scripts**
  - [ ] `GET /scripts/templates` - Listar plantillas
  - [ ] `POST /scripts/templates` - Crear plantilla
  - [ ] `GET /scripts/templates/{id}` - Obtener plantilla
  - [ ] `PUT /scripts/templates/{id}` - Actualizar plantilla
  - [ ] `DELETE /scripts/templates/{id}` - Eliminar plantilla
  - [ ] `POST /scripts/render` - Renderizar con variables
  - [ ] `GET /scripts/templates/by-use-case/{country}/{use_case}` - Filtrar

- [ ] **Endpoints Faltantes**
  - [ ] `GET /accounts/{id}/balance` - Balance detallado
  - [ ] `GET /accounts/{id}/stats` - Estadísticas cuenta
  - [ ] `GET /batches/{id}/summary` - Resumen batch
  - [ ] `GET /batches/{id}/status` - Estado en tiempo real
  - [ ] `POST /batches/{id}/cancel` - Cancelar batch

- [ ] **Refactor de Modelos**
  - [ ] Mover `allowed_call_hours` de Account a Batch
  - [ ] Mover `retry_settings` de Account a Batch
  - [ ] Agregar `script_template_id` a Batch
  - [ ] Agregar `script_variables` a Batch
  - [ ] Script de migración para datos existentes

### Frontend

- [ ] **Nuevos Componentes**
  - [ ] `ScriptSelector.tsx` - Selector de plantillas
  - [ ] `ScriptEditor.tsx` - Editor de scripts
  - [ ] `ScriptPreview.tsx` - Preview con variables
  - [ ] `VariableMapper.tsx` - Mapeo de variables Excel

- [ ] **Actualizar Componentes Existentes**
  - [ ] Simplificar `CreateAccountModal.tsx` (quitar configuraciones de llamadas)
  - [ ] Actualizar `CreateBatchModal.tsx` (agregar paso de script)
  - [ ] Mejorar `NewBatchWizard.tsx` (integrar selector de scripts)

- [ ] **Nuevos Hooks**
  - [ ] `useScriptTemplates()` - Listar plantillas
  - [ ] `useCreateScriptTemplate()` - Crear plantilla
  - [ ] `useUpdateScriptTemplate()` - Actualizar plantilla
  - [ ] `useRenderScript()` - Renderizar con variables

- [ ] **Actualizar Types**
  - [ ] Agregar `ScriptTemplate` interface
  - [ ] Agregar `ScriptVariable` interface
  - [ ] Actualizar `CreateBatchRequest` (agregar script_template_id)
  - [ ] Actualizar `AccountModel` (quitar call_settings)

### Documentación

- [ ] Documentar API de Scripts
- [ ] Guía de migración de datos
- [ ] Tutorial de uso de plantillas
- [ ] Best practices para scripts efectivos

---

## 🚀 Plan de Implementación por Fases

### Fase 1: Endpoints Críticos (1 semana)
1. Implementar endpoints faltantes de Account y Batch
2. Testear con Postman/Insomnia
3. Actualizar frontend para usar nuevos endpoints

### Fase 2: Sistema de Scripts (2 semanas)
1. Crear modelos de ScriptTemplate
2. Implementar CRUD de scripts
3. Sistema de renderizado de variables
4. Plantillas predefinidas (Chile/Argentina)

### Fase 3: Refactor Frontend (1.5 semanas)
1. Crear componentes de scripts
2. Actualizar wizard de batches
3. Simplificar CreateAccountModal
4. Testing end-to-end

### Fase 4: Migración de Datos (0.5 semana)
1. Script de migración de configuraciones
2. Validar datos migrados
3. Rollback plan

### Total: ~5 semanas

---

## 💡 Beneficios de los Cambios

### Para Usuarios
- ✅ Crear campañas más rápido (plantillas reutilizables)
- ✅ Menos errores (validación de scripts)
- ✅ Más flexibilidad (diferentes configs por campaña)
- ✅ Mejor UX (wizard guiado paso a paso)

### Para el Negocio
- ✅ Más ventas (clientes pueden crear campañas fácilmente)
- ✅ Menos soporte (menos errores de usuario)
- ✅ Mejor producto (sistema profesional y escalable)

### Para Desarrollo
- ✅ Código más limpio (separación de responsabilidades)
- ✅ Más mantenible (modelos bien definidos)
- ✅ Más escalable (sistema de plantillas reutilizable)
- ✅ Menos bugs (arquitectura correcta desde el inicio)
