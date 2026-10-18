# ApexAnalytics • Enterprise DuckDB OLAP Web Platform

Modern, high-performance, enterprise-grade web application powered by **FastAPI**, **DuckDB** (in-process columnar vectorized database), and a reactive **Single-Page Application** (Tailwind CSS CDN, Chart.js, Lucide Icons).

---

## 🏛️ Architecture Overview

- **Backend**: Python FastAPI with Uvicorn ASGI server.
- **Database Engine**: DuckDB (`ecommerce_analytics.duckdb`) embedded in-process, featuring SIMD vectorized morsel execution, `QUALIFY` filtering, and sliding window partitions.
- **Connection Model**: Read-only connection pool for non-blocking concurrent OLAP queries; exclusive context-managed connections (`with duckdb.connect(...)`) for write transactions to prevent file locks.
- **Frontend**: Lightweight single-page application (`static/index.html`) using Tailwind CSS via CDN, Chart.js for responsive visual analytics, and Lucide icons. Zero `node_modules`, zero React build tools, zero bundling overhead.

---

## 🚀 Quickstart Guide

### 1. Set Up Virtual Environment & Dependencies

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1
# Or Windows CMD:
# .\.venv\Scripts\activate.bat
# Or Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Seed Database (DuckDB Embedded OLAP)

```powershell
python seed_db.py
```

### 3. Launch the FastAPI Application

```powershell
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at **`http://localhost:8000`**. Interactive OpenAPI documentation is available at **`http://localhost:8000/docs`**.

---

## ⚡ REST API Specifications

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves single-page application `static/index.html` |
| `GET` | `/api/kpis` | Real-time gross revenue, profit, orders, active customers, AOV, and margin % |
| `GET` | `/api/charts/velocity` | Daily sales timeline with rolling 7-day moving averages (`ROWS BETWEEN 6 PRECEDING`) |
| `GET` | `/api/charts/pareto` | Product 80/20 cumulative profit distributions (`ROWS UNBOUNDED PRECEDING`) |
| `GET` | `/api/charts/rfm` | Customer Recency, Frequency, and Monetary scoring via DuckDB `QUALIFY` clause |
| `GET` | `/api/charts/funnel` | Multi-touchpoint clickstream funnel conversion by customer segment |
| `GET` | `/api/tables/{table}` | Dynamic table viewer with keyword search and limit pagination |
| `GET` | `/api/categories` | Catalog category options for product creation |
| `POST` | `/api/products` | Inserts a new validated product into DuckDB with lock-free connection release |
| `POST` | `/api/execute-sql` | Interactive SQL console for executing read-only queries with millisecond timer |
| `GET` | `/api/architecture` | Live schema topology and DuckDB engine thread/memory settings |
