import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("filli_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const loginApi = (username, password) => api.post("/api/auth/login", { username, password });
export const meApi = () => api.get("/api/auth/me");
export const summaryApi = () => api.get("/api/dashboard/summary");
export const invoicesApi = (params = {}) => api.get("/api/invoices", { params });
export const customersApi = (params = {}) => api.get("/api/customers", { params });
export const chatApi = (message, history) => api.post("/api/assistant/chat", { message, history });
export const sendEmailApi = (payload) => api.post("/api/actions/email", payload);
export const callApi = (payload) => api.post("/api/actions/call", payload);
export const callStatusApi = (callId) => api.get(`/api/actions/call/${callId}/status`);
export const actionLogApi = () => api.get("/api/actions/log");
export const trendsApi = () => api.get("/api/analytics/trends");
export const riskApi = () => api.get("/api/analytics/risk");
export const cashflowApi = () => api.get("/api/analytics/cashflow");
export const teamApi = () => api.get("/api/analytics/team");

export default api;
