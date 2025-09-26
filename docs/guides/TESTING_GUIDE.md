# 📋 Guía de Tests y Scripts

## 🧪 **Ejecutar Tests**

### Tests Individuales
```bash
cd app

# Test de estructura y imports
python tests/test_structure.py

# Test completo de Excel batch (requiere MongoDB)
python tests/test_excel_batch.py

# Test de API (requiere servidor corriendo)
python tests/test_api.py
```

### Todos los Tests
```bash
cd app
python -m pytest tests/ -v
```

## 🛠️ **Scripts de Desarrollo**

### Configuración Inicial
```bash
cd app

# Crear índices de MongoDB (ejecutar una vez)
python scripts/create_indexes.py

# Inicializar datos de prueba
python scripts/init_data.py
```

### Utilidades de Desarrollo
```bash
# Generar Excel de muestra
python scripts/generate_sample_excel.py

# Reset de un job específico
python scripts/reset_job.py <job_id>
```

## 📁 **Archivos por Categoría**

### 🚀 **Producción** (app/)
- `api.py` - Endpoints principales
- `run_api.py` - Servidor FastAPI
- `call_worker.py` - Worker de llamadas
- `config/` - Configuración
- `domain/` - Modelos y enums
- `infrastructure/` - DB y servicios externos
- `services/` - Lógica de negocio
- `utils/` - Utilidades generales

### 🧪 **Testing** (app/tests/)
- `test_structure.py` - Tests de estructura
- `test_excel_batch.py` - Tests de Excel processing
- `test_api.py` - Tests de API REST

### 🔧 **Scripts** (app/scripts/)
- `create_indexes.py` - Setup de MongoDB
- `init_data.py` - Datos de prueba
- `generate_sample_excel.py` - Excel de muestra
- `reset_job.py` - Utilidad de desarrollo

### 📚 **Documentación** (docs/)
- `workflows/` - Archivos JSON de n8n
- Varios archivos README.md

## 🎯 **Comandos Rápidos**

```bash
# Inicializar proyecto desde cero
cd app
python scripts/create_indexes.py
python scripts/init_data.py

# Verificar que todo funciona
python tests/test_structure.py

# Correr servidor
python run_api.py

# Test completo del sistema
python tests/test_excel_batch.py
```

## 🔄 **Flujo de Desarrollo**

1. **Setup inicial**: `create_indexes.py` + `init_data.py`
2. **Desarrollo**: Modificar código en `app/`
3. **Testing**: Ejecutar tests desde `tests/`
4. **Deploy**: Solo usar archivos de `app/` (sin tests/ ni scripts/)