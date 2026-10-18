"""
FastAPI Enterprise OLAP Server for DuckDB E-Commerce Analytics
"""
import os
import time
from typing import Optional, List, Dict, Any
import duckdb
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

DB_PATH = "ecommerce_analytics.duckdb"

app = FastAPI(
    title="ApexAnalytics API",
    description="Enterprise DuckDB Vectorized OLAP Analytics Engine",
    version="2.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# Database Connection Management
# ---------------------------------------------------------
def get_read_connection():
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database file '{DB_PATH}' not found. Please run seed_db.py first."
        )
    return duckdb.connect(database=DB_PATH, read_only=True)

def execute_read(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    conn = get_read_connection()
    try:
        rel = conn.execute(query, params) if params else conn.execute(query)
        if not rel.description:
            return []
        cols = [desc[0] for desc in rel.description]
        rows = rel.fetchall()
        return [dict(zip(cols, row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

def execute_write(query: str, params: tuple = None):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=503, detail="Database file not found.")
    try:
        with duckdb.connect(database=DB_PATH, read_only=False) as conn:
            if params:
                conn.execute(query, params)
            else:
                conn.execute(query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------
class ProductCreate(BaseModel):
    product_id: int = Field(..., gt=0, description="Unique product ID")
    product_name: str = Field(..., min_length=2, description="Product title")
    category_id: int = Field(..., gt=0, description="Valid category reference")
    unit_price: float = Field(..., gt=0, description="Selling unit price")
    cost_price: float = Field(..., gt=0, description="Supplier cost price")
    stock_level: int = Field(..., ge=0, description="Initial stock level")

class SQLExecuteRequest(BaseModel):
    sql: str = Field(..., min_length=5, description="SELECT statement")

# ---------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------

@app.get("/api/kpis")
def get_kpis():
    """Returns top-level executive metrics."""
    query = """
    SELECT 
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS total_revenue,
        ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 2) AS gross_profit,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNT(DISTINCT o.customer_id) AS active_customers,
        ROUND(AVG(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS aov,
        ROUND((SUM(oi.quantity * (oi.unit_price - p.cost_price)) / 
               NULLIF(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 0)) * 100, 1) AS overall_margin_pct
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.status != 'Cancelled';
    """
    rows = execute_read(query)
    return rows[0] if rows else {}

@app.get("/api/charts/velocity")
def get_velocity(window_days: int = 7):
    """Returns time-series revenue timeline with moving average."""
    preceding = max(1, window_days - 1)
    query = f"""
    WITH daily_sales AS (
        SELECT 
            o.order_date,
            COUNT(DISTINCT o.order_id) AS order_count,
            ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS daily_revenue,
            ROUND(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 2) AS daily_profit
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        WHERE o.status != 'Cancelled'
        GROUP BY o.order_date
    )
    SELECT 
        order_date,
        daily_revenue,
        daily_profit,
        order_count,
        ROUND(AVG(daily_revenue) OVER (
            ORDER BY order_date 
            ROWS BETWEEN {preceding} PRECEDING AND CURRENT ROW
        ), 2) AS rolling_avg_rev,
        ROUND(SUM(daily_revenue) OVER (
            ORDER BY order_date 
            ROWS BETWEEN {preceding} PRECEDING AND CURRENT ROW
        ), 2) AS rolling_cumulative_rev,
        ROUND(daily_revenue - LAG(daily_revenue, 1) OVER (ORDER BY order_date), 2) AS daily_velocity_delta
    FROM daily_sales
    ORDER BY order_date;
    """
    return execute_read(query)

@app.get("/api/charts/pareto")
def get_pareto():
    """Returns 80/20 cumulative profit distribution for products."""
    query = """
    WITH product_agg AS (
        SELECT 
            p.product_id,
            p.product_name,
            cat.category_name,
            cat.department,
            p.unit_price,
            p.cost_price,
            ROUND(((p.unit_price - p.cost_price) / p.unit_price) * 100, 1) AS margin_rate_pct,
            COALESCE(SUM(oi.quantity), 0) AS total_units_sold,
            ROUND(COALESCE(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 0), 2) AS gross_revenue,
            ROUND(COALESCE(SUM(oi.quantity * (oi.unit_price - p.cost_price)), 0), 2) AS total_profit
        FROM products p
        JOIN categories cat ON p.category_id = cat.category_id
        LEFT JOIN order_items oi ON p.product_id = oi.product_id
        LEFT JOIN orders o ON oi.order_id = o.order_id AND o.status != 'Cancelled'
        GROUP BY p.product_id, p.product_name, cat.category_name, cat.department, p.unit_price, p.cost_price
    )
    SELECT 
        product_name,
        category_name,
        department,
        unit_price,
        cost_price,
        margin_rate_pct,
        total_units_sold,
        gross_revenue,
        total_profit,
        ROUND(SUM(total_profit) OVER (ORDER BY total_profit DESC ROWS UNBOUNDED PRECEDING), 2) AS cumulative_profit,
        ROUND((SUM(total_profit) OVER (ORDER BY total_profit DESC ROWS UNBOUNDED PRECEDING) / 
               NULLIF(SUM(total_profit) OVER (), 0)) * 100, 2) AS cumulative_profit_pct,
        CASE 
            WHEN (SUM(total_profit) OVER (ORDER BY total_profit DESC ROWS UNBOUNDED PRECEDING) / 
                  NULLIF(SUM(total_profit) OVER (), 0)) <= 0.80 THEN 'Pareto Core (Top 80%)'
            ELSE 'Tail Product'
        END AS pareto_status
    FROM product_agg
    ORDER BY total_profit DESC;
    """
    return execute_read(query)

@app.get("/api/charts/rfm")
def get_rfm():
    """Returns customer RFM metrics and segmentation using QUALIFY clause."""
    query = """
    WITH customer_metrics AS (
        SELECT 
            c.customer_id,
            c.customer_name,
            c.segment,
            c.city,
            c.country,
            MAX(o.order_date) AS last_order_date,
            date_diff('day', MAX(o.order_date), CAST('2025-10-15' AS DATE)) AS recency_days,
            COUNT(DISTINCT o.order_id) AS frequency_orders,
            ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS monetary_value,
            ROUND(AVG(oi.quantity * oi.unit_price * (1 - oi.discount)), 2) AS avg_item_spend,
            NTILE(4) OVER (ORDER BY SUM(oi.quantity * oi.unit_price * (1 - oi.discount)) DESC) AS spend_quartile,
            PERCENT_RANK() OVER (ORDER BY COUNT(DISTINCT o.order_id)) AS loyalty_rank
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.status != 'Cancelled'
        GROUP BY c.customer_id, c.customer_name, c.segment, c.city, c.country
    )
    SELECT 
        customer_id,
        customer_name,
        segment,
        city,
        country,
        recency_days,
        frequency_orders,
        monetary_value,
        avg_item_spend,
        spend_quartile,
        ROUND(loyalty_rank * 100, 1) AS loyalty_percentile,
        ROW_NUMBER() OVER (PARTITION BY segment ORDER BY monetary_value DESC) AS segment_rank,
        CASE 
            WHEN spend_quartile = 1 AND recency_days <= 30 THEN 'Top Tier VIP'
            WHEN spend_quartile = 1 AND recency_days > 30 THEN 'High Value (At Risk)'
            WHEN spend_quartile IN (2, 3) AND recency_days <= 45 THEN 'Engaged Core'
            ELSE 'Lapsed / Low Frequency'
        END AS rfm_tier
    FROM customer_metrics
    QUALIFY ROW_NUMBER() OVER (PARTITION BY segment ORDER BY monetary_value DESC) <= 8
    ORDER BY segment, segment_rank;
    """
    return execute_read(query)

@app.get("/api/charts/funnel")
def get_funnel():
    """Returns multi-stage engagement touchpoints by segment."""
    query = """
    SELECT 
        c.segment,
        COUNT(ci.interaction_id) AS total_events,
        COUNT(CASE WHEN ci.action_type = 'view' THEN 1 END) AS views,
        COUNT(CASE WHEN ci.action_type = 'add_to_cart' THEN 1 END) AS cart_adds,
        COUNT(CASE WHEN ci.action_type = 'purchase' THEN 1 END) AS purchases,
        COUNT(CASE WHEN ci.action_type = 'review' THEN 1 END) AS reviews,
        ROUND(AVG(ci.session_duration_sec), 1) AS avg_duration_sec,
        ROUND((COUNT(CASE WHEN ci.action_type = 'purchase' THEN 1 END)::DOUBLE / 
               NULLIF(COUNT(CASE WHEN ci.action_type = 'view' THEN 1 END), 0)) * 100, 2) AS conversion_rate_pct
    FROM customer_interactions ci
    JOIN customers c ON ci.customer_id = c.customer_id
    GROUP BY c.segment
    ORDER BY total_events DESC;
    """
    return execute_read(query)

@app.get("/api/tables/{table_name}")
def get_table_data(
    table_name: str,
    search: Optional[str] = Query(None, description="Keyword search filter"),
    limit: int = Query(25, ge=1, le=100)
):
    """Dynamic table viewer with safe sanitized search."""
    allowed = ["products", "customers", "orders", "order_items", "categories", "customer_interactions"]
    if table_name not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid table name '{table_name}'.")

    # Get column definitions
    info = execute_read(f"PRAGMA table_info('{table_name}')")
    cols = [r['name'] for r in info]
    varchar_cols = [r['name'] for r in info if any(t in str(r['type']).upper() for t in ['VARCHAR', 'TEXT', 'CHAR'])]

    clean_search = search.strip() if search else ""
    if clean_search and varchar_cols:
        safe_term = clean_search.replace("'", "''")
        where_clauses = [f"{c} ILIKE '%{safe_term}%'" for c in varchar_cols]
        where_sql = " OR ".join(where_clauses)
        data = execute_read(f"SELECT * FROM {table_name} WHERE {where_sql} LIMIT {limit}")
    else:
        data = execute_read(f"SELECT * FROM {table_name} LIMIT {limit}")

    total = execute_read(f"SELECT COUNT(*) AS c FROM {table_name}")[0]['c']
    return {
        "table": table_name,
        "columns": cols,
        "total_rows": total,
        "returned_rows": len(data),
        "data": data
    }

@app.get("/api/categories")
def get_categories():
    """Returns category list for dropdowns."""
    return execute_read("SELECT category_id, category_name, department FROM categories ORDER BY category_id")

@app.post("/api/products")
def create_product(product: ProductCreate):
    """Creates a new product record."""
    if product.cost_price >= product.unit_price:
        raise HTTPException(status_code=400, detail="Cost price must be strictly less than Unit price.")

    # Check category existence
    cat_check = execute_read("SELECT COUNT(*) AS cnt FROM categories WHERE category_id = ?", (product.category_id,))
    if cat_check[0]['cnt'] == 0:
        raise HTTPException(status_code=400, detail=f"Category ID {product.category_id} does not exist.")

    # Insert
    execute_write(
        "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)",
        (product.product_id, product.product_name, product.category_id, product.unit_price, product.cost_price, product.stock_level)
    )
    return {"status": "success", "message": f"Product '{product.product_name}' (ID {product.product_id}) created."}

@app.post("/api/execute-sql")
def run_sql(req: SQLExecuteRequest):
    """Executes a read-only SQL query."""
    sql = req.sql.strip()
    # Guard against destructive queries in the read-only console
    blocked_keywords = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "ALTER", "INSERT", "CREATE"]
    first_token = sql.split()[0].upper() if sql else ""
    if first_token in blocked_keywords:
        raise HTTPException(status_code=403, detail="Only read-only SELECT queries are allowed in this terminal.")

    t0 = time.time()
    data = execute_read(sql)
    elapsed_ms = round((time.time() - t0) * 1000, 2)
    return {
        "execution_time_ms": elapsed_ms,
        "row_count": len(data),
        "data": data
    }

@app.get("/api/architecture")
def get_architecture():
    """Returns DuckDB schema topology and memory settings."""
    tables = ["customers", "categories", "products", "orders", "order_items", "customer_interactions"]
    schema_stats = []
    for t in tables:
        rc = execute_read(f"SELECT COUNT(*) AS c FROM {t}")[0]['c']
        info = execute_read(f"PRAGMA table_info('{t}')")
        schema_stats.append({
            "table_name": t,
            "row_count": rc,
            "column_count": len(info)
        })

    settings = execute_read("SELECT name, value, description FROM duckdb_settings() WHERE name IN ('threads', 'memory_limit', 'access_mode', 'preserve_insertion_order');")
    db_size = round(os.path.getsize(DB_PATH) / 1024, 1) if os.path.exists(DB_PATH) else 0

    return {
        "db_file": DB_PATH,
        "storage_kb": db_size,
        "tables": schema_stats,
        "settings": settings
    }

@app.on_event("startup")
def on_startup():
    """Ensure database exists on boot; auto-seed if absent."""
    if not os.path.exists(DB_PATH):
        try:
            print(f"Database '{DB_PATH}' not found. Initializing schema and seed data...")
            import seed_db
            seed_db.seed_database()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Warning: Automatic database seeding encountered an error: {e}")

# ---------------------------------------------------------
# Static Files & SPA Routing
# ---------------------------------------------------------
if not os.path.exists("static"):
    os.makedirs("static", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "ApexAnalytics API Online", "docs": "/docs"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting ApexAnalytics Server on {host}:{port}...")
    uvicorn.run("server:app", host=host, port=port, reload=False)

