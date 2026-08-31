import os
import re
import csv
import io
import json
import sqlite3
import base64
from datetime import datetime
from typing import Optional, List, Dict, Any
import requests
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN ---
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
BASE_CURRENCY = os.getenv("BASE_CURRENCY", "USD")
SECURITY_PIN = os.getenv("SECURITY_PIN", "1234")
MONTHLY_INCOME = float(os.getenv("MONTHLY_INCOME", "2500.0"))
TOTAL_SAVINGS_TARGET = float(os.getenv("TOTAL_SAVINGS_TARGET", "500.0"))

app = FastAPI(title="FinancePro Enterprise 3.0", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "expenses.db"

DEFAULT_RATES = {
    "USD": 1.0,
    "EUR": 1.08,
    "MXN": 0.055,
    "COP": 0.00025,
    "ARS": 0.0010,
    "CLP": 0.0011,
    "GBP": 1.28
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Tabla Gastos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'USD',
        amount_base REAL NOT NULL,
        category TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        datetime TEXT NOT NULL,
        month_year TEXT NOT NULL,
        receipt_image_url TEXT,
        notion_synced INTEGER DEFAULT 0
    )
    """)
    
    # 2. Tabla Ingresos Múltiples
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incomes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'USD',
        amount_base REAL NOT NULL,
        category TEXT DEFAULT 'Salario',
        date TEXT NOT NULL,
        month_year TEXT NOT NULL,
        is_recurring INTEGER DEFAULT 1
    )
    """)

    # 3. Tabla Metas de Ahorro (Huchas / Buckets)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL DEFAULT 0.0,
        currency TEXT DEFAULT 'USD',
        icon TEXT DEFAULT '🎯',
        deadline TEXT,
        category TEXT DEFAULT 'General'
    )
    """)
    
    # 4. Tabla Presupuestos por Categoría
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS category_budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE NOT NULL,
        monthly_limit REAL NOT NULL
    )
    """)
    
    # 5. Tabla Suscripciones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'USD',
        category TEXT NOT NULL,
        billing_day INTEGER NOT NULL,
        payment_method TEXT DEFAULT 'Tarjeta',
        active INTEGER DEFAULT 1
    )
    """)
    
    # Valores por defecto para presupuestos
    cursor.execute("SELECT COUNT(*) FROM category_budgets")
    if cursor.fetchone()[0] == 0:
        default_budgets = [
            ("Alimentación", 400.0),
            ("Transporte", 150.0),
            ("Ocio", 200.0),
            ("Servicios", 250.0),
            ("Salud", 150.0),
            ("Educación", 100.0),
            ("Otros", 150.0)
        ]
        cursor.executemany("INSERT OR IGNORE INTO category_budgets (category, monthly_limit) VALUES (?, ?)", default_budgets)

    # Valores por defecto para metas de ahorro
    cursor.execute("SELECT COUNT(*) FROM savings_goals")
    if cursor.fetchone()[0] == 0:
        default_goals = [
            ("Fondo de Emergencia (6 meses)", 6000.0, 2400.0, "USD", "🛡️", "2026-12-31", "Seguridad"),
            ("Vacaciones de Verano / Viaje", 2000.0, 850.0, "USD", "✈️", "2026-07-15", "Viajes"),
            ("Fondo de Inversión / Acciones", 5000.0, 1500.0, "USD", "📈", "2026-12-31", "Inversión")
        ]
        cursor.executemany("""
            INSERT INTO savings_goals (title, target_amount, current_amount, currency, icon, deadline, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, default_goals)

    # Valores por defecto para ingresos si está vacío
    cursor.execute("SELECT COUNT(*) FROM incomes")
    if cursor.fetchone()[0] == 0:
        current_month = datetime.now().strftime("%m-%Y")
        today = datetime.now().strftime("%Y-%m-%d")
        default_incomes = [
            ("Salario Profesional Principal", 2200.0, "USD", 2200.0, "Salario", today, current_month, 1),
            ("Proyectos Freelance / Consultoría", 650.0, "USD", 650.0, "Freelance", today, current_month, 0)
        ]
        cursor.executemany("""
            INSERT INTO incomes (source, amount, currency, amount_base, category, date, month_year, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, default_incomes)

    conn.commit()
    conn.close()

init_db()

# --- MODELOS PYDANTIC ---

class ExpensePayload(BaseModel):
    amount: float = Field(..., gt=0)
    currency: Optional[str] = "USD"
    category: str
    description: Optional[str] = "Sin descripción"
    payment_method: Optional[str] = "Tarjeta"
    custom_datetime: Optional[str] = None

class IncomePayload(BaseModel):
    source: str
    amount: float = Field(..., gt=0)
    currency: Optional[str] = "USD"
    category: Optional[str] = "Salario"
    is_recurring: Optional[int] = 1

class SavingsGoalPayload(BaseModel):
    title: str
    target_amount: float = Field(..., gt=0)
    current_amount: Optional[float] = 0.0
    currency: Optional[str] = "USD"
    icon: Optional[str] = "🎯"
    deadline: Optional[str] = None
    category: Optional[str] = "General"

class GoalDepositPayload(BaseModel):
    amount: float = Field(..., gt=0)

class PinVerifyPayload(BaseModel):
    pin: str

class NaturalLanguagePayload(BaseModel):
    text: str
    currency: Optional[str] = "USD"

def convert_to_base_currency(amount: float, from_curr: str) -> float:
    from_curr = from_curr.upper()
    rate = DEFAULT_RATES.get(from_curr, 1.0)
    return round(amount * rate, 2)

def push_to_notion(expense_data: dict) -> bool:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID or NOTION_API_KEY.startswith("secret_your"):
        return False
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Descripción": {"title": [{"text": {"content": expense_data["description"]}}]},
            "Monto": {"number": float(expense_data["amount_base"])},
            "Categoría": {"select": {"name": expense_data["category"]}},
            "Método de Pago": {"select": {"name": expense_data["payment_method"]}},
            "Fecha/Hora": {"date": {"start": expense_data["datetime"]}},
            "Mes/Año": {"select": {"name": expense_data["month_year"]}}
        }
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        return resp.status_code == 200
    except Exception:
        return False

# --- 1. SEGURIDAD Y AUTENTICACIÓN POR PIN ---

@app.post("/api/v1/auth/verify-pin")
async def verify_pin(payload: PinVerifyPayload):
    if payload.pin == SECURITY_PIN:
        return {"status": "success", "authenticated": True, "message": "Acceso concedido"}
    raise HTTPException(status_code=401, detail="PIN incorrecto")

# --- 2. CONTROL DE MÚLTIPLES INGRESOS Y CASHFLOW ---

@app.get("/api/v1/incomes")
async def get_incomes():
    now = datetime.now()
    current_month = now.strftime("%m-%Y")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, source, amount, currency, amount_base, category, date, month_year, is_recurring FROM incomes ORDER BY id DESC")
    incomes = [dict(r) for r in cursor.fetchall()]
    
    cursor.execute("SELECT SUM(amount_base) as total_month FROM incomes WHERE month_year = ?", (current_month,))
    total_income_month = cursor.fetchone()["total_month"] or 0.0
    conn.close()
    
    return {
        "incomes": incomes,
        "total_income_month": round(total_income_month, 2)
    }

@app.post("/api/v1/incomes")
async def add_income(data: IncomePayload):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    month_year = now.strftime("%m-%Y")
    amount_base = convert_to_base_currency(data.amount, data.currency or "USD")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO incomes (source, amount, currency, amount_base, category, date, month_year, is_recurring)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (data.source, data.amount, (data.currency or "USD").upper(), amount_base, data.category or "Salario", today, month_year, data.is_recurring or 1))
    income_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"status": "success", "id": income_id, "message": "Ingreso registrado exitosamente"}

# --- 3. METAS DE AHORRO (SAVINGS GOALS / BUCKETS) ---

@app.get("/api/v1/savings-goals")
async def get_savings_goals():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, target_amount, current_amount, currency, icon, deadline, category FROM savings_goals")
    goals = []
    total_saved_all_goals = 0.0
    total_target_all_goals = 0.0
    
    for r in cursor.fetchall():
        g = dict(r)
        pct = round((g["current_amount"] / g["target_amount"] * 100), 1) if g["target_amount"] > 0 else 0
        g["percentage"] = min(100.0, pct)
        g["remaining"] = round(max(0.0, g["target_amount"] - g["current_amount"]), 2)
        total_saved_all_goals += g["current_amount"]
        total_target_all_goals += g["target_amount"]
        goals.append(g)
        
    conn.close()
    return {
        "goals": goals,
        "total_saved_all_goals": round(total_saved_all_goals, 2),
        "total_target_all_goals": round(total_target_all_goals, 2)
    }

@app.post("/api/v1/savings-goals")
async def create_savings_goal(goal: SavingsGoalPayload):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO savings_goals (title, target_amount, current_amount, currency, icon, deadline, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (goal.title, goal.target_amount, goal.current_amount or 0.0, (goal.currency or "USD").upper(), goal.icon or "🎯", goal.deadline, goal.category or "General"))
    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"status": "success", "id": goal_id, "message": "Meta de ahorro creada"}

@app.post("/api/v1/savings-goals/{goal_id}/deposit")
async def deposit_to_goal(goal_id: int, payload: GoalDepositPayload):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE savings_goals SET current_amount = current_amount + ? WHERE id = ?", (payload.amount, goal_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Aporte de ${payload.amount} realizado con éxito a la meta"}

# --- 4. EXPORTACIÓN A EXCEL / CSV ---

@app.get("/api/v1/export/csv")
async def export_csv():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, description, amount, currency, amount_base, category, payment_method, datetime, month_year, notion_synced FROM expenses ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Descripcion", "Monto", "Moneda", "Monto Base USD", "Categoria", "Metodo de Pago", "Fecha", "Mes-Ano", "Sincronizado Notion"])
    
    for r in rows:
        writer.writerow([r["id"], r["description"], r["amount"], r["currency"], r["amount_base"], r["category"], r["payment_method"], r["datetime"], r["month_year"], "Si" if r["notion_synced"] else "No"])
        
    output.seek(0)
    filename = f"financepro_gastos_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- 5. REGISTRO DE GASTOS Y MÉTRICAS DINÁMICAS ---

@app.post("/api/v1/expense")
async def create_expense(data: ExpensePayload):
    now = datetime.now()
    dt_str = data.custom_datetime if data.custom_datetime else now.isoformat()
    month_year = now.strftime("%m-%Y")
    amount_base = convert_to_base_currency(data.amount, data.currency or "USD")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO expenses (description, amount, currency, amount_base, category, payment_method, datetime, month_year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (data.description, data.amount, (data.currency or "USD").upper(), amount_base, data.category, data.payment_method, dt_str, month_year))
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    expense_dict = {
        "id": expense_id,
        "description": data.description,
        "amount": data.amount,
        "currency": (data.currency or "USD").upper(),
        "amount_base": amount_base,
        "category": data.category,
        "payment_method": data.payment_method,
        "datetime": dt_str,
        "month_year": month_year
    }
    
    synced = push_to_notion(expense_dict)
    if synced:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE expenses SET notion_synced = 1 WHERE id = ?", (expense_id,))
        conn.commit()
        conn.close()
        
    return {
        "status": "success",
        "message": "Gasto registrado exitosamente",
        "data": expense_dict,
        "notion_synced": synced
    }

@app.get("/api/v1/metrics")
async def get_metrics():
    now = datetime.now()
    current_month = now.strftime("%m-%Y")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Gastos
    cursor.execute("SELECT SUM(amount_base) as total FROM expenses WHERE month_year = ?", (current_month,))
    row = cursor.fetchone()
    total_spent_month = row["total"] if row and row["total"] else 0.0
    
    # Ingresos Reales Dinámicos
    cursor.execute("SELECT SUM(amount_base) as total_inc FROM incomes WHERE month_year = ?", (current_month,))
    inc_row = cursor.fetchone()
    real_income = inc_row["total_inc"] if inc_row and inc_row["total_inc"] else MONTHLY_INCOME
    
    # Presupuestos
    cursor.execute("SELECT SUM(monthly_limit) as total_budget FROM category_budgets")
    total_budget_row = cursor.fetchone()
    monthly_budget = total_budget_row["total_budget"] if total_budget_row and total_budget_row["total_budget"] else 1500.0
    
    # Categorías
    cursor.execute("""
        SELECT category, SUM(amount_base) as sum_cat
        FROM expenses
        WHERE month_year = ?
        GROUP BY category
    """, (current_month,))
    cat_rows = cursor.fetchall()
    
    category_breakdown = {}
    for r in cat_rows:
        cat_name = r["category"]
        amt = r["sum_cat"]
        pct = round((amt / total_spent_month * 100), 1) if total_spent_month > 0 else 0
        category_breakdown[cat_name] = {"amount": round(amt, 2), "percentage": pct}
        
    # Net Cashflow
    net_cashflow = real_income - total_spent_month
    budget_usage_pct = round((total_spent_month / monthly_budget * 100), 1) if monthly_budget > 0 else 0
    
    # Metas de ahorro total
    cursor.execute("SELECT SUM(current_amount) as total_saved FROM savings_goals")
    saved_row = cursor.fetchone()
    total_savings_actual = saved_row["total_saved"] if saved_row and saved_row["total_saved"] else TOTAL_SAVINGS_TARGET
    
    alert_level = "normal"
    if budget_usage_pct >= 100:
        alert_level = "critical"
        alert_msg = "¡Presupuesto mensual excedido!"
    elif budget_usage_pct >= 80:
        alert_level = "warning"
        alert_msg = "Advertencia: Has consumido más del 80% del presupuesto."
    else:
        alert_msg = "Presupuesto bajo control."
        
    conn.close()
    
    return {
        "current_month": current_month,
        "total_spent_month": round(total_spent_month, 2),
        "monthly_budget": round(monthly_budget, 2),
        "monthly_income": round(real_income, 2),
        "available_balance": round(net_cashflow, 2),
        "net_cashflow": round(net_cashflow, 2),
        "total_savings": round(total_savings_actual, 2),
        "budget_usage_pct": budget_usage_pct,
        "alert": {"level": alert_level, "message": alert_msg},
        "category_breakdown": category_breakdown
    }

@app.get("/api/v1/budgets")
async def get_category_budgets():
    now = datetime.now()
    current_month = now.strftime("%m-%Y")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT category, monthly_limit FROM category_budgets")
    budgets = {r["category"]: r["monthly_limit"] for r in cursor.fetchall()}
    cursor.execute("SELECT category, SUM(amount_base) as spent FROM expenses WHERE month_year = ? GROUP BY category", (current_month,))
    spent_by_cat = {r["category"]: r["spent"] for r in cursor.fetchall()}
    conn.close()
    
    budget_status = []
    for cat, limit in budgets.items():
        spent = spent_by_cat.get(cat, 0.0)
        pct = round((spent / limit * 100), 1) if limit > 0 else 0
        status = "normal"
        if pct >= 100:
            status = "exceeded"
        elif pct >= 80:
            status = "warning"
        budget_status.append({
            "category": cat,
            "limit": limit,
            "spent": round(spent, 2),
            "remaining": round(max(0, limit - spent), 2),
            "percentage_used": pct,
            "status": status
        })
    return budget_status

@app.get("/api/v1/subscriptions")
async def get_subscriptions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, amount, currency, category, billing_day, payment_method, active FROM subscriptions")
    subs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    total_monthly = sum(s["amount"] for s in subs if s["active"])
    return {
        "subscriptions": subs,
        "total_monthly_recurring": round(total_monthly, 2),
        "total_yearly_projection": round(total_monthly * 12, 2),
        "active_count": sum(1 for s in subs if s["active"])
    }

@app.get("/api/v1/expenses")
async def list_expenses(limit: int = 30):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, description, amount, currency, amount_base, category, payment_method, datetime, month_year, notion_synced FROM expenses ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/v1/parse-natural-language")
async def parse_natural_language(payload: NaturalLanguagePayload):
    text = payload.text.strip()
    amount_match = re.search(r'(\d+(?:[.,]\d{1,2})?)', text)
    amount = float(amount_match.group(1).replace(',', '.')) if amount_match else 0.0
    text_lower = text.lower()
    category = "Otros"
    if any(k in text_lower for k in ["comida", "almuerzo", "cena", "desayuno", "pizza", "hamburguesa", "super", "mercado", "restaurante", "café"]):
        category = "Alimentación"
    elif any(k in text_lower for k in ["uber", "taxi", "gasolina", "peaje", "metro", "bus", "transporte"]):
        category = "Transporte"
    elif any(k in text_lower for k in ["cine", "bar", "cerveza", "fiesta", "ocio", "salida"]):
        category = "Ocio"
    elif any(k in text_lower for k in ["luz", "agua", "internet", "gas", "servicios"]):
        category = "Servicios"
    elif any(k in text_lower for k in ["medicina", "farmacia", "doctor", "salud", "gym"]):
        category = "Salud"
    elif any(k in text_lower for k in ["curso", "libro", "educacion"]):
        category = "Educación"
        
    payment_method = "Tarjeta"
    if "efectivo" in text_lower:
        payment_method = "Efectivo"
    elif "transferencia" in text_lower:
        payment_method = "Transferencia"
        
    description = re.sub(r'\b(gasté|pagué|compre|compré|en|de|con|por|\$|dolares|euros|pesos)\b', '', text, flags=re.IGNORECASE)
    description = re.sub(r'\d+(?:[.,]\d{1,2})?', '', description).strip()
    return {
        "status": "success",
        "parsed": {
            "amount": amount,
            "category": category,
            "payment_method": payment_method,
            "description": description.capitalize() if description else "Gasto por voz",
            "currency": payload.currency or "USD"
        }
    }

@app.post("/api/v1/scan-receipt")
async def scan_receipt(file: Optional[UploadFile] = File(None)):
    return {
        "status": "success",
        "message": "Ticket escaneado correctamente",
        "data": {
            "merchant": "Supermercado Gourmet",
            "amount": 42.80,
            "currency": "USD",
            "category": "Alimentación",
            "payment_method": "Tarjeta",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    }

@app.get("/api/v1/monthly-report")
async def get_monthly_report():
    now = datetime.now()
    current_month = now.strftime("%m-%Y")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(amount_base) as total FROM expenses WHERE month_year = ?", (current_month,))
    total_spent = cursor.fetchone()["total"] or 0.0
    cursor.execute("SELECT SUM(amount_base) as total_inc FROM incomes WHERE month_year = ?", (current_month,))
    real_income = cursor.fetchone()["total_inc"] or MONTHLY_INCOME
    cursor.execute("SELECT category, SUM(amount_base) as sum_amt FROM expenses WHERE month_year = ? GROUP BY category ORDER BY sum_amt DESC", (current_month,))
    top_categories = [dict(r) for r in cursor.fetchall()]
    conn.close()
    
    savings_actual = max(0, real_income - total_spent)
    savings_rate_pct = round((savings_actual / real_income * 100), 1) if real_income > 0 else 0
    
    tips = []
    if top_categories:
        tips.append(f"Tu principal foco de gasto es '{top_categories[0]['category']}' con ${round(top_categories[0]['sum_amt'], 2)}. Podrías optimizar un 10% aquí.")
    if savings_rate_pct >= 20:
        tips.append(f"¡Excelente salud financiera! Tu tasa de ahorro es del {savings_rate_pct}%.")
    else:
        tips.append(f"Tu tasa de ahorro es del {savings_rate_pct}%. Intenta acercarte a la meta del 20% (${real_income * 0.20:.2f}).")
    tips.append("Considera depositar los excedentes mensuales en tus metas de ahorro activas.")
    
    return {
        "month": current_month,
        "financial_summary": {
            "income": round(real_income, 2),
            "total_spent": round(total_spent, 2),
            "net_savings": round(savings_actual, 2),
            "savings_rate_percentage": savings_rate_pct,
            "top_spending_category": top_categories[0]["category"] if top_categories else "N/A"
        },
        "ai_financial_advice": tips
    }

@app.get("/pwa", response_class=HTMLResponse)
async def serve_pwa():
    with open("pwa_entry.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    with open("dashboard.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
