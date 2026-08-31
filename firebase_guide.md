# 🚀 Guía de Despliegue en Firebase & Google Cloud

Hemos dejado **todo preconfigurado** en tu proyecto (`firebase.json`, carpeta `public/`, `Dockerfile` y `Procfile`) para que puedas subir tu sistema a la infraestructura de Google Firebase en 2 sencillos pasos.

---

## 🌐 1. Despliegue del Frontend y PWA en Firebase Hosting

Firebase Hosting distribuye tu Dashboard y la PWA móvil en la red CDN mundial de Google con HTTPS y carga instantánea.

### Paso 1: Iniciar Sesión en Firebase
Abre tu consola de comandos en esta carpeta y ejecuta:
```bash
firebase login
```
*(Se abrirá una ventana en tu navegador para que selecciones tu cuenta de Google).*

### Paso 2: Asociar o Crear tu Proyecto en Firebase
Si es la primera vez:
```bash
firebase init hosting
```
- Selecciona: *"Use an existing project"* (o *"Create a new project"*).
- Directorio público: `public` (ya está configurado).
- Single-page app: `Yes`.

### Paso 3: Desplegar
```bash
firebase deploy
```
*¡Listo! Firebase te dará una URL oficial como `https://tu-proyecto.web.app`.*

---

## ⚡ 2. Despliegue del Backend Python (FastAPI)

Dado que el backend procesa los webhooks de tu iPhone, la base de datos y la sincronización con Notion API:

### Opción A: Google Cloud Run (100% Ecosistema Google / Firebase)
Ejecuta con el CLI de Google Cloud:
```bash
gcloud run deploy financepro-backend --source .
```

### Opción B: Railway / Render (Gratis y Automático en 60 segundos)
1. Entra a [railway.app](https://railway.app) o [render.com](https://render.com).
2. Haz clic en **"New Project"** ➔ **"Deploy from GitHub repo"**.
3. Selecciona tu repositorio: `https://github.com/Jairolp15/FINANCE-PRO.git`.
4. El servidor leerá el archivo `Procfile` y estará activo las 24 horas del día.
