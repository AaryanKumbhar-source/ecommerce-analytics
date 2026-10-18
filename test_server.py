"""
Pre-Flight Verification for Live FastAPI DuckDB Server
"""
import requests
import duckdb
from server import DB_PATH

BASE_URL = "http://127.0.0.1:8000"

def test_endpoints():
    print(f"--- TESTING LIVE FASTAPI DUCKDB SERVER AT {BASE_URL} ---")

    # 1. Test Static Index & Root
    r_root = requests.get(f"{BASE_URL}/")
    assert r_root.status_code == 200, f"Root returned {r_root.status_code}"
    assert "ApexAnalytics" in r_root.text
    print("[PASS] GET / -> HTTP 200 (Served static/index.html SPA)")

    # 2. Test KPIs
    r_kpis = requests.get(f"{BASE_URL}/api/kpis")
    assert r_kpis.status_code == 200, f"KPIs returned {r_kpis.status_code}"
    data_kpi = r_kpis.json()
    assert "total_revenue" in data_kpi
    assert float(data_kpi["total_revenue"]) > 0
    print(f"[PASS] GET /api/kpis -> HTTP 200 (Revenue: ${float(data_kpi['total_revenue']):,.2f})")

    # 3. Test Velocity Chart
    r_vel = requests.get(f"{BASE_URL}/api/charts/velocity")
    assert r_vel.status_code == 200
    assert len(r_vel.json()) > 0
    print(f"[PASS] GET /api/charts/velocity -> HTTP 200 ({len(r_vel.json())} timeline records)")

    # 4. Test Pareto Chart
    r_par = requests.get(f"{BASE_URL}/api/charts/pareto")
    assert r_par.status_code == 200
    assert len(r_par.json()) > 0
    print(f"[PASS] GET /api/charts/pareto -> HTTP 200 ({len(r_par.json())} products classified)")

    # 5. Test RFM QUALIFY Query
    r_rfm = requests.get(f"{BASE_URL}/api/charts/rfm")
    assert r_rfm.status_code == 200
    assert len(r_rfm.json()) > 0
    print(f"[PASS] GET /api/charts/rfm -> HTTP 200 ({len(r_rfm.json())} segmented customers)")

    # 6. Test Funnel Query
    r_fun = requests.get(f"{BASE_URL}/api/charts/funnel")
    assert r_fun.status_code == 200
    assert len(r_fun.json()) > 0
    print(f"[PASS] GET /api/charts/funnel -> HTTP 200 ({len(r_fun.json())} segments)")

    # 7. Test Table Explorer
    r_tbl = requests.get(f"{BASE_URL}/api/tables/products?limit=10")
    assert r_tbl.status_code == 200
    tbl_data = r_tbl.json()
    assert tbl_data["returned_rows"] <= 10
    print(f"[PASS] GET /api/tables/products -> HTTP 200 (Total rows in table: {tbl_data['total_rows']})")

    # 8. Test SQL Terminal Execution
    r_sql = requests.post(f"{BASE_URL}/api/execute-sql", json={"sql": "SELECT COUNT(*) AS c FROM orders;"})
    assert r_sql.status_code == 200
    assert r_sql.json()["data"][0]["c"] > 0
    print(f"[PASS] POST /api/execute-sql -> HTTP 200 ({r_sql.json()['execution_time_ms']} ms execution)")

    # 9. Test Architecture & Settings
    r_arch = requests.get(f"{BASE_URL}/api/architecture")
    assert r_arch.status_code == 200
    assert len(r_arch.json()["tables"]) == 6
    print(f"[PASS] GET /api/architecture -> HTTP 200 (All 6 tables mapped)")

    # 10. Test Product Mutation (Write Context Manager)
    test_prod = {
        "product_id": 9999,
        "product_name": "FastAPI Verified Ergonomic Keyboard",
        "category_id": 1,
        "unit_price": 249.99,
        "cost_price": 120.00,
        "stock_level": 50
    }
    r_create = requests.post(f"{BASE_URL}/api/products", json=test_prod)
    assert r_create.status_code == 200
    print(f"[PASS] POST /api/products -> HTTP 200 (Product created)")

    # Cleanup test product
    with duckdb.connect(database=DB_PATH, read_only=False) as conn:
        conn.execute("DELETE FROM products WHERE product_id = 9999")
    print(f"[PASS] Cleaned up test product entity without lock retention.")

    print("\n--- ALL FASTAPI LIVE ENDPOINTS VERIFIED & OPERATIONAL ---")

if __name__ == "__main__":
    test_endpoints()
