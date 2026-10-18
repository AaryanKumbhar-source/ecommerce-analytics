import React, { useEffect, useState, useRef } from "react";
import { Network } from "vis-network/standalone";
import { 
  ShoppingBag, 
  Share2, 
  Sparkles, 
  CheckCircle, 
  Database, 
  Package, 
  RefreshCw 
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("catalog");
  const [catalog, setCatalog] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(101);
  const [recommendations, setRecommendations] = useState([]);
  const [loadingRecs, setLoadingRecs] = useState(false);
  const [orderMessage, setOrderMessage] = useState("");
  const [placingOrder, setPlacingOrder] = useState(false);
  
  const graphContainerRef = useRef(null);
  const networkInstanceRef = useRef(null);

  useEffect(() => {
    fetchCatalog();
    fetchCustomers();
  }, []);

  useEffect(() => {
    if (selectedCustomer) {
      fetchRecommendations(selectedCustomer);
    }
  }, [selectedCustomer]);

  useEffect(() => {
    if (activeTab === "graph") {
      fetchAndRenderGraph();
    }
  }, [activeTab]);

  const fetchCatalog = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/catalog`);
      const data = await res.json();
      setCatalog(data);
    } catch (err) {
      console.error("Failed to load catalog:", err);
    }
  };

  const fetchCustomers = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/customers`);
      const data = await res.json();
      setCustomers(data);
    } catch (err) {
      console.error("Failed to load customers:", err);
    }
  };

  const fetchRecommendations = async (custId) => {
    setLoadingRecs(true);
    try {
      const res = await fetch(`${API_BASE}/api/recommendations/${custId}`);
      const data = await res.json();
      setRecommendations(data);
    } catch (err) {
      console.error("Failed to load recommendations:", err);
    } finally {
      setLoadingRecs(false);
    }
  };

  const handleBuyProduct = async (product) => {
    setPlacingOrder(true);
    setOrderMessage("");
    const newOrderId = Math.floor(1000 + Math.random() * 9000);
    try {
      const res = await fetch(`${API_BASE}/api/orders`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: newOrderId,
          customer_id: selectedCustomer,
          items: [{ product_id: product.product_id, quantity: 1 }]
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setOrderMessage(`Order #${newOrderId} placed successfully for ₹${product.price.toLocaleString()}!`);
        fetchCustomers();
        fetchRecommendations(selectedCustomer);
      } else {
        setOrderMessage(`Error: ${data.detail || "Could not place order"}`);
      }
    } catch (err) {
      setOrderMessage("Server connection error while placing order.");
    } finally {
      setPlacingOrder(false);
    }
  };

  const fetchAndRenderGraph = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/graph-data`);
      const data = await res.json();

      const colorMap = {
        Customer: "#ec4899",
        Product: "#8b5cf6",
        Order: "#10b981",
        Warehouse: "#f59e0b",
        Vendor: "#3b82f6",
        LogisticsPartner: "#6366f1"
      };

      const visNodes = data.nodes.map(n => ({
        id: n.id,
        label: `${n.name}\n[${n.label}]`,
        shape: "dot",
        size: n.label === "Product" || n.label === "Customer" ? 22 : 16,
        color: {
          background: colorMap[n.label] || "#94a3b8",
          border: "#ffffff",
          highlight: { background: "#ffffff", border: "#000000" }
        },
        font: { color: "#ffffff", size: 12, face: "sans-serif" }
      }));

      const visEdges = data.links.map(l => ({
        from: l.source,
        to: l.target,
        label: l.label,
        arrows: "to",
        font: { color: "#94a3b8", size: 9, align: "middle" },
        color: { color: "#475569", highlight: "#38bdf8" },
        smooth: { type: "continuous" }
      }));

      if (graphContainerRef.current) {
        const container = graphContainerRef.current;
        const graphData = { nodes: visNodes, edges: visEdges };
        const options = {
          physics: {
            stabilization: false,
            barnesHut: { gravitationalConstant: -3500, springLength: 120 }
          },
          interaction: { hover: true, tooltipDelay: 100 }
        };
        networkInstanceRef.current = new Network(container, graphData, options);
      }
    } catch (err) {
      console.error("Failed to render graph:", err);
    }
  };

  const currentCustomerObj = customers.find(c => c.customer_id === Number(selectedCustomer));

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "#0f172a", color: "#f8fafc", fontFamily: "Segoe UI, sans-serif" }}>
      {/* Top Navbar */}
      <header style={{ borderBottom: "1px solid #1e293b", padding: "16px 32px", display: "flex", justifyContent: "space-between", alignItems: "center", backgroundColor: "#1e293b" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Database size={28} color="#38bdf8" />
          <div>
            <h1 style={{ margin: 0, fontSize: "1.25rem", fontWeight: "bold", letterSpacing: "0.5px" }}>
              Enterprise Neo4j E-Commerce Platform
            </h1>
            <span style={{ fontSize: "0.8rem", color: "#38bdf8" }}>Connected to Neo4j AuraDB Free Cloud Instance</span>
          </div>
        </div>

        {/* Customer Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px", background: "#0f172a", padding: "8px 16px", borderRadius: "8px", border: "1px solid #334155" }}>
          <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>Active Customer:</span>
          <select 
            value={selectedCustomer} 
            onChange={(e) => setSelectedCustomer(Number(e.target.value))}
            style={{ background: "#1e293b", color: "#ffffff", border: "1px solid #475569", padding: "6px 10px", borderRadius: "6px", cursor: "pointer" }}
          >
            {customers.map(c => (
              <option key={c.customer_id} value={c.customer_id}>
                {c.name} ({c.tier} Tier - {c.loyalty_points} pts)
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav style={{ padding: "16px 32px", borderBottom: "1px solid #1e293b", display: "flex", gap: "12px" }}>
        <button
          onClick={() => setActiveTab("catalog")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            borderRadius: "6px",
            border: "none",
            cursor: "pointer",
            fontWeight: "600",
            backgroundColor: activeTab === "catalog" ? "#38bdf8" : "#1e293b",
            color: activeTab === "catalog" ? "#0f172a" : "#cbd5e1"
          }}
        >
          <ShoppingBag size={18} /> Storefront Catalog
        </button>
        <button
          onClick={() => setActiveTab("graph")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            borderRadius: "6px",
            border: "none",
            cursor: "pointer",
            fontWeight: "600",
            backgroundColor: activeTab === "graph" ? "#38bdf8" : "#1e293b",
            color: activeTab === "graph" ? "#0f172a" : "#cbd5e1"
          }}
        >
          <Share2 size={18} /> Live Neo4j Graph View
        </button>
      </nav>

      {/* Main Container */}
      <main style={{ padding: "32px", maxWidth: "1400px", margin: "0 auto" }}>
        {orderMessage && (
          <div style={{ backgroundColor: "#065f46", color: "#a7f3d0", padding: "12px 18px", borderRadius: "8px", marginBottom: "24px", display: "flex", alignItems: "center", gap: "10px" }}>
            <CheckCircle size={20} />
            {orderMessage}
          </div>
        )}

        {/* Tab 1: Catalog & Recommendations */}
        {activeTab === "catalog" && (
          <div>
            {currentCustomerObj && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px", marginBottom: "32px" }}>
                <div style={{ background: "#1e293b", padding: "16px", borderRadius: "10px", border: "1px solid #334155" }}>
                  <div style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Customer Name</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: "bold" }}>{currentCustomerObj.name}</div>
                  <div style={{ color: "#64748b", fontSize: "0.8rem" }}>{currentCustomerObj.email}</div>
                </div>
                <div style={{ background: "#1e293b", padding: "16px", borderRadius: "10px", border: "1px solid #334155" }}>
                  <div style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Loyalty Tier</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: "bold", color: "#facc15" }}>★ {currentCustomerObj.tier}</div>
                  <div style={{ color: "#64748b", fontSize: "0.8rem" }}>{currentCustomerObj.loyalty_points} Reward Points</div>
                </div>
                <div style={{ background: "#1e293b", padding: "16px", borderRadius: "10px", border: "1px solid #334155" }}>
                  <div style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Subscription Status</div>
                  <div style={{ fontSize: "1.2rem", fontWeight: "bold", color: "#34d399" }}>{currentCustomerObj.subscription_status}</div>
                  <div style={{ color: "#64748b", fontSize: "0.8rem" }}>{currentCustomerObj.order_count} Total Orders</div>
                </div>
              </div>
            )}

            {/* Neo4j Collaborative Filtering Recommendation Panel */}
            <div style={{ background: "linear-gradient(135deg, #1e1b4b 0%, #1e293b 100%)", padding: "24px", borderRadius: "12px", border: "1px solid #6366f1", marginBottom: "32px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                <Sparkles size={24} color="#818cf8" />
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.2rem", color: "#c7d2fe" }}>Graph-Powered Personalized Recommendations</h3>
                  <div style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
                    Cypher Traversal: <code>(c1)-[:PLACED]-&gt;(:Order)-[:CONTAINS]-&gt;(:Product)&lt;-[:CONTAINS]-(:Order)&lt;-[:PLACED]-(c2)</code>
                  </div>
                </div>
              </div>

              {loadingRecs ? (
                <div style={{ color: "#94a3b8" }}>Running graph traversal in Neo4j...</div>
              ) : recommendations.length === 0 ? (
                <div style={{ color: "#94a3b8", fontSize: "0.9rem" }}>No personalized recommendations yet. Place an order to generate graph traversal links!</div>
              ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px" }}>
                  {recommendations.map(r => (
                    <div key={r.product_id} style={{ background: "#0f172a", padding: "16px", borderRadius: "8px", border: "1px solid #4338ca", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontWeight: "bold", color: "#f8fafc" }}>{r.product_name}</div>
                        <div style={{ color: "#a5b4fc", fontSize: "0.85rem" }}>₹{r.price.toLocaleString()} • {r.category}</div>
                        <span style={{ fontSize: "0.75rem", background: "#312e81", color: "#c7d2fe", padding: "2px 8px", borderRadius: "4px" }}>
                          Score: {r.similarity_score} graph links
                        </span>
                      </div>
                      <button
                        onClick={() => handleBuyProduct(r)}
                        disabled={placingOrder}
                        style={{ background: "#6366f1", color: "#fff", border: "none", padding: "8px 14px", borderRadius: "6px", cursor: "pointer", fontWeight: "bold" }}
                      >
                        Buy Now
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Catalog */}
            <h3 style={{ fontSize: "1.3rem", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <Package size={22} color="#38bdf8" /> Available Products & Warehouse Stock
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "20px" }}>
              {catalog.map(item => (
                <div key={item.product_id} style={{ background: "#1e293b", padding: "20px", borderRadius: "10px", border: "1px solid #334155", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                      <h4 style={{ margin: "0 0 4px 0", fontSize: "1.1rem" }}>{item.name}</h4>
                      <span style={{ background: "#0f172a", padding: "4px 8px", borderRadius: "4px", fontSize: "0.75rem", color: "#38bdf8" }}>{item.category}</span>
                    </div>
                    <div style={{ fontSize: "1.3rem", fontWeight: "bold", color: "#38bdf8", margin: "8px 0" }}>
                      ₹{item.price.toLocaleString()}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "12px" }}>
                      Vendor: <span style={{ color: "#e2e8f0" }}>{item.vendor_name}</span>
                    </div>

                    <div style={{ background: "#0f172a", padding: "10px", borderRadius: "6px", fontSize: "0.8rem", color: "#94a3b8", marginBottom: "16px" }}>
                      <div style={{ fontWeight: "600", marginBottom: "4px", color: "#cbd5e1" }}>Distributed Warehouse Stock:</div>
                      {item.inventory.map((inv, idx) => (
                        <div key={idx} style={{ display: "flex", justifyContent: "space-between" }}>
                          <span>{inv.warehouse} ({inv.city})</span>
                          <span style={{ color: inv.stock > 0 ? "#34d399" : "#f87171" }}>{inv.stock} in stock</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => handleBuyProduct(item)}
                    disabled={placingOrder}
                    style={{ background: "#0284c7", color: "#fff", border: "none", padding: "10px", borderRadius: "6px", fontWeight: "bold", cursor: "pointer" }}
                  >
                    Place Order as {currentCustomerObj ? currentCustomerObj.name : "Customer"}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 2: Interactive Graph View */}
        {activeTab === "graph" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <div>
                <h3 style={{ margin: "0 0 4px 0", fontSize: "1.3rem" }}>Interactive Neo4j Graph Visualizer</h3>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "#94a3b8" }}>
                  Click and drag nodes to explore relationships. Color legend: 
                  <span style={{ color: "#ec4899", marginLeft: "10px" }}>● Customer</span>
                  <span style={{ color: "#8b5cf6", marginLeft: "10px" }}>● Product</span>
                  <span style={{ color: "#10b981", marginLeft: "10px" }}>● Order</span>
                  <span style={{ color: "#f59e0b", marginLeft: "10px" }}>● Warehouse</span>
                  <span style={{ color: "#3b82f6", marginLeft: "10px" }}>● Vendor</span>
                  <span style={{ color: "#6366f1", marginLeft: "10px" }}>● Logistics</span>
                </p>
              </div>
              <button
                onClick={fetchAndRenderGraph}
                style={{ display: "flex", alignItems: "center", gap: "6px", background: "#1e293b", color: "#38bdf8", border: "1px solid #38bdf8", padding: "8px 14px", borderRadius: "6px", cursor: "pointer" }}
              >
                <RefreshCw size={16} /> Re-center Graph
              </button>
            </div>

            <div 
              ref={graphContainerRef} 
              style={{ width: "100%", height: "650px", background: "#020617", borderRadius: "12px", border: "1px solid #334155" }}
            />
          </div>
        )}
      </main>
    </div>
  );
}