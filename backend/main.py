import os
import time
from contextlib import asynccontextmanager
from typing import List
import duckdb
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_FILE = "ecommerce.duckdb"

def fetch_as_dicts(con, query: str, params: list = None):
    """Executes SQL and maps columns directly to dicts without requiring pandas."""
    rel = con.execute(query, params) if params else con.execute(query)
    columns = [desc[0] for desc in rel.description] if rel.description else []
    return [dict(zip(columns, row)) for row in rel.fetchall()]

def init_db():
    """Initializes tables and seeds 50,000+ realistic e-commerce records in DuckDB."""
    con = duckdb.connect(DB_FILE)
    
    table_check = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'orders'").fetchone()[0]
    if table_check > 0:
        count = con.execute("SELECT count(*) FROM orders").fetchone()[0]
        if count >= 10000:
            print(f">>> DuckDB database ready with {count:,} orders.")
            con.close()
            return

    print(">>> Initializing DuckDB schema & generating 50,000+ enterprise records...")

    con.execute("""
    -- 1. CUSTOMERS
    CREATE OR REPLACE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        customer_name VARCHAR,
        email VARCHAR,
        tier VARCHAR,
        loyalty_points INTEGER,
        subscription_status VARCHAR,
        city VARCHAR,
        country VARCHAR
    );

    -- 2. VENDORS
    CREATE OR REPLACE TABLE vendors (
        vendor_id VARCHAR PRIMARY KEY,
        vendor_name VARCHAR,
        category VARCHAR,
        rating DOUBLE
    );

    -- 3. PRODUCTS
    CREATE OR REPLACE TABLE products (
        product_id VARCHAR PRIMARY KEY,
        product_name VARCHAR,
        vendor_id VARCHAR,
        category VARCHAR,
        price DOUBLE,
        cost_price DOUBLE
    );

    -- 4. WAREHOUSES
    CREATE OR REPLACE TABLE warehouses (
        warehouse_id VARCHAR PRIMARY KEY,
        warehouse_name VARCHAR,
        city VARCHAR,
        state VARCHAR,
        capacity INTEGER
    );

    -- 5. INVENTORY
    CREATE OR REPLACE TABLE inventory (
        product_id VARCHAR,
        warehouse_id VARCHAR,
        stock_quantity INTEGER,
        reorder_level INTEGER,
        PRIMARY KEY (product_id, warehouse_id)
    );

    -- 6. LOGISTICS PARTNERS
    CREATE OR REPLACE TABLE logistics_partners (
        partner_id VARCHAR PRIMARY KEY,
        partner_name VARCHAR,
        tier VARCHAR,
        avg_delivery_days INTEGER
    );

    -- 7. ORDERS & ITEMS
    CREATE OR REPLACE TABLE orders (
        order_id BIGINT PRIMARY KEY,
        customer_id INTEGER,
        partner_id VARCHAR,
        order_date DATE,
        order_status VARCHAR,
        payment_method VARCHAR,
        shipping_fee DOUBLE,
        order_amount DOUBLE
    );

    CREATE OR REPLACE TABLE order_items (
        order_item_id BIGINT PRIMARY KEY,
        order_id BIGINT,
        product_id VARCHAR,
        quantity INTEGER,
        unit_price DOUBLE,
        discount DOUBLE
    );
    """)

    # Static Master Entities
    con.execute("""
    INSERT INTO vendors VALUES
        ('V01', 'TechGlobal Logistics', 'Electronics', 4.8),
        ('V02', 'Acoustic Labs Inc', 'Audio', 4.6),
        ('V03', 'Apex Wearables Corp', 'Wearables', 4.9),
        ('V04', 'BrewCraft Appliances', 'Home Appliances', 4.5),
        ('V05', 'Nova Visual Displays', 'Displays & Computing', 4.7);

    INSERT INTO products VALUES
        ('P01', 'Titan Ultra Pro 16 Laptop', 'V01', 'Electronics', 85000.00, 68000.00),
        ('P02', 'SonicBlast ANC Headphones', 'V02', 'Audio', 6500.00, 4200.00),
        ('P03', 'Vanguard Pulse Smartwatch', 'V03', 'Wearables', 14500.00, 10500.00),
        ('P04', 'Barista Deluxe Espresso Hub', 'V04', 'Home Appliances', 8500.00, 5900.00),
        ('P05', 'Infinity Vision 4K 144Hz Monitor', 'V05', 'Displays & Computing', 28000.00, 21000.00),
        ('P06', 'ErgoGlide Mechanical Keyboard', 'V01', 'Electronics', 4500.00, 2900.00),
        ('P07', 'Precision Optic Mouse', 'V01', 'Electronics', 2200.00, 1400.00),
        ('P08', 'AeroBass Portable Speaker', 'V02', 'Audio', 3800.00, 2400.00);

    INSERT INTO warehouses VALUES
        ('W01', 'Northeast Fulfillment Center', 'New York', 'NY', 150000),
        ('W02', 'Southern Distribution Hub', 'Dallas', 'TX', 200000),
        ('W03', 'Midwest Gateway Logistics', 'Chicago', 'IL', 120000),
        ('W04', 'Pacific Northwest Terminal', 'Seattle', 'WA', 180000);

    INSERT INTO logistics_partners VALUES
        ('LP01', 'PrimeAir Express', 'Overnight Priority', 1),
        ('LP02', 'TransContinental Freight', 'Standard Ground', 4),
        ('LP03', 'MetroSpeed Cargo', 'Expedited Two-Day', 2);
    """)

    # 1,500 Customers
    con.execute("""
    INSERT INTO customers
    SELECT 
        1000 + i AS customer_id,
        'Enterprise Client ' || (1000 + i) AS customer_name,
        'client_' || (1000 + i) || '@enterprise-corp.com' AS email,
        CASE (i % 4)
            WHEN 0 THEN 'Platinum'
            WHEN 1 THEN 'Gold'
            WHEN 2 THEN 'Silver'
            ELSE 'Bronze'
        END AS tier,
        CAST((i * 17) % 3500 AS INTEGER) AS loyalty_points,
        CASE WHEN (i % 3 == 0) THEN 'Active' ELSE 'Inactive' END AS subscription_status,
        CASE (i % 5)
            WHEN 0 THEN 'New York'
            WHEN 1 THEN 'San Francisco'
            WHEN 2 THEN 'Austin'
            WHEN 3 THEN 'Chicago'
            ELSE 'Seattle'
        END AS city,
        'USA' AS country
    FROM range(1, 1501) t(i);
    """)

    # Inventory distribution
    con.execute("""
    INSERT INTO inventory
    SELECT 
        p.product_id,
        w.warehouse_id,
        CAST(80 + (random() * 850) AS INTEGER) AS stock_quantity,
        50 AS reorder_level
    FROM products p CROSS JOIN warehouses w;
    """)

    # 50,000 Orders
    con.execute("""
    INSERT INTO orders
    SELECT
        500000 + i AS order_id,
        1000 + CAST(1 + (random() * 1499) AS INTEGER) AS customer_id,
        CASE (i % 3)
            WHEN 0 THEN 'LP01'
            WHEN 1 THEN 'LP02'
            ELSE 'LP03'
        END AS partner_id,
        DATE '2025-01-01' + CAST((random() * 450) AS INTEGER) AS order_date,
        CASE (i % 20)
            WHEN 0 THEN 'Returned'
            WHEN 1 THEN 'Cancelled'
            WHEN 2 THEN 'Pending'
            ELSE 'Completed'
        END AS order_status,
        CASE (i % 4)
            WHEN 0 THEN 'Credit Card'
            WHEN 1 THEN 'Corporate Net30'
            WHEN 2 THEN 'ACH Transfer'
            ELSE 'UPI'
        END AS payment_method,
        CASE WHEN (i % 4 == 0) THEN 0.0 ELSE 250.0 END AS shipping_fee,
        0.0 AS order_amount
    FROM range(1, 50001) t(i);
    """)

    # 65,000 Order Items
    con.execute("""
    INSERT INTO order_items
    SELECT
        1000000 + i AS order_item_id,
        500000 + (i % 50000 + 1) AS order_id,
        'P0' || CAST(1 + (i % 8) AS VARCHAR) AS product_id,
        CAST(1 + (random() * 3) AS INTEGER) AS quantity,
        0.0 AS unit_price,
        CASE WHEN (i % 5 == 0) THEN 0.10 ELSE 0.0 END AS discount
    FROM range(1, 65001) t(i);

    UPDATE order_items
    SET unit_price = p.price
    FROM products p
    WHERE order_items.product_id = p.product_id;

    UPDATE orders
    SET order_amount = sub.total + orders.shipping_fee
    FROM (
        SELECT order_id, SUM(quantity * unit_price * (1.0 - discount)) AS total
        FROM order_items
        GROUP BY order_id
    ) sub
    WHERE orders.order_id = sub.order_id;
    """)

    total_orders = con.execute("SELECT count(*) FROM orders").fetchone()[0]
    print(f">>> Successfully generated {total_orders:,} orders in DuckDB!")
    con.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Enterprise DuckDB Analytics API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_con():
    return duckdb.connect(DB_FILE, read_only=False)

