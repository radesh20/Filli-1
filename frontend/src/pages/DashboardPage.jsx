import { useEffect, useState } from "react";
import { BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, LineChart, Line, Legend } from "recharts";
import { summaryApi, trendsApi, riskApi, teamApi } from "../api";
import { useAuth } from "../AuthContext";

const COLORS = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"];
const ANALYST = "Collections Analyst";
const MANAGER = "Collections Manager";

export default function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState([]);
  const [risk, setRisk] = useState([]);
  const [team, setTeam] = useState([]);

  useEffect(() => {
    Promise.all([summaryApi(), trendsApi(), riskApi(), teamApi()]).then(([s, t, r, tm]) => {
      setSummary(s.data);
      setTrends(t.data);
      setRisk(r.data);
      setTeam(tm.data || []);
    });
  }, []);

  if (!summary) return <div>Loading dashboard...</div>;

  const isAnalyst = user?.role === ANALYST;
  const isManager = user?.role === MANAGER;

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2>Dashboard</h2>
      <div style={{ fontSize: 13, color: "#8b949e" }}>Viewing as: {user?.name} ({user?.role})</div>

      <div className="grid-4">
        <div className="card"><div>{isAnalyst ? "My Overdue" : "Total Overdue"}</div><h3>Rs.{summary.overdue.total_overdue_amount.toLocaleString()}</h3></div>
        <div className="card"><div>Overdue Invoices</div><h3>{summary.overdue.total_overdue_invoices}</h3></div>
        <div className="card"><div>Critical (&gt;90d)</div><h3>{summary.overdue.critical_count}</h3></div>
        <div className="card"><div>High (61-90d)</div><h3>{summary.overdue.high_count}</h3></div>
      </div>

      <div className="grid-2">
        <div className="card" style={{ height: 320 }}>
          <h4>Overdue Trend</h4>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={trends.slice(-8)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2d4f" />
              <XAxis dataKey="week" hide />
              <YAxis />
              <Tooltip />
              <Bar dataKey="total_overdue" fill="#ffe600" />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card" style={{ height: 320 }}>
          <h4>Risk Distribution</h4>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={risk} dataKey="count" nameKey="risk_level" outerRadius={90}>
                {risk.map((entry, index) => <Cell key={entry.risk_level} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {isManager && (
        <div className="card" style={{ minHeight: 340 }}>
          <h4>Manager View: Team Performance</h4>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={team}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2d4f" />
              <XAxis dataKey="analyst" />
              <YAxis yAxisId="left" />
              <YAxis yAxisId="right" orientation="right" />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="total_overdue_amount" fill="#ffe600" name="Overdue Amount" />
              <Line yAxisId="right" type="monotone" dataKey="collection_rate" stroke="#e74c3c" strokeWidth={2} name="Collection Rate (%)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
