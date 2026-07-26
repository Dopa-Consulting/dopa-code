import { useState, useRef, useEffect, useCallback } from "react";
import useWebSocket from "../hooks/useWebSocket";
import { syncJobs } from "../services/sync";

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;

interface Message {
  id: string;
  role: "intl" | "user" | "architect" | "builder" | "reviewer" | "system";
  content: string;
  timestamp: string;
  jobId?: string;
}

const WELCOME: Message = {
  id: "welcome", role: "intl",
  content: "**Dopa Code** - Inti\nWorkspace: `D:\\Dopa\\01_Desarrollo\\dopa-code\\backend-inti`\n\n`crea landing page` `lee archivo` `lista archivos` `git status` `/stream X`",
  timestamp: new Date().toISOString(),
};

function loadMsgs(): Message[] {
  try { const s = sessionStorage.getItem("dopa-chat"); return s ? JSON.parse(s) : [WELCOME]; } catch { return [WELCOME]; }
}
function saveMsgs(msgs: Message[]) {
  try { sessionStorage.setItem("dopa-chat", JSON.stringify(msgs.slice(-50))); } catch {}
}

export default function Chat() {
  const { connected, subscribe, send } = useWebSocket(WS_URL);
  const [messages, setMessages] = useState<Message[]>(loadMsgs);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = bottomRef.current;
    if (!el) return;
    const parent = el.parentElement;
    if (parent) {
      const nearBottom = parent.scrollHeight - parent.scrollTop - parent.clientHeight < 100;
      if (nearBottom || messages.length <= 2) el.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);
  useEffect(() => { saveMsgs(messages); }, [messages]);

  useEffect(() => {
    if (!connected) return;
    const unsub = subscribe("*", (e: Record<string,unknown>) => {
      const et = e.event_type as string;
      if (["step.delta","step.start","step.stop","interaction.created","interaction.status_update","interaction.completed","done"].includes(et)) return;
      if (et === "chat_response") {
        const p = e.payload as Record<string,unknown>;
        setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "intl", content: (p.content as string) || "Sin respuesta", timestamp: new Date().toISOString() }]);
        return;
      }
      if (et === "JobStateChanged") {
        const p = e.payload as Record<string,unknown>;
        setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", content: `Job #${(e.job_id as string).slice(0,8)}: ${p.previous_status} → ${p.new_status}`, timestamp: new Date().toISOString(), jobId: e.job_id as string }]);
      }
    });
    return unsub;
  }, [connected, subscribe]);

  const handleSend = useCallback(async () => {
    if (!input.trim()) return;
    const isStream = input.startsWith("/stream ");
    const prompt = isStream ? input.slice(8) : input;
    const msg: Message = { id: crypto.randomUUID(), role: "user", content: input, timestamp: new Date().toISOString() };

    if (isStream) {
      const streamMsg: Message = { id: crypto.randomUUID(), role: "intl", content: "", timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, msg, streamMsg]);
      setInput("");
      send({ type: "chat", content: prompt, stream: true, model: "gemini-2.5-flash" });
      const unsub = subscribe("*", (e: Record<string,unknown>) => {
        const d = (e as Record<string,unknown>).data as Record<string,string> || (e.payload as Record<string,string>);
        const text = d?.text || "";
        if (e.event_type === "step.delta" && text) {
          setMessages((prev) => prev.map((m) => m.id === streamMsg.id ? { ...m, content: m.content + text } : m));
        } else if (e.event_type === "interaction.completed" || e.event_type === "done") {
          unsub();
        }
      });
      return;
    }

    setMessages((prev) => [...prev, msg]);
    send({ type: "chat", content: prompt });
    setInput("");
    if (prompt.includes("crea sesion")) {
      const role = prompt.includes("builder") ? "builder" : "architect";
      try { await fetch("/api/v1/sessions/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ role }) }); } catch {}
    }
    if (prompt.includes("job") || prompt.includes("lista")) await syncJobs();
  }, [input, send, subscribe]);

  return (
    <div className="flex flex-col h-[calc(100dvh-120px)]">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Chat</h2>
        <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
      </div>
      <div className="flex-1 overflow-y-auto space-y-2">
        {messages.map((m) => (
          <div key={m.id} className={`border-l-2 rounded-r-lg p-2 mb-2 ${m.role === "intl" ? "border-amber-500 bg-amber-500/5" : m.role === "user" ? "border-blue-500 bg-blue-500/5" : "border-slate-600 bg-slate-800/30"}`}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-slate-400">{m.role === "intl" ? "Inti" : m.role === "user" ? "Tu" : "Sistema"}</span>
              <span className="text-xs text-slate-600 ml-auto">{m.timestamp.slice(11, 19)}</span>
            </div>
            <div className="text-sm text-slate-300 whitespace-pre-wrap">{m.content || "..."}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-2 mt-3">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Hola Inti..."
          className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-4 py-2.5 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50" />
        <button onClick={handleSend} disabled={!input.trim()}
          className="rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold px-4 py-2.5 transition-colors text-sm">
          Send
        </button>
      </div>
    </div>
  );
}
