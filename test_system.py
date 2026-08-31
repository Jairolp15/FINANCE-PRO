import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    print("--- 1. Enviando Gastos de Prueba (Webhook Simulando iPhone/Android) ---")
    expenses = [
        {"amount": 25.50, "category": "Alimentación", "description": "Almuerzo Restaurante", "payment_method": "Tarjeta"},
        {"amount": 12.00, "category": "Transporte", "description": "Uber al trabajo", "payment_method": "Tarjeta"},
        {"amount": 45.00, "category": "Ocio", "description": "Entradas de Cine + Popcorn", "payment_method": "Efectivo"},
        {"amount": 85.00, "category": "Servicios", "description": "Pago Factura Luz", "payment_method": "Transferencia"}
    ]
    
    for exp in expenses:
        res = requests.post(f"{BASE_URL}/api/v1/expense", json=exp)
        print(f"Gasto '{exp['description']}': Status {res.status_code} -> {res.json()['status']}")
        
    print("\n--- 2. Obteniendo Métricas del Dashboard ---")
    metrics_res = requests.get(f"{BASE_URL}/api/v1/metrics")
    metrics = metrics_res.json()
    print(json.dumps(metrics, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_flow()
