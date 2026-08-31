"""
Script de Configuración Inicial e Integración con Notion API
Crea la base de datos de "Gastos" y "Presupuestos" en Notion mediante la API oficial.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
PARENT_PAGE_ID = os.getenv("NOTION_PARENT_PAGE_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def create_expenses_database(parent_page_id: str):
    """Crea la base de datos 'Gastos' en Notion con la estructura requerida."""
    url = "https://api.notion.com/v1/databases"
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": "Gastos Personales"}}],
        "properties": {
            "Descripción": {"title": {}},
            "Monto": {"number": {"format": "dollar"}},
            "Categoría": {
                "select": {
                    "options": [
                        {"name": "Alimentación", "color": "green"},
                        {"name": "Transporte", "color": "blue"},
                        {"name": "Ocio", "color": "purple"},
                        {"name": "Servicios", "color": "yellow"},
                        {"name": "Salud", "color": "red"},
                        {"name": "Educación", "color": "orange"},
                        {"name": "Otros", "color": "gray"}
                    ]
                }
            },
            "Método de Pago": {
                "select": {
                    "options": [
                        {"name": "Tarjeta", "color": "blue"},
                        {"name": "Efectivo", "color": "green"},
                        {"name": "Transferencia", "color": "pink"}
                    ]
                }
            },
            "Fecha/Hora": {"date": {}},
            "Mes/Año": {"select": {}}
        }
    }
    
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        db_id = response.json()["id"]
        print(f"Base de Datos 'Gastos' creada con éxito! Database ID: {db_id}")
        return db_id
    else:
        print(f"Error al crear base de datos: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    if not NOTION_API_KEY or NOTION_API_KEY.startswith("secret_your"):
        print("Por favor configura NOTION_API_KEY y NOTION_PARENT_PAGE_ID en tu archivo .env")
    elif not PARENT_PAGE_ID:
        print("Falta el ID de la página padre (NOTION_PARENT_PAGE_ID).")
    else:
        create_expenses_database(PARENT_PAGE_ID)
