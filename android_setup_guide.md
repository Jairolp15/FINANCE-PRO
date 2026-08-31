# 🤖 Guía de Configuración para Android (MacroDroid / Tasker / PWA)

En Android tienes dos opciones de alta eficiencia para capturar gastos en 2 segundos:
1. **PWA / Web App (Acceso Directo)** -> Opción sin aplicaciones pagadas, ultra-rápida.
2. **MacroDroid / Tasker (Formulario Emergente Flotante)** -> Integración nativa a nivel de sistema.

---

## 🟢 Opción A: Acceso Directo PWA (Recomendada - 1 minuto de setup)

1. Abre Chrome o Edge en tu dispositivo Android.
2. Navega a la URL de tu servidor: `http://TU_DOMINIO_O_IP:8000/pwa`.
3. Toca el menú de 3 puntos (esquina superior derecha) de Chrome.
4. Selecciona **"Añadir a la pantalla de inicio"** (Add to Home Screen).
5. Se creará un icono interactivo en tu pantalla principal de Android que funciona como una app nativa con teclado listo para ingresar el monto en 1 segundo.

---

## 🤖 Opción B: Automatización con MacroDroid

### Paso 1: Crear una Macro
1. Descarga **MacroDroid** desde Google Play Store.
2. Toca **Añadir Macro**.
3. Nombre: `Registrar Gasto Rápido`.

### Paso 2: Disparador (Trigger)
- Elige el disparador que prefieras:
  - **Acceso directo en pantalla de inicio**.
  - **Agitar dispositivo**.
  - **Botón flotante en pantalla**.

### Paso 3: Acciones (Actions)

1. **Cuadro de Diálogo: Ingresar Monto**
   - Acción: `Variables de MacroDroid` -> `Fijar Variable`.
   - Variable: `gasto_monto` (Tipo: Decimal).
   - Utiliza la acción `Solicitar entrada del usuario` con título: `Ingresa el monto`.

2. **Seleccionar Categoría**
   - Acción: `Opciones de usuario / Cuadro de lista`.
   - Nombre de lista: `Categorías`.
   - Opciones: `Alimentación`, `Transporte`, `Ocio`, `Servicios`, `Salud`, `Educación`, `Otros`.
   - Guardar selección en variable: `gasto_categoria`.

3. **Ingresar Nota / Descripción**
   - Variable: `gasto_nota` (Tipo: Texto).
   - Acción: `Solicitar entrada del usuario` (Texto opcional).

4. **Petición HTTP Webhook POST**
   - Acción: `Abrir sitio web / Solicitud HTTP`.
   - Selecciona **Solicitud HTTP POST**.
   - URL: `http://TU_DOMINIO_O_IP:8000/api/v1/expense`
   - Content-Type: `application/json`
   - Body:
     ```json
     {
       "amount": {v=gasto_monto},
       "category": "{v=gasto_categoria}",
       "payment_method": "Tarjeta",
       "description": "{v=gasto_nota}"
     }
     ```

5. **Notificación Toast**
   - Acción: `Mostrar notificación Toast` -> *"Gasto guardado en Notion y Dashboard"*.
