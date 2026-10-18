"""
Seed Database Script for E-Commerce OLAP Analytics
Database: DuckDB (embedded file: ecommerce_analytics.duckdb)
"""

import duckdb
import random
from datetime import datetime, timedelta

DB_FILE = "ecommerce_analytics.duckdb"

def seed_database():
    print(f"Connecting to DuckDB database: {DB_FILE}...")
    conn = duckdb.connect(DB_FILE)

    # 1. Drop existing tables for idempotent seed execution
    print("Dropping existing tables if any...")
    conn.execute("""
        DROP TABLE IF EXISTS customer_interactions;
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS categories;
        DROP TABLE IF EXISTS customers;
    """)

    # 2. Schema Definition
    print("Creating relational OLAP schema...")
    conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            customer_name VARCHAR NOT NULL,
            email VARCHAR NOT NULL UNIQUE,
            segment VARCHAR NOT NULL,
            city VARCHAR NOT NULL,
            country VARCHAR NOT NULL,
            signup_date DATE NOT NULL
        );

        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY,
            category_name VARCHAR NOT NULL,
            department VARCHAR NOT NULL
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name VARCHAR NOT NULL,
            category_id INTEGER NOT NULL,
            unit_price DOUBLE NOT NULL,
            cost_price DOUBLE NOT NULL,
            stock_level INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            order_date DATE NOT NULL,
            status VARCHAR NOT NULL,
            payment_method VARCHAR NOT NULL,
            shipping_cost DOUBLE NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        CREATE TABLE order_items (
            item_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price DOUBLE NOT NULL,
            discount DOUBLE NOT NULL DEFAULT 0.0,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        CREATE TABLE customer_interactions (
            interaction_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            session_duration_sec INTEGER NOT NULL,
            action_type VARCHAR NOT NULL,
            rating INTEGER,
            interaction_timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
    """)

    # 3. Seed Data Generation
    print("Generating realistic synthetic seed dataset...")
    random.seed(42)

    # Categories
    categories_data = [
        (1, "Laptops & Computers", "Electronics"),
        (2, "Smartphones & Tablets", "Electronics"),
        (3, "Audio & Headphones", "Electronics"),
        (4, "Office Furniture", "Home & Furniture"),
        (5, "Kitchen Appliances", "Home & Living"),
        (6, "Fitness & Sportswear", "Apparel & Health"),
    ]
    conn.executemany("INSERT INTO categories VALUES (?, ?, ?)", categories_data)

    # Customers (25 records)
    first_names = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", "Pat", "Avery", "Riley", "Cameron",
                   "Dakota", "Reese", "Casey", "Quinn", "Skyler", "Jesse", "Jamie", "Logan", "Peyton", "Kendall",
                   "Harper", "Rowan", "Hayden", "Finley", "Emerson"]
    last_names = ["Chen", "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez",
                  "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson",
                  "Martin", "Lee", "Perez", "Thompson", "White"]
    segments = ["Consumer", "Corporate", "Home Office"]
    cities = [("San Francisco", "USA"), ("New York", "USA"), ("London", "UK"), ("Berlin", "Germany"), 
              ("Toronto", "Canada"), ("Tokyo", "Japan"), ("Bengaluru", "India"), ("Sydney", "Australia")]

    customers_data = []
    base_date = datetime(2025, 1, 1)
    for i in range(1, 26):
        c_name = f"{first_names[i-1]} {last_names[i-1]}"
        email = f"{first_names[i-1].lower()}.{last_names[i-1].lower()}{i}@example.com"
        seg = segments[i % len(segments)]
        city, country = cities[i % len(cities)]
        s_date = (base_date + timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d")
        customers_data.append((i, c_name, email, seg, city, country, s_date))

    conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?, ?, ?)", customers_data)

    # Products (20 records)
    products_catalog = [
        (101, "UltraBook Pro 15", 1, 1299.99, 850.00, 45),
        (102, "MacBook Air M3", 1, 1099.00, 720.00, 30),
        (103, "ThinkPad X1 Carbon", 1, 1450.00, 920.00, 25),
        (104, "Gaming Rig RTX 4080", 1, 2199.99, 1500.00, 15),
        (105, "Galaxy S24 Ultra", 2, 1199.99, 780.00, 60),
        (106, "iPhone 16 Pro Max", 2, 1299.00, 840.00, 50),
        (107, "Pixel 9 Pro", 2, 999.00, 620.00, 40),
        (108, "iPad Air 11-inch", 2, 599.00, 380.00, 55),
        (109, "Sony WH-1000XM5", 3, 398.00, 220.00, 75),
        (110, "Bose QuietComfort Ultra", 3, 429.00, 240.00, 65),
        (111, "AirPods Pro 2", 3, 249.00, 140.00, 90),
        (112, "Ergonomic Mesh Chair", 4, 349.50, 180.00, 35),
        (113, "Standing Desk Motorized", 4, 499.00, 280.00, 20),
        (114, "Dual Monitor Arm Mount", 4, 89.99, 42.00, 80),
        (115, "Espresso Machine Deluxe", 5, 649.00, 390.00, 28),
        (116, "Air Fryer Max 6L", 5, 129.99, 65.00, 70),
        (117, "Smart Robot Vacuum", 5, 399.00, 210.00, 32),
        (118, "Adjustable Dumbbells Set", 6, 299.99, 150.00, 40),
        (119, "Smart Fitness Tracker Band", 6, 99.50, 45.00, 110),
        (120, "Treadmill Foldable Pro", 6, 799.00, 460.00, 18),
    ]
    conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?)", products_catalog)

    # Orders (60 records)
    statuses = ["Completed", "Completed", "Completed", "Shipped", "Pending", "Cancelled"]
    pay_methods = ["Credit Card", "PayPal", "UPI", "Bank Transfer"]
    orders_data = []
    order_items_data = []
    item_counter = 1

    start_order_date = datetime(2025, 6, 1)

    for order_id in range(1, 61):
        cust_id = random.randint(1, 25)
        # Orders spread over 120 days to support time-series & rolling window queries
        ord_date = (start_order_date + timedelta(days=random.randint(0, 120))).strftime("%Y-%m-%d")
        status = random.choice(statuses)
        pay_method = random.choice(pay_methods)
        shipping_cost = round(random.uniform(5.0, 30.0), 2)
        orders_data.append((order_id, cust_id, ord_date, status, pay_method, shipping_cost))

        # Generate 1 to 4 items per order
        num_items = random.randint(1, 4)
        chosen_products = random.sample(products_catalog, num_items)
        for prod in chosen_products:
            prod_id = prod[0]
            unit_price = prod[3]
            qty = random.randint(1, 3)
            discount = round(random.choice([0.0, 0.05, 0.10, 0.15]), 2)
            order_items_data.append((item_counter, order_id, prod_id, qty, unit_price, discount))
            item_counter += 1

    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders_data)
    conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?)", order_items_data)

    # Customer Interactions / Clickstream & Reviews (100 records)
    actions = ["view", "view", "add_to_cart", "purchase", "review"]
    interactions_data = []
    for int_id in range(1, 101):
        c_id = random.randint(1, 25)
        p_id = random.choice(products_catalog)[0]
        duration = random.randint(10, 450)
        action = random.choice(actions)
        rating = random.randint(3, 5) if action == "review" else None
        int_timestamp = (datetime(2025, 6, 1) + timedelta(days=random.randint(0, 120), minutes=random.randint(0, 1440)))
        interactions_data.append((int_id, c_id, p_id, duration, action, rating, int_timestamp))

    conn.executemany("INSERT INTO customer_interactions VALUES (?, ?, ?, ?, ?, ?, ?)", interactions_data)

    # 4. Print Summary Verification
    print("\n--- DATABASE SEEDING COMPLETE ---")
    tables = ["customers", "categories", "products", "orders", "order_items", "customer_interactions"]
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"Table '{t}': {count} records loaded.")

    conn.close()
    print(f"Successfully closed connection to {DB_FILE}.\n")

if __name__ == "__main__":
    seed_database()
