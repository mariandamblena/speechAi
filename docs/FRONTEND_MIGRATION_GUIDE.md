# 📢 AVISO IMPORTANTE PARA FRONTEND - Cambios en API

**Fecha:** 28 de Octubre, 2025  
**Urgencia:** Media (cambios opcionales, sin breaking changes)  
**Branch Backend:** `refactor/eliminate-job-duplicates`

---

## 🎯 Resumen Ejecutivo

Hemos consolidado endpoints duplicados en la API para seguir mejores prácticas RESTful. Los endpoints antiguos **siguen funcionando** pero están **deprecados** y se eliminarán en v2.0.0.

**⏰ Timeline:**
- **Ahora:** Endpoints deprecados funcionan normalmente
- **3 meses:** Período de migración recomendado
- **v2.0.0:** Se eliminarán endpoints deprecados

---

## 🔄 Cambios Requeridos en Frontend

### 1. ⚠️ Pausar/Reanudar Batches

#### ❌ ANTES (Deprecado - funciona pero no usar)
```typescript
// Pausar
await api.put(`/api/v1/batches/${batchId}/pause`);

// Reanudar
await api.put(`/api/v1/batches/${batchId}/resume`);
```

#### ✅ AHORA (Recomendado)
```typescript
// Pausar
await api.patch(`/api/v1/batches/${batchId}`, {
  is_active: false
});

// Reanudar
await api.patch(`/api/v1/batches/${batchId}`, {
  is_active: true
});

// 🎁 BONUS: Ahora puedes actualizar múltiples campos a la vez
await api.patch(`/api/v1/batches/${batchId}`, {
  is_active: true,
  priority: 2,
  name: "Nuevo nombre",
  call_settings: {
    max_attempts: 5,
    retry_delay_hours: 12
  }
});
```

**Beneficio:** ✅ Una sola llamada para pausar Y actualizar otros campos

---

### 2. ⚠️ Suspender/Activar Cuentas

#### ❌ ANTES (Deprecado - funciona pero no usar)
```typescript
// Suspender
await api.put(`/api/v1/accounts/${accountId}/suspend`, {
  reason: "No payment"
});

// Activar
await api.put(`/api/v1/accounts/${accountId}/activate`);
```

#### ✅ FUTURO (Cuando backend implemente PATCH accounts)
```typescript
// Suspender
await api.patch(`/api/v1/accounts/${accountId}`, {
  status: "suspended",
  suspension_reason: "No payment"
});

// Activar
await api.patch(`/api/v1/accounts/${accountId}`, {
  status: "active"
});
```

**Nota:** Por ahora sigan usando los endpoints antiguos para cuentas, el cambio es solo informativo.

---

### 3. ✅ Cancelar Jobs (Ya actualizado)

#### ❌ ANTES
```typescript
await api.delete(`/api/v1/jobs/${jobId}`);
```

#### ✅ AHORA
```typescript
await api.put(`/api/v1/jobs/${jobId}/cancel`);
```

**Razón del cambio:** DELETE es para eliminar físicamente, PUT/cancel es para cambiar estado a "cancelled"

---

## 📋 Checklist de Migración

### Cambios Obligatorios (Implementar pronto)

- [ ] **Batches:** Cambiar `PUT /pause` y `PUT /resume` por `PATCH` con `is_active`
- [ ] **Jobs:** Cambiar `DELETE /jobs/{id}` por `PUT /jobs/{id}/cancel`
- [ ] Actualizar tests del frontend
- [ ] Verificar en staging que todo funciona

### Cambios Opcionales (Mejoras recomendadas)

- [ ] **Batches:** Aprovechar PATCH para actualizar múltiples campos a la vez
- [ ] **call_settings:** Usar configuración por batch (ver sección siguiente)
- [ ] Eliminar referencias a endpoints deprecados del código

---

## 🆕 Nueva Funcionalidad: call_settings por Batch

Ahora pueden configurar horarios y reintentos específicos por campaña:

### Ejemplo de Uso

```typescript
// Al crear batch desde Excel
const formData = new FormData();
formData.append('file', file);
formData.append('account_id', accountId);
formData.append('batch_name', 'Campaña Cobranza Urgente');

// ⭐ NUEVO: Configuración específica de esta campaña
const callSettings = {
  max_attempts: 5,              // 5 reintentos (vs default 3)
  retry_delay_hours: 12,        // Cada 12 horas (vs default 24)
  allowed_hours: {
    start: "09:00",
    end: "20:00"                // Horario extendido
  },
  days_of_week: [1,2,3,4,5,6], // Incluye sábados
  timezone: "America/Santiago",
  max_concurrent_calls: 10
};

formData.append('call_settings_json', JSON.stringify(callSettings));

await api.post('/api/v1/batches/excel/create', formData);
```

### Escenarios de Uso

#### Campaña de Cobranza Urgente
```typescript
{
  max_attempts: 5,
  retry_delay_hours: 12,
  allowed_hours: { start: "09:00", end: "20:00" }
}
```

