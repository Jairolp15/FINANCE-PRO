import sys
import io
import requests
import json
import time

# Forzar salida en UTF-8 para consola Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_full_suite():
    print("==================================================")
    print("EJECUTANDO SUITE DE PRUEBAS FINANCIERO 2.0")
    print("==================================================")
    
    # 1. Test NLP Parser (Texto Libre)
    print("\n--- 1. Test Modulo NLP (Lenguaje Natural) ---")
    nlp_payload = {"text": "Gaste 32.50 euros en cena de pizza con tarjeta", "currency": "EUR"}
    nlp_res = requests.post(f"{BASE_URL}/api/v1/parse-natural-language", json=nlp_payload)
    assert nlp_res.status_code == 200
    parsed = nlp_res.json()["parsed"]
    print(f"Texto: '{nlp_payload['text']}'")
    print(f"-> Parsed: Monto={parsed['amount']}, Categoria={parsed['category']}, Metodo={parsed['payment_method']}")
    
    # 2. Test Multi-Divisa (Guardar gasto en EUR convertido a USD)
    print("\n--- 2. Test Modulo Multi-Divisa y Registro ---")
    exp_res = requests.post(f"{BASE_URL}/api/v1/expense", json=parsed)
    if exp_res.status_code != 200:
        print(f"Error in expense creation: {exp_res.status_code} - {exp_res.text}")
    assert exp_res.status_code == 200
    exp_data = exp_res.json()["data"]
    print(f"-> Gasto guardado: {exp_data['amount']} {exp_data['currency']} -> ${exp_data['amount_base']} USD base")
    
    # 3. Test OCR Receipt Scanner
    print("\n--- 3. Test Modulo OCR / Vision de Tickets ---")
    ocr_res = requests.post(f"{BASE_URL}/api/v1/scan-receipt")
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()["data"]
    print(f"-> OCR Detectado: {ocr_data['merchant']} - Total: ${ocr_data['amount']} ({ocr_data['category']})")
    
    # 4. Test Presupuestos por Categoria y Alertas
    print("\n--- 4. Test Modulo Presupuestos por Categoria ---")
    budgets_res = requests.get(f"{BASE_URL}/api/v1/budgets")
    assert budgets_res.status_code == 200
    budgets = budgets_res.json()
    for b in budgets[:3]:
        print(f"-> {b['category']}: ${b['spent']} / ${b['limit']} ({b['percentage_used']}%) - Estado: {b['status']}")
        
    # 5. Test Gestor de Suscripciones
    print("\n--- 5. Test Modulo Suscripciones Fijas ---")
    subs_res = requests.get(f"{BASE_URL}/api/v1/subscriptions")
    assert subs_res.status_code == 200
    subs = subs_res.json()
    print(f"-> Suscripciones Activas: {subs['active_count']} | Mensual: ${subs['total_monthly_recurring']} | Anual Proyectado: ${subs['total_yearly_projection']}")
    
    # 6. Test Reporte Mensual Ejecutivo & Consejos IA
    print("\n--- 6. Test Reporte Ejecutivo Mensual con IA ---")
    report_res = requests.get(f"{BASE_URL}/api/v1/monthly-report")
    assert report_res.status_code == 200
    report = report_res.json()
    print(f"-> Resumen: Ingresos: ${report['financial_summary']['income']} | Gastos: ${report['financial_summary']['total_spent']} | Ahorro: {report['financial_summary']['savings_rate_percentage']}%")
    print(f"-> Consejo IA Principal: {report['ai_financial_advice'][0]}")

    print("\n==================================================")
    print("TODAS LAS PRUEBAS (MODULOS 1 AL 6) PASARON EXITOSAMENTE")
    print("==================================================")

if __name__ == "__main__":
    test_full_suite()
