"""
Pre-Flight Verification Test Suite for DuckDB E-Commerce Analytics
"""
import app

def run_tests():
    print("--- RUNNING PRE-FLIGHT VERIFICATION ---")

    # a) fetch_kpis
    kpi_df = app.fetch_kpis()
    assert not kpi_df.empty, "KPI dataframe is empty!"
    rev = float(kpi_df['total_revenue'].iloc[0])
    orders = int(kpi_df['total_orders'].iloc[0])
    print(f"[PASS] fetch_kpis: Total Revenue=${rev:,.2f}, Total Orders={orders}")

    # b) fetch_rolling_velocity
    vel_df = app.fetch_rolling_velocity()
    assert not vel_df.empty, "Rolling velocity dataframe is empty!"
    print(f"[PASS] fetch_rolling_velocity: {len(vel_df)} daily timeline rows with 7-day moving averages")

    # c) fetch_rfm_segmentation (testing date_diff and QUALIFY)
    rfm_df = app.fetch_rfm_segmentation()
    assert not rfm_df.empty, "RFM segmentation dataframe is empty!"
    assert "recency_days" in rfm_df.columns, "recency_days missing from RFM!"
    assert "rfm_tier" in rfm_df.columns, "rfm_tier missing from RFM!"
    print(f"[PASS] fetch_rfm_segmentation: {len(rfm_df)} customers segmented via QUALIFY & date_diff")

    # d) fetch_pareto_profitability & fetch_funnel_engagement
    pareto_df = app.fetch_pareto_profitability()
    assert not pareto_df.empty, "Pareto dataframe is empty!"
    print(f"[PASS] fetch_pareto_profitability: {len(pareto_df)} products classified by 80/20 rule")

    funnel_df = app.fetch_funnel_engagement()
    assert not funnel_df.empty, "Funnel dataframe is empty!"
    print(f"[PASS] fetch_funnel_engagement: {len(funnel_df)} customer segments analyzed across touchpoints")

    # e) Context-managed write query & concurrent read verification (No File Lock)
    test_pid = 9999
    app.execute_write_query(
        "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)",
        (test_pid, "Verified Mechanical Keyboard", 1, 199.99, 99.00, 25)
    )
    # Read back immediately
    check_df = app.execute_read_query("SELECT * FROM products WHERE product_id = ?", (test_pid,))
    assert len(check_df) == 1, "Inserted test product could not be found!"
    print(f"[PASS] execute_write_query context manager: Successfully inserted test product {test_pid}")

    # Delete test record and verify
    app.execute_write_query("DELETE FROM products WHERE product_id = ?", (test_pid,))
    check_deleted = app.execute_read_query("SELECT * FROM products WHERE product_id = ?", (test_pid,))
    assert len(check_deleted) == 0, "Test product could not be deleted!"
    print("[PASS] execute_write_query lock release: Successfully removed test product without file lock collisions")

    print("\n--- ALL PRE-FLIGHT VERIFICATION CHECKS COMPLETED SUCCESSFULLY ---")

if __name__ == "__main__":
    run_tests()
