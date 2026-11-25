import React, { useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const configuredApiBase = (import.meta.env.VITE_API_BASE_URL || "").trim();
const API_BASE = (configuredApiBase || (import.meta.env.DEV ? "http://localhost:8000" : "")).replace(/\/$/, "");

function makeSessionId() {
  return `s-${crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`}`;
}

function App() {
  const [sessionId] = useState(makeSessionId);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [message, setMessage] = useState("");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  async function sendMessage(event) {
    event?.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || loading) return;
    setItems((current) => [...current, { role: "user", content: trimmed }]);
    setMessage("");
    if (!API_BASE) {
      setItems((current) => [...current, { role: "error", content: "Chat backend is not configured. Set VITE_API_BASE_URL to enable chat." }]);
      return;
    }
    setLoading(true);
    try {
      const body = { session_id: sessionId, message: trimmed };
      if (systemPrompt.trim()) body.system_prompt = systemPrompt.trim();
      const response = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "The request could not be completed.");
      setItems((current) => [...current, { role: "assistant", content: data.reply, metadata: data.metadata }]);
    } catch (error) {
      setItems((current) => [...current, { role: "error", content: error.message }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  return (
    <main className="app-shell">
      <section className="chat-card">
        <header><div><p className="eyebrow">LYFTR AI</p><h1>Chat workspace</h1></div><span className={API_BASE ? "status" : "status offline"}><i /> {API_BASE ? "Backend URL set" : "Chat unavailable"}</span></header>
        <label className="prompt-field">System prompt
          <input data-testid="system-prompt-input" value={systemPrompt} onChange={(event) => setSystemPrompt(event.target.value)} placeholder="Optional instructions for this session" />
        </label>
        <div className="conversation" aria-live="polite">
          {!API_BASE && <div className="error-message" role="status">The frontend is published without a backend URL. Chat will work after VITE_API_BASE_URL is configured.</div>}
          {items.length === 0 && <div className="empty-state"><div className="empty-mark">AI</div><p>Start a conversation</p></div>}
          {items.map((item, index) => item.role === "assistant" ? (
            <article className="message assistant" data-testid="assistant-message" key={index}>
              <div className="avatar">AI</div>
              <div className="bubble">
                <p>{item.content}</p>
                <div className="metadata">
                  <span data-testid="meta-source"><b>Source:</b> {item.metadata.resolution_source}</span>
                  <span data-testid="meta-model"><b>Model:</b> {item.metadata.model}</span>
                  <span data-testid="meta-latency"><b>Latency:</b> {item.metadata.latency_ms} ms</span>
                  <span data-testid="meta-input-tokens"><b>Input:</b> {item.metadata.input_tokens}</span>
                  <span data-testid="meta-output-tokens"><b>Output:</b> {item.metadata.output_tokens}</span>
                </div>
              </div>
            </article>
          ) : item.role === "error" ? (
            <div className="error-message" key={index}>{item.content}</div>
          ) : (
            <article className="message user" key={index}><div className="bubble">{item.content}</div></article>
          ))}
          {loading && <div className="loading">Thinking…</div>}
        </div>
        <form className="composer" onSubmit={sendMessage}>
          <textarea ref={inputRef} data-testid="chat-input" value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) sendMessage(event); }} placeholder="Message the assistant..." rows="2" />
          <button data-testid="send-button" type="submit" disabled={loading || !message.trim()}>Send</button>
        </form>
      </section>
    </main>
  );
}
createRoot(document.getElementById("root")).render(<App />);
