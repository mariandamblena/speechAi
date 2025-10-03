# 📊 Generadores de Reportes de Llamadas

Este directorio contiene tres scripts para generar reportes en Excel con los datos de las llamadas realizadas por el sistema.

## 🎯 Scripts Disponibles

### 1. `reportes.py` - Launcher Principal ⭐
Menú interactivo para acceso fácil a todas las funciones.

**Características:**
- ✅ Menú intuitivo con opciones numeradas
- ✅ Reportes rápidos con un clic
- ✅ Filtros avanzados guiados
- ✅ Verificación automática de dependencias
- ✅ Nombres de archivo automáticos
- ✅ Ayuda integrada

### 2. `generate_call_report.py` - Script Completo
Script avanzado con múltiples opciones de filtrado y formato profesional.

**Características:**
- ✅ Filtros avanzados por cuenta, batch, fechas, estado
- ✅ Formato Excel profesional con tablas y estilos
- ✅ Hoja de resumen con estadísticas detalladas
- ✅ Información completa: transcripciones, URLs, variables capturadas
- ✅ Cálculos de costos y duraciones
- ✅ Análisis de tasas de éxito y motivos de desconexión

### 3. `simple_report.py` - Script Rápido
Script simplificado para reportes cotidianos.

**Características:**
- ✅ Argumentos de línea de comandos
- ✅ Filtro por días hacia atrás
- ✅ Reporte básico con datos esenciales
- ✅ Hoja de resumen con métricas clave
- ✅ Generación rápida

## 🛠️ Instalación de Dependencias

Antes de usar los scripts, instala las dependencias necesarias:

```bash
pip install pandas openpyxl python-dotenv
```

## 🚀 Uso Rápido (Recomendado)

### Launcher Principal
```bash
python reportes.py
```

Esto abrirá un menú interactivo con todas las opciones:
1. Reporte rápido (últimos 7 días)
2. Reporte personalizado por días
3. Reporte de cuenta específica
4. Reporte de batch específico
5. Reporte con rango de fechas
6. Ver estadísticas rápidas
7. Ayuda completa

## 🛠️ Uso Avanzado

### Script Rápido
```bash
# Últimos 7 días
python simple_report.py --days 7

# Últimos 30 días con nombre personalizado
python simple_report.py --days 30 --output "reporte_mes.xlsx"

# Modo interactivo
python simple_report.py --interactive
```

### Script Completo

### Ejemplos de Uso

```bash
# Reporte de todas las llamadas
python generate_call_report.py

# Reporte de los últimos 30 días
python generate_call_report.py --days 30

# Reporte de una cuenta específica
python generate_call_report.py --account-id "cuenta123"

# Reporte de un batch específico
python generate_call_report.py --batch-id "batch456"

# Reporte por rango de fechas
python generate_call_report.py --start-date 2025-09-01 --end-date 2025-09-30

# Reporte solo de llamadas exitosas
python generate_call_report.py --status completed

# Reporte con nombre personalizado
python generate_call_report.py --output "reporte_septiembre.xlsx"

# Reporte sin hoja de resumen
python generate_call_report.py --no-summary
```

### Parámetros Disponibles

| Parámetro | Descripción | Ejemplo |
|-----------|-------------|---------|
| `--account-id` | Filtrar por cuenta específica | `--account-id "cuenta123"` |
| `--batch-id` | Filtrar por batch específico | `--batch-id "batch456"` |
| `--start-date` | Fecha de inicio (YYYY-MM-DD) | `--start-date 2025-09-01` |
| `--end-date` | Fecha de fin (YYYY-MM-DD) | `--end-date 2025-09-30` |
| `--days` | Últimos N días | `--days 30` |
| `--status` | Filtrar por estado | `--status completed` |
| `--output` | Nombre del archivo de salida | `--output "mi_reporte.xlsx"` |
| `--no-summary` | No incluir hoja de resumen | `--no-summary` |

### Estados Válidos para Filtro

- `pending` - Llamadas pendientes
- `in_progress` - Llamadas en progreso
- `completed` - Llamadas completadas
- `done` - Llamadas terminadas
- `failed` - Llamadas fallidas
- `suspended` - Llamadas suspendidas

## 🎮 Uso del Launcher (Más Fácil)

```bash
# Abrir menú interactivo
python reportes.py
```

El launcher te guiará paso a paso para:
- Generar reportes rápidos
- Configurar filtros personalizados  
- Verificar estadísticas
- Obtener ayuda contextual

## 🎮 Uso del Script Rápido

```bash
# Con argumentos
python simple_report.py --days 7 --output "mi_reporte.xlsx"

# Modo interactivo
python simple_report.py --interactive
```

