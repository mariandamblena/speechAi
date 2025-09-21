# Proyecto de Automatización de Cobranzas

## 📄 Descripción del Sistema
Este sistema automatiza el proceso de contacto con deudores, ejecutando llamadas telefónicas mediante un agente de voz con IA.  
Integra una base de datos central con manejo de reglas de contacto, historial de llamadas, control de intentos y agendamiento inteligente.  
Su objetivo es optimizar la recuperación de deuda y reducir costos operativos.

---

## 📌 Requerimientos de Usuario
- Contactar automáticamente a un grupo de 60 deudores por día en tandas (9:00, 12:00, 15:00).
- No llamar más de 3 veces por día a la misma persona.
- Si se han hecho llamadas en 3 días diferentes sin respuesta, excluir de la lista.
- Permitir reagendado cuando el deudor lo solicite.
- Ejecutar un flujo de negociación según tipo de mora.
- Guardar historial de llamadas y resultado.
- Integrarse con sistemas MCP/Webhook para disparar acciones externas (ej: enviar link de pago por WhatsApp).
- Recuperarse automáticamente ante fallos o reinicios del servidor.
- Panel de control para ver estado y métricas.

---

## 🎯 Requerimientos de Diseño
- Arquitectura modular basada en N8N + Base de Datos SQL/Supabase.
- Separación de capas:  
  1. **Catálogos** (parámetros, reglas y configuraciones).  
  2. **Núcleo Operativo** (lógica de contacto, manejo de estados y timers).  
  3. **Operación** (registro de llamadas, reintentos y resultados).
- Resiliencia ante caídas del sistema (retomar proceso en el último punto).
- Escalabilidad para aumentar volumen de llamadas.
- Seguridad: acceso a la base con credenciales y cifrado en tránsito.
- Uso de variables dinámicas para personalizar el diálogo del agente.

---

## 🗄 Diagramas Entidad-Relación

### DER – Catálogos
![DER Catálogos](./catalogosDer.png)

### DER – Núcleo Operativo
![DER Núcleo Operativo](./nucleoOperativoDer.png)

### DER – Operación
![DER Operación](./operacionDer.png)

---

## 🔄 Diagrama de Flujo Temporal (Ejemplo)
*(Aquí iría otro diagrama UML o de flujo mostrando el proceso de llamadas, reintentos y exclusiones)*

---

## 📂 Estructura de Archivos