class NewOrderPayload(BaseModel):
    customer_id: int
    product_id: str
    warehouse_id: str
    quantity: int
    payment_method: str

@app.get("/api/overview")
def get_overview():
    start = time.perf_counter()
    con = get_con()
    kpi_query = """
    SELECT 
        COUNT(order_id) AS total_orders,
        ROUND(SUM(order_amount), 2) AS total_revenue,
        ROUND(AVG(order_amount), 2) AS avg_order_value,
        COUNT(DISTINCT customer_id) AS active_customers,
        SUM(CASE WHEN order_status = 'Returned' THEN 1 ELSE 0 END) AS returned_orders
    FROM orders
    """
    records = fetch_as_dicts(con, kpi_query)
    kpis = records[0] if records else {}
    
    low_stock = con.execute("SELECT count(*) FROM inventory WHERE stock_quantity <= reorder_level").fetchone()[0]
    kpis["low_stock_alerts"] = low_stock
    kpis["query_execution_time_ms"] = round((time.perf_counter() - start) * 1000, 2)
    con.close()
    return kpis

@app.get("/api/analytics/monthly-revenue")
def get_monthly_revenue():
    start = time.perf_counter()
    con = get_con()
    query = """
    SELECT 
        STRFTIME(order_date, '%Y-%m') AS month,
        ROUND(SUM(order_amount) / 1000000.0, 2) AS revenue_millions,
        COUNT(order_id) AS order_count
    FROM orders
    WHERE order_status = 'Completed'
    GROUP BY month
    ORDER BY month ASC
    LIMIT 12
    """
    data = fetch_as_dicts(con, query)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    con.close()
    return {"data": data, "execution_time_ms": elapsed_ms}

