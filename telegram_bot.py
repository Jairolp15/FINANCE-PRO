"""
Bot de Telegram para Registro Rápido de Gastos mediante Voz y Texto Libre
Permite registrar gastos escribiendo 'Gasté 20 en comida' o enviando notas de voz.
Comandos: /cierre, /balance, /resumen, /ingreso <monto> [descripción]
"""

import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_SERVER_URL = os.getenv("API_SERVER_URL", "http://127.0.0.1:8000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─────────────────────────────────────────────────────────────────
# UTILIDADES DE TELEGRAM
# ─────────────────────────────────────────────────────────────────

def send_telegram_message(chat_id, text):
    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM] Token no configurado.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

def get_file_path(file_id):
    """Obtiene la ruta del archivo en los servidores de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    try:
        resp = requests.get(url, timeout=5).json()
        if resp.get("ok"):
            return resp["result"]["file_path"]
    except Exception:
        pass
    return None

def download_telegram_file(file_path):
    """Descarga un archivo de Telegram y retorna sus bytes."""
    url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.content
    except Exception as e:
        print(f"Error al descargar archivo: {e}")
    return None

# ─────────────────────────────────────────────────────────────────
# TRANSCRIPCIÓN DE NOTAS DE VOZ CON GEMINI
# ─────────────────────────────────────────────────────────────────

def transcribe_voice_gemini(audio_bytes: bytes, mime_type: str = "audio/ogg") -> str:
    """Transcribe audio usando Gemini Flash si hay API key configurada."""
    if not GEMINI_API_KEY:
        return ""
    try:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{
                "parts": [
                    {"inline_data": {"mime_type": mime_type, "data": audio_b64}},
                    {"text": (
                        "Transcribe exactamente lo que dice este audio en español. "
                        "Devuelve solo el texto transcrito, sin comentarios adicionales."
                    )}
                ]
            }]
        }
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
    except Exception as e:
        print(f"Error en transcripción Gemini: {e}")
    return ""

# ─────────────────────────────────────────────────────────────────
# PROCESADORES DE MENSAJES
# ─────────────────────────────────────────────────────────────────

def handle_voice_message(chat_id, file_id, mime_type="audio/ogg"):
    """Descarga, transcribe y procesa una nota de voz de Telegram."""
    send_telegram_message(chat_id, "🎙️ *Procesando tu nota de voz...*")

    file_path = get_file_path(file_id)
    if not file_path:
        send_telegram_message(chat_id, "❌ No pude acceder al archivo de audio.")
        return

    audio_bytes = download_telegram_file(file_path)
    if not audio_bytes:
        send_telegram_message(chat_id, "❌ Error al descargar el audio.")
        return

    transcript = transcribe_voice_gemini(audio_bytes, mime_type)

    if not transcript:
        if not GEMINI_API_KEY:
            send_telegram_message(
                chat_id,
                "⚠️ *Transcripción de voz no disponible*\n\n"
                "Para usar notas de voz, configura `GEMINI_API_KEY` en tu `.env`.\n"
                "Mientras tanto, escríbeme en texto:\n"
                "• *'Gasté 30 en comida'*\n"
                "• *'Cobré 100 de un cliente'*"
            )
        else:
            send_telegram_message(chat_id, "❌ No pude transcribir el audio. Intenta de nuevo más claro.")
        return

    send_telegram_message(chat_id, f"🗣️ *Escuché:* _{transcript}_")
    process_text_message(chat_id, transcript)


def handle_quick_income_command(chat_id, args_text):
    """
    Maneja: /ingreso <monto> [descripción]
    Ejemplo: /ingreso 150 Venta de producto
    """
    parts = args_text.strip().split(None, 1)
    if not parts:
        send_telegram_message(
            chat_id,
            "ℹ️ *Uso:* `/ingreso <monto> [descripción]`\n"
            "Ejemplo: `/ingreso 150 Venta de productos`"
        )
        return

    try:
        amount = float(parts[0].replace(",", "."))
    except ValueError:
        send_telegram_message(chat_id, "⚠️ El monto debe ser un número. Ej: `/ingreso 75.50 Servicio`")
        return

    description = parts[1] if len(parts) > 1 else "Ingreso registrado por Telegram"

    try:
        res = requests.post(
            f"{API_SERVER_URL}/api/v1/income",
            json={
                "amount": amount,
                "currency": "USD",
                "category": "Ventas / Cobros",
                "description": description,
                "payment_method": "Efectivo"
            },
            timeout=5
        )
        if res.status_code == 200:
            send_telegram_message(
                chat_id,
                f"✅ *Ingreso Registrado* 💰\n\n"
                f"💵 *Monto:* ${amount:.2f} USD\n"
                f"📝 *Descripción:* {description}\n"
                f"🏷️ *Categoría:* Ventas / Cobros"
            )
        else:
            send_telegram_message(chat_id, "❌ Error al registrar el ingreso.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error de conexión: {e}")


def handle_photo_message(chat_id, file_id):
    """Descarga una foto de ticket de Telegram y la envía al OCR de Gemini."""
    send_telegram_message(chat_id, "📸 *Analizando foto del ticket con IA...*")

    file_path = get_file_path(file_id)
    if not file_path:
        send_telegram_message(chat_id, "❌ No pude acceder a la imagen.")
        return

    photo_bytes = download_telegram_file(file_path)
    if not photo_bytes:
        send_telegram_message(chat_id, "❌ Error al descargar la foto.")
        return

    try:
        # Enviar al endpoint de scan-receipt en Base64
        photo_b64 = base64.b64encode(photo_bytes).decode("utf-8")
        res = requests.post(
            f"{API_SERVER_URL}/api/v1/scan-receipt",
            data={"base64_image": photo_b64},
            timeout=30
        )
        if res.status_code == 200:
            data = res.json()["data"]
            amount = data.get("amount", 0.0)
            merchant = data.get("merchant", "Ticket")
            category = data.get("category", "Otros")
            payment_method = data.get("payment_method", "Tarjeta")

            # Registrar automáticamente el gasto
            exp_res = requests.post(
                f"{API_SERVER_URL}/api/v1/expense",
                json={
                    "amount": amount,
                    "currency": data.get("currency", "USD"),
                    "category": category,
                    "description": f"Ticket: {merchant}",
                    "payment_method": payment_method
                },
                timeout=5
            )

            if exp_res.status_code == 200:
                msg = (
                    f"🧾 *Ticket Escaneado y Registrado* ✅\n\n"
                    f"🏢 *Comercio:* {merchant}\n"
                    f"💵 *Monto:* ${amount:.2f} {data.get('currency', 'USD')}\n"
                    f"🏷️ *Categoría:* {category}\n"
                    f"💳 *Método:* {payment_method}\n"
                    f"📅 *Fecha:* {data.get('date', 'Hoy')}\n\n"
                    f"🔗 Guardado automáticamente en tu base de datos."
                )
                send_telegram_message(chat_id, msg)
            else:
                send_telegram_message(chat_id, f"⚠️ Detecté el ticket (${amount} en {merchant}), pero hubo un error al guardarlo.")
        else:
            send_telegram_message(chat_id, "❌ No se pudo extraer la información del ticket.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al procesar imagen: {e}")


def handle_export_command(chat_id):
    """Descarga el reporte CSV y lo envía como documento al chat de Telegram."""
    send_telegram_message(chat_id, "📊 *Generando reporte financiero en Excel / CSV...*")
    try:
        res = requests.get(f"{API_SERVER_URL}/api/v1/export/csv", timeout=10)
        if res.status_code == 200:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            files = {"document": ("reporte_financiero.csv", res.content, "text/csv")}
            data = {"chat_id": chat_id, "caption": "📈 Aquí tienes tu reporte completo en formato compatible con Excel."}
            requests.post(url, data=data, files=files, timeout=20)
        else:
            send_telegram_message(chat_id, "❌ Error al generar reporte.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error de conexión al exportar: {e}")


def process_text_message(chat_id, text):
    """Llama al endpoint NLP del servidor para interpretar el mensaje o ejecutar comandos."""
    text_clean = text.strip()

    # ── Comandos de Cierre / Resumen Diario ──
    if text_clean.lower() in ["/cierre", "/balance", "/resumen", "cierre", "balance"]:
        try:
            res = requests.get(f"{API_SERVER_URL}/api/v1/daily-summary", timeout=5).json()
            status_icon = "🟢" if res["net_profit_today"] >= 0 else "🔴"
            status_text = "Ganancia" if res["net_profit_today"] >= 0 else "Déficit"
            b_name = res.get("business_name", "Resumen")
            msg = (
                f"🏪 *{b_name}*\n"
                f"📅 *Cierre Diario ({res['date']})*\n\n"
                f"💰 *Ingresos / Ventas:* +${res['incomes_today']:.2f}\n"
                f"💸 *Gastos:* -${res['expenses_today']:.2f}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📊 *Balance Neto:* *${res['net_profit_today']:.2f}* "
                f"({status_icon} {status_text})\n\n"
                f"🔢 *Movimientos hoy:* {res['transactions_count']}"
            )
            send_telegram_message(chat_id, msg)
            return
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Error al consultar cierre: {e}")
            return

    # ── Comando /exportar ──
    if text_clean.lower() in ["/exportar", "/reporte", "/excel", "/csv"]:
        handle_export_command(chat_id)
        return

    # ── Comando /ingreso rápido ──
    if text_clean.lower().startswith("/ingreso"):
        remainder = text_clean[len("/ingreso"):].strip()
        handle_quick_income_command(chat_id, remainder)
        return

    # ── Procesamiento NLP general (texto libre) ──
    try:
        nlp_res = requests.post(
            f"{API_SERVER_URL}/api/v1/parse-natural-language",
            json={"text": text_clean},
            timeout=5
        )
        if nlp_res.status_code == 200:
            parsed_data = nlp_res.json()["parsed"]

            if parsed_data["amount"] <= 0:
                send_telegram_message(
                    chat_id,
                    "⚠️ No pude detectar el monto. Ejemplos:\n"
                    "• *'Gasté 25 en taxi con tarjeta'*\n"
                    "• *'Cobré 120 de una venta efectivo'*\n"
                    "• */ingreso 80 Servicio prestado*\n"
                    "• */cierre* o */exportar*"
                )
                return

            is_income = parsed_data.get("type") == "income"
            endpoint = f"{API_SERVER_URL}/api/v1/income" if is_income else f"{API_SERVER_URL}/api/v1/expense"

            res = requests.post(endpoint, json=parsed_data, timeout=5)
            if res.status_code == 200:
                emoji = "💰" if is_income else "💸"
                title = "Venta / Ingreso Registrado" if is_income else "Gasto Registrado"
                msg = (
                    f"✅ *{title}* {emoji}\n\n"
                    f"💵 *Monto:* ${parsed_data['amount']:.2f} {parsed_data['currency']}\n"
                    f"🏷️ *Categoría:* {parsed_data['category']}\n"
                    f"💳 *Método:* {parsed_data['payment_method']}\n"
                    f"📝 *Detalle:* {parsed_data['description']}\n\n"
                    f"🔗 Sincronizado en tiempo real con Dashboard y Notion."
                )
                send_telegram_message(chat_id, msg)
            else:
                send_telegram_message(chat_id, "❌ Error al guardar en base de datos.")
    except Exception as e:
        send_telegram_message(chat_id, f"❌ Error al conectar con el servidor: {e}")


# ─────────────────────────────────────────────────────────────────
# BUCLE DE POLLING
# ─────────────────────────────────────────────────────────────────

def start_polling():
    """Bucle de sondeo (polling) para recibir mensajes de Telegram."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN.startswith("your_"):
        print("💡 Para activar el bot de Telegram, agrega TELEGRAM_BOT_TOKEN en tu archivo .env")
        print("Obtén tu token gratis en Telegram hablando con @BotFather.")
        return

    gemini_status = "✅ Voz y OCR ACTIVOS (Gemini)" if GEMINI_API_KEY else "⚠️ Solo texto (sin GEMINI_API_KEY)"
    print(f"🤖 Bot de Telegram iniciado — {gemini_status}")

    last_update_id = 0
    while True:
        try:
            url = (
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
                f"/getUpdates?offset={last_update_id + 1}&timeout=30"
            )
            resp = requests.get(url, timeout=35).json()
            if resp.get("ok"):
                for result in resp.get("result", []):
                    last_update_id = result["update_id"]
                    msg = result.get("message", {})
                    chat_id = msg.get("chat", {}).get("id")
                    text = msg.get("text", "")
                    voice = msg.get("voice")
                    audio = msg.get("audio")
                    photo = msg.get("photo")

                    if not chat_id:
                        continue

                    # ── Bienvenida ──
                    if text and text.startswith("/start"):
                        send_telegram_message(
                            chat_id,
                            "👋 ¡Hola! Soy tu asistente financiero y POS personal para tu negocio.\n\n"
                            "Escríbeme frases libres o usa comandos:\n"
                            "• *Gasté 18 en insumos con tarjeta*\n"
                            "• *Cobré 45 por un corte y barba efectivo*\n"
                            "• */ingreso 200 Venta de producto*\n"
                            "• */cierre* — Ver balance neto de hoy\n"
                            "• */exportar* — Descargar reporte para Excel\n\n"
                            "📸 *Foto de ticket:* Envíame una foto de factura o ticket para auto-registrarlo.\n"
                            "🎙️ *Nota de voz:* Envíame un audio diciendo lo que gastaste o cobraste."
                        )

                    # ── Foto de Recibo / Ticket ──
                    elif photo:
                        # Tomar la imagen con mayor resolución (última en la lista)
                        best_photo = photo[-1]
                        handle_photo_message(chat_id, best_photo["file_id"])

                    # ── Nota de Voz ──
                    elif voice:
                        handle_voice_message(chat_id, voice["file_id"], mime_type="audio/ogg")

                    # ── Archivo de Audio ──
                    elif audio:
                        mime = audio.get("mime_type", "audio/mpeg")
                        handle_voice_message(chat_id, audio["file_id"], mime_type=mime)

                    # ── Texto libre ──
                    elif text:
                        process_text_message(chat_id, text)

        except Exception as e:
            print(f"Error en polling: {e}")


if __name__ == "__main__":
    start_polling()

