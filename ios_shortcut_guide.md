# 📱 Guía de Configuración de Atajo de iOS (Shortcuts) para Registro Rápido de Gastos

Esta guía te explica paso a paso cómo crear un **Atajo de iOS (Shortcut)** ejecutable desde el **Botón de Acción (iPhone 15 Pro/16)**, **Widget en Pantalla de Inicio** o por comando de voz con **Siri**.

---

## 🚀 Paso 1: Abrir la Aplicación "Atajos" (Shortcuts)
1. Abre la app **Atajos** en tu iPhone.
2. Toca el botón **`+`** (esquina superior derecha) para crear un nuevo atajo.
3. Nómbralo: `Registrar Gasto`.

---

## ⚙️ Paso 2: Agregar las Acciones del Atajo

### 1. Solicitar Monto
- Busca y agrega la acción **Solicitar entrada** (Ask for Input).
- Configúrala como:
  - **Tipo**: Número
  - **Pregunta**: `¿Cuánto gastaste?`

### 2. Guardar Monto en Variable
- Busca la acción **Establecer variable** (Set Variable).
- Nombre de variable: `Monto`.

### 3. Seleccionar Categoría
- Busca la acción **Elegir de menú** (Choose from Menu).
- Agrega las opciones:
  - 🍔 Alimentación
  - 🚗 Transporte
  - 🎬 Ocio
  - 💡 Servicios
  - 🏥 Salud
  - 📚 Educación
  - 📦 Otros

### 4. Definir Categoría en Variable
- Dentro de cada opción del menú, agrega una acción **Establecer variable** llamada `Categoria` asignándole el texto de la categoría seleccionada (ej: `Alimentación`, `Transporte`, etc.).

### 5. Seleccionar Método de Pago
- Busca otra acción **Elegir de menú**.
- Agrega las opciones: `Tarjeta`, `Efectivo`, `Transferencia`.
- Guarda la selección en una variable llamada `MetodoPago`.

### 6. Solicitar Nota u Descripción (Opcional)
- Busca **Solicitar entrada**.
- Tipo: Texto
- Pregunta: `Descripción o nota (opcional):`
- Guarda en variable: `Descripcion`.

### 7. Formatear Payload JSON
- Busca la acción **Texto** (Text) y pega el siguiente esquema JSON (usando las variables mágicas de iOS):

```json
{
  "amount": Monto,
  "category": "Categoria",
  "payment_method": "MetodoPago",
  "description": "Descripcion"
}
```

### 8. Enviar Petición HTTP Webhook
- Busca la acción **Obtener contenido de URL** (Get Contents of URL).
- **URL**: `http://TU_DOMINIO_O_IP:8000/api/v1/expense` (o tu URL de Ngrok / Cloudflare Tunnel / VPS).
- **Método**: `POST`
- **Cabeceras** (Headers):
  - `Content-Type`: `application/json`
- **Cuerpo del mensaje** (Request Body): Selecciona `Texto` (el bloque JSON del paso anterior).

---

## 🎯 Paso 3: Asignar Métodos de Activación Rápida (Compatible con TODO tipo de iPhone)

Para que funcione en **cualquier modelo de iPhone** (desde iPhone 8 / SE hasta iPhone 16 Pro), puedes elegir entre cualquiera de estos métodos de activación inmediata:

---

### 1. 👆 Toque Posterior / Tocar Atrás (*Back Tap*) — *Para iPhone 8, X, 11, 12, 13, 14, 15, 16*
Te permite registrar un gasto dando **2 toques con el dedo en la parte trasera del iPhone**:
1. Ve a **Ajustes** ➔ **Accesibilidad** ➔ **Tocar**.
2. Desplázate al final y pulsa **Tocar atrás** (Back Tap).
3. Selecciona **Tocar dos veces** o **Tocar tres veces**.
4. En la sección "Atajos", selecciona **Registrar Gasto**.
*¡Listo! Con solo dar dos golpecitos en la manzana trasera del teléfono se abrirá el formulario.*

---

### 2. 📱 Icono en la Pantalla de Inicio (*Home Screen*) — *Para el 100% de los iPhones*
1. Abre la app **Atajos**.
2. Toca los tres puntos `...` de tu atajo **Registrar Gasto**.
3. Toca el botón de **Compartir** (o el icono de ajustes/detalles en la esquina) y elige **Añadir a pantalla de inicio**.
4. Puedes elegirle un icono de tarjeta/monedas y un color personalizado.
*Quedará como una app más en tu pantalla de inicio.*

---

### 3. 🔒 Widget en Pantalla de Bloqueo (*Lock Screen*) — *Para iOS 16 o superior*
1. Bloquea tu iPhone y enciende la pantalla.
2. Mantén presionada la pantalla de bloqueo y pulsa **Personalizar** ➔ **Pantalla de bloqueo**.
3. Toca el área de widgets debajo de la hora.
4. Selecciona el widget de **Atajos** y asigna **Registrar Gasto**.
*Puedes registrar gastos directamente desde la pantalla de bloqueo sin desbloquear el móvil.*

---

### 4. 🔘 Botón Flotante / AssistiveTouch — *Compatible con modelos clásicos (iPhone 6s, 7, 8, SE, etc.)*
1. Ve a **Ajustes** ➔ **Accesibilidad** ➔ **Tocar** ➔ **AssistiveTouch** (actívalo).
2. En "Acciones personalizadas" (o "Menú de nivel superior"):
   - Asigna **Doble toque** o **Pulsación larga** al atajo **Registrar Gasto**.
*Tendrás un botón flotante en cualquier app para registrar gastos en 1 segundo.*

---

### 5. 🎛️ Centro de Control (*Control Center*) — *iOS 18 o Widget en iOS 14-17*
- En iOS 18: Desliza el Centro de Control, mantén presionado para editar, toca **Añadir control** ➔ **Atajos** ➔ **Registrar Gasto**.
- En iOS 14-17: Desliza hacia la izquierda desde la pantalla principal para ir a la vista "Hoy" y añade el Widget de Atajos.

---

### 6. ⚡ Botón de Acción (*Action Button*) — *iPhone 15 Pro, 15 Pro Max y familia iPhone 16*
1. Ve a **Ajustes** ➔ **Botón de acción**.
2. Desliza hasta la opción **Atajo**.
3. Selecciona **Registrar Gasto**.

---

### 7. 🗣️ Por Voz con Siri — *Para el 100% de los iPhones*
Simplemente di en voz alta:
> *"Oye Siri, Registrar Gasto"*
*(Siri te preguntará interactivamente el monto, la categoría y lo registrará en tu Dashboard y Notion).*