@app.get("/api/analytics/warehouse-distribution")
def get_warehouse_distribution():
    con = get_con()
    query = """
    SELECT 
        w.warehouse_id,
        w.warehouse_name,
        w.city,
        w.capacity,
        SUM(i.stock_quantity) AS total_stored_items,
        ROUND((SUM(i.stock_quantity) * 100.0) / w.capacity, 1) AS utilization_pct
    FROM warehouses w
    JOIN inventory i ON w.warehouse_id = i.warehouse_id
    GROUP BY w.warehouse_id, w.warehouse_name, w.city, w.capacity
    ORDER BY total_stored_items DESC
    """
    data = fetch_as_dicts(con, query)
    con.close()
    return data

@app.get("/api/analytics/customer-tiers")
def get_customer_tiers():
    con = get_con()
    query = """
    SELECT 
        c.tier,
        COUNT(DISTINCT c.customer_id) AS customer_count,
        ROUND(SUM(o.order_amount), 2) AS total_spend,
        ROUND(AVG(o.order_amount), 2) AS avg_spend_per_order
    FROM customers c
    JOIN orders o ON c.customer_id = o.customer_id
    GROUP BY c.tier
    ORDER BY total_spend DESC
    """
    data = fetch_as_dicts(con, query)
    con.close()
    return data

@app.get("/api/catalog")
def get_catalog():
    con = get_con()
    query = """
    SELECT 
        p.product_id,
        p.product_name,
        p.category,
        p.price,
        v.vendor_name,
        SUM(i.stock_quantity) AS total_stock
    FROM products p
    JOIN vendors v ON p.vendor_id = v.vendor_id
    JOIN inventory i ON p.product_id = i.product_id
    GROUP BY p.product_id, p.product_name, p.category, p.price, v.vendor_name
    ORDER BY p.product_id
    """
    data = fetch_as_dicts(con, query)
    con.close()
    return data

@app.post("/api/orders/place")
def place_order(payload: NewOrderPayload):
    con = get_con()
    stock = con.execute("""
        SELECT stock_quantity FROM inventory 
        WHERE product_id = ? AND warehouse_id = ?
    """, [payload.product_id, payload.warehouse_id]).fetchone()
    
    if not stock or stock[0] < payload.quantity:
        con.close()
        raise HTTPException(status_code=400, detail="Insufficient stock in the selected warehouse.")

    price = con.execute("SELECT price FROM products WHERE product_id = ?", [payload.product_id]).fetchone()[0]
    total_amount = (price * payload.quantity) + 150.0

    new_order_id = int(time.time() * 1000)
    con.execute("""
        INSERT INTO orders VALUES (?, ?, 'LP01', CURRENT_DATE, 'Completed', ?, 150.0, ?)
    """, [new_order_id, payload.customer_id, payload.payment_method, total_amount])

    new_item_id = int(time.time() * 1000) + 1
    con.execute("""
        INSERT INTO order_items VALUES (?, ?, ?, ?, ?, 0.0)
    """, [new_item_id, new_order_id, payload.product_id, payload.quantity, price])

    con.execute("""
        UPDATE inventory 
        SET stock_quantity = stock_quantity - ?
        WHERE product_id = ? AND warehouse_id = ?
    """, [payload.quantity, payload.product_id, payload.warehouse_id])

    con.close()
    return {
        "status": "Success",
        "order_id": new_order_id,
        "total_amount": total_amount,
        "message": f"Order #{new_order_id} recorded in DuckDB and inventory allocated."
    }

@app.get("/api/benchmark")
def run_benchmark():
    con = get_con()
    start = time.perf_counter()
    query = """
        SELECT 
            p.category,
            c.tier,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.quantity * oi.unit_price), 2) AS gross_sales,
            ROUND(AVG(oi.quantity), 2) AS avg_basket_size
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN customers c ON o.customer_id = c.customer_id
        GROUP BY p.category, c.tier
        ORDER BY gross_sales DESC
    """
    results = fetch_as_dicts(con, query)
    duration = (time.perf_counter() - start) * 1000
    con.close()
    
    return {
        "rows_scanned": 115000,
        "execution_time_ms": round(duration, 2),
        "results": results
    }