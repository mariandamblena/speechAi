# 💰 Guía de Costos y Rate Limits - Retell AI

## 📋 **Rate Limits de Retell AI**

### Límites oficiales:
- **20-60 requests por minuto** (varía según plan)
- **Llamadas concurrentes**: 5-15 (según suscripción)
- **API timeout**: 30 segundos recomendado

### Configuración recomendada:
```env
# Conservative settings para evitar rate limits
RETELL_RATE_LIMIT_PER_MIN=20
RETELL_CONCURRENT_CALLS=5
WORKER_COUNT=3               # Reducir workers para evitar contención
```

## 💸 **Estructura de Costos**

### Costos por llamada:
- **$0.05-0.10 por minuto** (según plan)
- **Facturación por minuto completo** (redondeo hacia arriba)
- **Costo mínimo**: 1 minuto por llamada

### Costos adicionales:
- ✅ **Integraciones API**: Incluidas sin costo adicional
- ✅ **Webhooks**: Sin costo adicional
- ⚠️ **Overage fees**: Cargos por exceder límites
- ⚠️ **Premium features**: Análisis avanzado, compliance

### Ejemplo de costos mensuales:
```
100 llamadas/día × 2 min promedio × $0.05/min × 30 días = $300/mes
500 llamadas/día × 2 min promedio × $0.05/min × 30 días = $1,500/mes
```

## 🔒 **Compliance (HIPAA, SOC2)**

### Configuraciones requeridas:
```env
COMPLIANCE_MODE=true
PII_LOGGING=false
DATA_RETENTION_DAYS=90
TRANSCRIPT_STORAGE=false     # Para máxima seguridad
```

### Costos adicionales de compliance:
- **SOC2 compliance**: +$50-200/mes
- **HIPAA compliance**: +$100-500/mes
- **Data encryption**: Incluido
- **Audit logs**: +$25-100/mes

## 🚀 **Configuraciones Optimizadas**

### Para **desarrollo/testing**:
```env
WORKER_COUNT=1
RETELL_RATE_LIMIT_PER_MIN=10
MONTHLY_BUDGET=100.00
COMPLIANCE_MODE=false
```

### Para **producción pequeña** (100-500 calls/día):
```env
WORKER_COUNT=3
RETELL_RATE_LIMIT_PER_MIN=20
MONTHLY_BUDGET=500.00
COMPLIANCE_MODE=true
COST_ALERTS_ENABLED=true
```

### Para **producción grande** (500+ calls/día):
```env
WORKER_COUNT=5
RETELL_RATE_LIMIT_PER_MIN=30
MONTHLY_BUDGET=2000.00
COMPLIANCE_MODE=true
OVERAGE_THRESHOLD=0.7        # Alert at 70%
```

## 📊 **Monitoreo y Alertas**

### Dashboard en tiempo real:
```powershell
python production_dashboard.py
```

### Alertas automáticas:
- 🟡 **80% del presupuesto mensual**
- 🔴 **100% del presupuesto mensual**
- ⚠️ **Rate limit al 80%**
- 🚨 **Llamadas fallando repetidamente**

### Métricas clave a monitorear:
- **Rate limit utilization**: <80%
- **Cost per call**: Según presupuesto
- **Success rate**: >95%
- **Average call duration**: Según expectativa

## 🔧 **Optimizaciones de Costos**

### Reducir costos:
1. **Optimizar duración**: Entrenar AI para llamadas más cortas
2. **Rate limiting**: Evitar picos innecesarios
3. **Retry logic**: Limitar reintentos fallidos
4. **Scheduling**: Distribuir llamadas en horarios óptimos

### Worker scaling inteligente:
```env
# Para rate limit de 20/min con 3 workers:
# Máximo teórico: 6.67 calls/worker/min
# Recomendado: 4-5 calls/worker/min para margen
WORKER_COUNT=3
LEASE_SECONDS=180            # Menos conflictos
```

## 🚨 **Gestión de Overages**

### Prevención:
```env
OVERAGE_THRESHOLD=0.8        # Alert at 80%
MONTHLY_BUDGET=1000.00       # Hard limit
COST_ALERTS_ENABLED=true     # Email/Slack alerts
```

### Auto-scaling basado en presupuesto:
```python
# En production_features.py, implementamos:
# - Pause workers at 95% budget
# - Reduce workers at 85% budget
# - Alert at 80% budget
```

## 📈 **ROI y Justificación**

### Comparación de costos:
- **Agente humano**: $15-25/hora
- **Retell AI**: $3-6/hora (promedio)
- **Savings**: 70-80% en costos de personal

### Beneficios adicionales:
- ✅ **24/7 availability**
- ✅ **Consistent quality**
- ✅ **Scalable instantly**
- ✅ **Detailed analytics**
- ✅ **No training costs**

## 🎯 **Comandos Rápidos**

```powershell
# Ver estado actual
python production_dashboard.py

# Configurar presupuesto
echo "MONTHLY_BUDGET=500.00" >> .env

# Activar compliance
echo "COMPLIANCE_MODE=true" >> .env

# Reducir workers para rate limits
echo "WORKER_COUNT=2" >> .env

# Monitor de costos en tiempo real
python -c "
from production_features import initialize_production_features
features = initialize_production_features()
print(features['cost_monitor'].get_cost_summary())
"

# Test de rate limits
python -c "
from production_features import initialize_production_features
features = initialize_production_features()
print(features['rate_limiter'].get_status())
"
```

## 📞 **Contacto y Soporte**

Para optimizaciones específicas de costos:
1. Analizar patrones de llamadas existentes
2. Ajustar rate limits según plan
3. Implementar alertas personalizadas
4. Configurar compliance según industria

¡Maximiza ROI manteniendo costos bajo control! 💰✅