#### Campaña de Marketing (No invasiva)
```typescript
{
  max_attempts: 2,
  retry_delay_hours: 48,
  allowed_hours: { start: "10:00", end: "17:00" },
  days_of_week: [1,2,3,4,5]  // Solo días laborales
}
```

#### Campaña Estándar (Usar defaults)
```typescript
// No enviar call_settings = usa configuración de la cuenta
```

---

## 🛠️ Guía de Actualización del Código

### Paso 1: Crear servicio helper (Recomendado)

```typescript
// services/api/batches.ts

export class BatchService {
  
  // ✅ Nuevo método unificado
  async updateBatch(batchId: string, updates: {
    is_active?: boolean;
    name?: string;
    description?: string;
    priority?: number;
    call_settings?: CallSettings;
  }) {
    return api.patch(`/api/v1/batches/${batchId}`, updates);
  }

  // Métodos convenientes
  async pauseBatch(batchId: string) {
    return this.updateBatch(batchId, { is_active: false });
  }

  async resumeBatch(batchId: string) {
    return this.updateBatch(batchId, { is_active: true });
  }
}
```

### Paso 2: Actualizar componentes

```typescript
// ❌ ANTES
const handlePause = async () => {
  await api.put(`/api/v1/batches/${batchId}/pause`);
};

const handleResume = async () => {
  await api.put(`/api/v1/batches/${batchId}/resume`);
};

// ✅ AHORA
const handlePause = async () => {
  await batchService.pauseBatch(batchId);
  // o directamente:
  // await api.patch(`/api/v1/batches/${batchId}`, { is_active: false });
};

const handleResume = async () => {
  await batchService.resumeBatch(batchId);
};
```

---

## 📖 Respuestas de la API

### PATCH /api/v1/batches/{batch_id}

**Response exitoso:**
```json
{
  "success": true,
  "message": "Batch paused",
  "batch_id": "batch-2025-10-28-143000-abc123",
  "updated_fields": ["is_active", "priority"]
}
```

**Error (batch no existe):**
```json
{
  "detail": "Batch not found"
}
```

---

## 🧪 Testing

### Tests Mínimos Requeridos

```typescript
describe('Batch Updates', () => {
  it('should pause batch using PATCH', async () => {
    const response = await api.patch(`/batches/${batchId}`, {
      is_active: false
    });
    expect(response.success).toBe(true);
    expect(response.message).toBe('Batch paused');
  });

  it('should update multiple fields at once', async () => {
    const response = await api.patch(`/batches/${batchId}`, {
      is_active: true,
      priority: 2,
      name: 'New name'
    });
    expect(response.updated_fields).toContain('is_active');
    expect(response.updated_fields).toContain('priority');
    expect(response.updated_fields).toContain('name');
  });
});
```

---

## ❓ FAQ - Preguntas Frecuentes

### ¿Los endpoints antiguos dejarán de funcionar?
**R:** No inmediatamente. Siguen funcionando pero están marcados como deprecados. Se eliminarán en v2.0.0 (en varios meses).

### ¿Tenemos que migrar todo ahora?
**R:** No es urgente, pero recomendamos hacerlo en las próximas semanas para evitar deuda técnica.

### ¿Qué pasa si no migramos?
**R:** Seguirá funcionando hasta v2.0.0, pero estarán usando endpoints deprecados.

### ¿El backend ya está actualizado?
**R:** Sí, está en el branch `refactor/eliminate-job-duplicates`. Los nuevos endpoints PATCH ya funcionan.

### ¿Dónde está la documentación completa?
**R:** En el repositorio backend:
- `docs/API_ENDPOINTS_REFERENCE.md` - Documentación completa de todos los endpoints
- `docs/CODE_CLEANUP_SUMMARY.md` - Detalles técnicos de los cambios

---

## 📞 Contacto

Si tienen dudas o encuentran problemas:

1. ✅ Revisar `docs/API_ENDPOINTS_REFERENCE.md` en el repo backend
2. ✅ Probar los endpoints en Postman/Insomnia con los ejemplos de arriba
3. ✅ Contactar al equipo de backend si algo no funciona

---

## ✅ Resumen de Acción

**Lo que tienen que hacer:**

1. 📝 Leer este documento
2. 🔄 Actualizar llamadas a `PUT /pause` y `PUT /resume` por `PATCH` con `is_active`
3. 🔄 Actualizar llamadas a `DELETE /jobs/{id}` por `PUT /jobs/{id}/cancel`
4. ✅ (Opcional) Aprovechar para actualizar múltiples campos a la vez con PATCH
5. ✅ (Opcional) Implementar `call_settings` para campañas específicas
6. 🧪 Testear en staging
7. 🚀 Deploy a producción

**Tiempo estimado:** 2-4 horas de desarrollo + testing

---

**Última actualización:** 28 de Octubre, 2025  
**Preparado por:** Backend Team  
**Versión:** 1.0
