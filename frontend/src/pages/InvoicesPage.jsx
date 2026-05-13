import { useEffect, useState } from "react";
import { invoicesApi } from "../api";
import { useAuth } from "../AuthContext";

export default function InvoicesPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("");
  const [minDays, setMinDays] = useState("");

  const load = async () => {
    const params = {};
    if (status) params.status = status;
    if (minDays) params.min_days_overdue = Number(minDays);
    const res = await invoicesApi(params);
    setRows(res.data);
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2>Invoices</h2>
      <div style={{ fontSize: 13, color: "#8b949e" }}>
        Viewing as: {user?.name} ({user?.role}){user?.analyst_id ? ` | Portfolio: ${user.analyst_id}` : ""}
      </div>
      <div className="card" style={{ display: "flex", gap: 8 }}>
        <input value={status} onChange={(e) => setStatus(e.target.value)} placeholder="Status (Open, Escalated...)" />
        <input value={minDays} onChange={(e) => setMinDays(e.target.value)} placeholder="Min overdue days" />
        <button onClick={load}>Apply</button>
      </div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Invoice</th><th>Customer</th><th>Amount</th><th>Days</th><th>Status</th><th>Analyst</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.invoice_id}>
                <td>{r.invoice_id}</td>
                <td>{r.customer_name}</td>
                <td>Rs.{Number(r.amount).toLocaleString()}</td>
                <td>{r.days_overdue}</td>
                <td>{r.status}</td>
                <td>{r.assigned_analyst}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
