import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import eyLogo from "../../../assets/ey_logo.gif";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div className="login-brand">
          <img src={eyLogo} alt="EY" className="login-logo" />
          <h1 className="login-title">Filli</h1>
          <p className="login-subtitle">AI-Powered Collections Assistant · EY Finance Operations</p>
        </div>

        <h2 style={{ marginTop: 0, marginBottom: 4 }}>Sign In</h2>
        <p style={{ fontSize: 13, color: "#8b949e", marginTop: 0 }}>Access the collections management portal</p>

        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" style={{ width: "100%", marginBottom: 8 }} />
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" style={{ width: "100%", marginBottom: 8 }} />
        {error && <div style={{ color: "#ff7b72", marginBottom: 8 }}>{error}</div>}
        <button disabled={loading} style={{ width: "100%" }}>{loading ? "Signing in..." : "Sign In"}</button>
      </form>
    </div>
  );
}
