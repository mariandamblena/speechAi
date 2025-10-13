# 📁 Scripts del Backend SpeechAI

## 🚀 Scripts Disponibles

### 1. **init_sample_data.py** 
Inicializa la base de datos con datos de ejemplo para desarrollo y testing.

**Qué crea:**
- 3 cuentas de ejemplo (Strasing Corp, Fintech Solutions, Retail Express)
- 3 batches por cuenta con estados variados
- 5 jobs por batch (completed, failed, pending)
- 6 transacciones por cuenta (últimos 30 días)

**Uso:**
```bash
cd app
python scripts/init_sample_data.py
```

### 2. **test_endpoints.py**
Verifica que los 4 endpoints implementados funcionan correctamente.

**Qué prueba:**
- `GET /api/v1/accounts`
- `GET /api/v1/accounts/{account_id}/batches`  
- `GET /api/v1/accounts/{account_id}/transactions`
- `GET /api/v1/batches/{batch_id}/jobs`

**Uso:**
```bash
cd app
python scripts/test_endpoints.py
```

### 3. **generate_reports.py**
Genera reportes de jobs en formato Excel (script existente).

**Uso:**
```bash
cd app
python scripts/generate_reports.py
```

## 🔄 Flujo de Trabajo Recomendado

1. **Inicializar datos**: `python scripts/init_sample_data.py`
2. **Verificar endpoints**: `python scripts/test_endpoints.py`
3. **Iniciar API**: `python run_api.py`
4. **Probar desde frontend**: Los endpoints están listos para consumir

## 📊 Datos de Ejemplo Creados

### Cuentas
- **strasing**: 1500 créditos, Plan créditos
- **fintech_solutions**: 850 minutos, Plan minutos  
- **retail_express**: 50 créditos, Plan créditos (suspendida)

### Transacciones por Cuenta
- Recargas de plan mensual
- Usos en campañas específicas
- Bonos promocionales
- Histórico de 30 días

### Jobs con Estados Reales
- **Completed**: CAROLA BELEN ORELLANA SANDOVAL
- **Failed**: MAGALY IVETTE MORALES, Carol Espinoza, Marcela Alejandra, ISABEL ALEJANDRA
- **Pending**: Algunos jobs nuevos

¡Todo listo para que el frontend consuma los datos! 🎉