El script te preguntará:
1. **Días hacia atrás**: Cuántos días incluir (default: 7)
2. **Nombre del archivo**: Nombre personalizado o automático

## 📊 Contenido de los Reportes

### Datos Incluidos en el Reporte

#### Información Básica
- **ID Job**: Identificador único del trabajo
- **Cuenta**: ID de la cuenta
- **Lote**: ID del batch
- **Nombre Contacto**: Nombre de la persona contactada
- **RUT/DNI**: Documento de identidad
- **Teléfono**: Número contactado
- **Monto Deuda**: Cantidad adeudada

#### Estado y Resultado
- **Resultado Final**: Categorización del resultado
- **Estado Job**: Estado técnico del trabajo
- **Estado Llamada**: Estado específico de la llamada
- **Éxito**: Indicador booleano de éxito
- **Motivo Desconexión**: Razón del fin de llamada

#### Tiempos y Fechas
- **Creado**: Cuándo se creó el job
- **Iniciado**: Cuándo empezó la llamada
- **Terminado**: Cuándo terminó la llamada
- **Finalizado**: Cuándo se completó el procesamiento
- **Duración**: Tiempo de llamada en formato legible
- **Minutos**: Duración en minutos decimales

#### Costos e Información de Llamada
- **Costo (USD)**: Costo de la llamada
- **URL Grabación**: Link a la grabación
- **URL Log Público**: Link al log público
- **ID Llamada Retell**: Identificador en Retell
- **Transcripción**: Texto completo de la conversación

#### Variables Capturadas
- **Fecha Pago Prometida**: Fecha comprometida por el cliente
- **Monto Pago Prometido**: Cantidad prometida
- **Variables Capturadas**: Todas las variables dinámicas

### Hoja de Resumen

La hoja de resumen incluye:

#### Estadísticas Generales
- Total de llamadas
- Llamadas exitosas y fallidas
- Tasa de éxito
- Costo total y tiempo total
- Duración promedio

#### Análisis por Estado
- Distribución de resultados
- Porcentajes por categoría
- Conteos detallados

## 🎨 Formato del Excel

### Características del Formato
- **Tablas estructuradas** con filtros automáticos
- **Colores profesionales** en headers
- **Anchos de columna optimizados** para legibilidad
- **Texto envuelto** en campos largos
- **Bordes y estilos** consistentes
- **Alineación vertical** para mejor lectura

### Hojas Incluidas
1. **Llamadas Detalladas**: Datos completos de cada llamada
2. **Resumen**: Estadísticas y análisis agregado

## 🔧 Solución de Problemas

### Error: "Dependencias faltantes"
```bash
pip install pandas openpyxl python-dotenv
```

### Error: "No se puede conectar a la base de datos"
- Verificar que el archivo `.env` esté en la carpeta `app/`
- Confirmar que la variable `MONGO_URI` sea correcta
- Asegurar que MongoDB esté ejecutándose

### Error: "No se encontraron llamadas"
- Verificar los filtros aplicados
- Comprobar que existan datos en el período especificado
- Revisar que el `account_id` o `batch_id` sean correctos

### Error: "Permisos de archivo"
- Cerrar el archivo Excel si está abierto
- Verificar permisos de escritura en el directorio
- Cambiar el nombre del archivo de salida

## 💡 Consejos de Uso

### Para Reportes Diarios
```bash
python simple_report.py
# Seleccionar 1 día hacia atrás
```

### Para Reportes Mensuales
```bash
python generate_call_report.py --days 30 --output "reporte_mensual.xlsx"
```

### Para Análisis de Cuenta Específica
```bash
python generate_call_report.py --account-id "tu_cuenta" --days 60
```

### Para Análisis de Campañas
```bash
python generate_call_report.py --batch-id "tu_batch" --include-summary
```

## 📈 Métricas Calculadas

### Tasa de Éxito
```
Tasa de Éxito = (Llamadas Exitosas / Total Llamadas) × 100
```

### Costo por Llamada Exitosa
```
Costo por Éxito = Costo Total / Llamadas Exitosas
```

### Duración Promedio
```
Duración Promedio = Tiempo Total / Llamadas Exitosas
```

### ROI Estimado
```
ROI = (Recuperación Prometida - Costo Total) / Costo Total × 100
```

## 🔮 Próximas Mejoras

- [ ] Filtros por horario específico
- [ ] Exportación a PDF
- [ ] Gráficos automáticos
- [ ] Comparación entre períodos
- [ ] Alertas automáticas
- [ ] Integración con dashboard web

---

**¿Necesitas ayuda?** Revisa los logs de error o contacta al equipo de desarrollo.