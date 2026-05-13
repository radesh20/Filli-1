import { Navigate, Route, Routes, Link, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import AssistantPage from "./pages/AssistantPage";
import InvoicesPage from "./pages/InvoicesPage";
import ActionsPage from "./pages/ActionsPage";
import eyLogo from "../../assets/ey_logo.gif";

function ProtectedLayout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <img src={eyLogo} alt="EY" className="sidebar-logo" />
          <h2 className="sidebar-title">Filli</h2>
          <p className="sidebar-subtitle">AI Collections Assistant</p>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-user-name">{user.name}</div>
          <div className="sidebar-user-role">{user.role}</div>
        </div>

        <div className="sidebar-nav">
          <Link to="/dashboard" className={`sidebar-link ${location.pathname === "/dashboard" ? "active" : ""}`}>Dashboard</Link>
          <Link to="/assistant" className={`sidebar-link ${location.pathname === "/assistant" ? "active" : ""}`}>Assistant</Link>
          <Link to="/invoices" className={`sidebar-link ${location.pathname === "/invoices" ? "active" : ""}`}>Invoices</Link>
          <Link to="/actions" className={`sidebar-link ${location.pathname === "/actions" ? "active" : ""}`}>Actions</Link>
        </div>

        <button onClick={logout} className="btn-secondary">Logout</button>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<ProtectedLayout><DashboardPage /></ProtectedLayout>} />
      <Route path="/assistant" element={<ProtectedLayout><AssistantPage /></ProtectedLayout>} />
      <Route path="/invoices" element={<ProtectedLayout><InvoicesPage /></ProtectedLayout>} />
      <Route path="/actions" element={<ProtectedLayout><ActionsPage /></ProtectedLayout>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
