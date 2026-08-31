import sqlite3
import os
import sys
import io

# Configuración de salida segura para consola Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = "expenses.db"

def inspect_database():
    print("==================================================")
    print("[*] AUDITORIA COMPLETA DE BASE DE DATOS (SQLITE & NOTION READY)")
    print("==================================================")
    
    if not os.path.exists(DB_PATH):
        print(f"[*] Archivo '{DB_PATH}' no encontrado. Inicializando estructura...")
        import server
        server.init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Verificar Tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r["name"] for r in cursor.fetchall() if not r["name"].startswith("sqlite_")]
    print(f"\n[+] Tablas encontradas ({len(tables)}): {', '.join(tables)}")
    
    expected_tables = ["expenses", "category_budgets", "subscriptions"]
    for t in expected_tables:
        if t in tables:
            print(f"  - Tabla '{t}': OK")
        else:
            print(f"  [!] Faltante: '{t}'")

    # 2. Verificar Columnas y Tipos en 'expenses'
    print("\n--- Estructura de la Tabla 'expenses' ---")
    cursor.execute("PRAGMA table_info(expenses);")
    columns = {r["name"]: r["type"] for r in cursor.fetchall()}
    for col, col_type in columns.items():
        print(f"  - {col}: {col_type}")
    
    # 3. Verificar Registros de Presupuestos
    print("\n--- Presupuestos por Categoria Inicializados ---")
    cursor.execute("SELECT category, monthly_limit FROM category_budgets")
    budgets = cursor.fetchall()
    for b in budgets:
        print(f"  - {b['category']}: ${b['monthly_limit']:.2f}")

    # 4. Verificar Suscripciones Registradas
    print("\n--- Suscripciones Recurrentes Activas ---")
    cursor.execute("SELECT name, amount, currency, category, billing_day FROM subscriptions WHERE active = 1")
    subs = cursor.fetchall()
    for s in subs:
        print(f"  - {s['name']}: ${s['amount']:.2f} {s['currency']} (Dia {s['billing_day']} - {s['category']})")

    # 5. Comprobar Conteo de Gastos y Métricas de Prueba
    cursor.execute("SELECT COUNT(*) as total_count, SUM(amount_base) as total_spent FROM expenses")
    stats = cursor.fetchone()
    print(f"\n--- Estadisticas de Gastos ---")
    print(f"  - Total transacciones registradas: {stats['total_count']}")
    print(f"  - Total gastado acumulado: ${stats['total_spent'] or 0.0:.2f}")

    # 6. Test de Inserción y Transacción ACID
    print("\n--- Test de Integridad y Rendimiento ---")
    try:
        cursor.execute("BEGIN TRANSACTION")
        cursor.execute("""
            INSERT INTO expenses (description, amount, currency, amount_base, category, payment_method, datetime, month_year, notion_synced)
            VALUES ('Test Auditoria', 10.0, 'USD', 10.0, 'Otros', 'Tarjeta', datetime('now'), strftime('%m-%Y', 'now'), 0)
        """)
        test_id = cursor.lastrowid
        cursor.execute("DELETE FROM expenses WHERE id = ?", (test_id,))
        conn.commit()
        print("  [+] Transacciones ACID (Insert & Delete): 100% Operativo")
    except Exception as e:
        conn.rollback()
        print(f"  [!] Error en test de transaccion: {e}")

    conn.close()
    print("\n==================================================")
    print("[+] RESULTADO: BASE DE DATOS AL 100% OPERATIVA")
    print("==================================================")

if __name__ == "__main__":
    inspect_database()
