import { useEffect, useMemo, useState } from "react";
import { callApi, callStatusApi, chatApi, sendEmailApi } from "../api";
import { useAuth } from "../AuthContext";

const ANALYST = "Collections Analyst";

export default function AssistantPage() {
  const { user } = useAuth();
  const [messages, setMessages] = useState([{ role: "assistant", content: "Hi, I am Filli. Ask me anything about collections." }]);
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState("");
  const [action, setAction] = useState(null);
  const [callStatus, setCallStatus] = useState(null);

  const suggestedQuestions = useMemo(() => {
    if (user?.role === ANALYST) {
      return [
        "Which invoices should I prioritize for follow-up today?",
        "Show me the aging bucket distribution for my portfolio",
        "Send a reminder email to the top overdue customer"
      ];
    }
    return [
      "What is the total overdue balance across all customers?",
      "Which customer accounts require escalation this period?",
      "How is the collections team performing against KPIs?"
    ];
  }, [user?.role]);

  const send = async (prompt = input) => {
    if (!prompt.trim()) return;
    const userMsg = { role: "user", content: prompt };
    setMessages((m) => [...m, userMsg]);
    const res = await chatApi(prompt, history);
    setHistory(res.data.history);
    setMessages((m) => [...m, { role: "assistant", content: res.data.reply }]);
    setAction(res.data.action || null);
    setInput("");
  };

  const triggerEmail = async () => {
    const res = await sendEmailApi({ customer_id: action.customer_id, invoice_id: action.invoice_id });
    setMessages((m) => [...m, { role: "assistant", content: `Email result: ${res.data.result.status}` }]);
    setAction(null);
  };

  const triggerCall = async () => {
    const res = await callApi({ customer_id: action.customer_id, invoice_id: action.invoice_id });
    const callId = res.data.result.call_id;
    setMessages((m) => [...m, { role: "assistant", content: `Call started: ${callId}` }]);
    setAction(null);
    if (!callId) return;
    const timer = setInterval(async () => {
      const st = await callStatusApi(callId);
      setCallStatus(st.data);
      if (st.data.completed) clearInterval(timer);
    }, 5000);
  };

  useEffect(() => {
    if (callStatus?.completed) {
      setMessages((m) => [...m, { role: "assistant", content: `Call completed. Outcome: ${callStatus?.parsed_outcome?.outcome || callStatus.status}` }]);
    }
  }, [callStatus]);

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <h2>Assistant</h2>
      <div style={{ fontSize: 13, color: "#8b949e" }}>
        Logged in as: {user?.name} ({user?.role}){user?.analyst_id ? ` | Portfolio: ${user.analyst_id}` : ""}
      </div>

      <div className="card">
        <div style={{ marginBottom: 8, fontWeight: 600 }}>Suggested Questions</div>
        <div style={{ display: "grid", gap: 8 }}>
          {suggestedQuestions.map((q) => (
            <button key={q} onClick={() => send(q)}>{q}</button>
          ))}
        </div>
      </div>

      <div className="chat-box">
        {messages.map((m, i) => <div key={i} className={m.role === "user" ? "msg-user" : "msg-ai"}><b>{m.role === "user" ? "You" : "Filli"}:</b> {m.content}</div>)}
      </div>

      {action && (
        <div className="card">
          <div><b>Suggested action</b>: {action.action}</div>
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            {action.action === "send_email" && <button onClick={triggerEmail}>Confirm Email</button>}
            {action.action === "initiate_call" && <button onClick={triggerCall}>Confirm Call</button>}
          </div>
        </div>
      )}

      {callStatus && <div className="card"><b>Call Status:</b> {callStatus.status} {callStatus.duration ? `(${callStatus.duration} min)` : ""}</div>}

      <div style={{ display: "flex", gap: 8 }}>
        <input style={{ flex: 1 }} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask Filli..." onKeyDown={(e) => e.key === "Enter" && send()} />
        <button onClick={() => send()}>Send</button>
      </div>
    </div>
  );
}
