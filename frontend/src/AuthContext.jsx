import { createContext, useContext, useEffect, useState } from "react";
import { loginApi, meApi } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("filli_token");
    if (!token) {
      setLoading(false);
      return;
    }
    meApi()
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem("filli_token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (username, password) => {
    const res = await loginApi(username, password);
    localStorage.setItem("filli_token", res.data.access_token);
    setUser(res.data.user);
  };

  const logout = () => {
    localStorage.removeItem("filli_token");
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
