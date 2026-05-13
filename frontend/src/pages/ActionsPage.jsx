import { useEffect, useMemo, useState } from "react";
import { actionLogApi } from "../api";
import { useAuth } from "../AuthContext";

const MANAGER = "Collections Manager";

export default function ActionsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [tab, setTab] = useState("actions");

  useEffect(() => {
    actionLogApi().then((res) => setRows(res.data.slice().reverse()));
  }, []);

  const calls = useMemo(() => rows.filter((r) => r.type === "call"), [rows]);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2>Action Log</h2>
      <div style={{ fontSize: 13, color: "#8b949e" }}>Viewing as: {user?.name} ({user?.role})</div>

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => setTab("actions")} style={{ opacity: tab === "actions" ? 1 : 0.7 }}>Actions</button>
        <button onClick={() => setTab("transcripts")} style={{ opacity: tab === "transcripts" ? 1 : 0.7 }}>Call Transcripts</button>
      </div>

      {tab === "actions" && (
        <div className="card">
          <table>
            <thead>
              <tr>
                <th>Type</th><th>Customer</th><th>Invoice</th><th>Amount</th><th>Result</th><th>When</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, idx) => (
                <tr key={`${r.timestamp}-${idx}`}>
                  <td>{r.type}</td>
                  <td>{r.customer}</td>
                  <td>{r.invoice_id}</td>
                  <td>{r.amount ? `Rs.${Number(r.amount).toLocaleString()}` : "-"}</td>
                  <td>{r.result || r.outcome || "-"}</td>
                  <td>{r.timestamp}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "transcripts" && (
        <div style={{ display: "grid", gap: 10 }}>
          {calls.length === 0 && <div className="card">No call transcripts available yet.</div>}
          {calls.map((c, idx) => (
            <div className="card" key={`${c.call_id || c.timestamp}-${idx}`}>
              <div><b>{c.customer}</b> | Invoice: {c.invoice_id || "-"}</div>
              <div style={{ fontSize: 13, color: "#8b949e", marginTop: 4 }}>
                Outcome: {(c.outcome || "unknown").replaceAll("_", " ")} | Duration: {c.call_duration || "-"}
              </div>
              <div style={{ marginTop: 8 }}>
                <b>{user?.role === MANAGER ? "Call Summary" : "Transcript"}:</b>
              </div>
              <div style={{ marginTop: 4, whiteSpace: "pre-wrap" }}>
                {user?.role === MANAGER ? (c.summary || "Summary unavailable") : (c.transcript || c.summary || "Transcript unavailable")}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
