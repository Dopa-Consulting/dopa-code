import { useState, useRef, useEffect, useCallback } from "react";
import useWebSocket from "../hooks/useWebSocket";

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;

function renderMd(text: string): string {
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre class='bg-slate-950 border border-slate-700 rounded p-2 my-1 overflow-x-auto text-xs'><code>$2</code></pre>")
    .replace(/`([^`]+)`/g, "<code class='bg-slate-700 px-1 rounded text-xs'>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong class='text-white'>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/~~(.+?)~~/g, "<del>$1</del>")
    .replace(/\n/g, "<br>");
}

interface Message {
  id: string;
  role: "intl" | "user" | "system";
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
  try { const s = localStorage.getItem("dopa-chat"); return s ? JSON.parse(s) : [WELCOME]; } catch { return [WELCOME]; }
}
function saveMsgs(msgs: Message[]) {
  try { localStorage.setItem("dopa-chat", JSON.stringify(msgs.slice(-50))); } catch {}
}

export default function Chat() {
  const { connected, subscribe, send } = useWebSocket(WS_URL);
  const [messages, setMessages] = useState<Message[]>(loadMsgs);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [clickedJobs, setClickedJobs] = useState<Set<string>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    if (messages.length > 1) {
      saveMsgs(messages);
    }
  }, [messages]);

  useEffect(() => {
    if (!connected) return;
    const unsub = subscribe("*", (e: Record<string,unknown>) => {
      const et = e.event_type as string;

      // Mostrar herramientas ejecutandose (antes estaban bloqueadas - el usuario no veia nada)
      if (et === "step.start") {
        const d = (e.data || e.payload || {}) as Record<string,unknown>;
        const tool = (d.tool as string) || (d.step_type as string) || "";
        if (tool) {
          setMessages((prev) => [...prev, {
            id: crypto.randomUUID(), role: "system",
            content: `Ejecutando: ${tool}...`,
            timestamp: (e.timestamp as string) || new Date().toISOString(),
          }]);
        }
        return;
      }
      if (et === "step.delta" || et === "step.stop") return;
      if (["interaction.created","interaction.status_update","interaction.completed","done"].includes(et)) return;

      if (et === "chat_response") {
        setThinking(false);
        const p = (e.payload || {}) as Record<string,unknown>;
        const jid = (p.job_id as string) || (e.job_id as string) || "";
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(), role: "intl",
          content: (p.content as string) || "Sin respuesta",
          timestamp: (e.timestamp as string) || new Date().toISOString(),
          jobId: jid,
        }]);
        return;
      }
      if (et === "JobStateChanged") {
        const p = e.payload as Record<string,unknown>;
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(), role: "system",
          content: `Job #${(e.job_id as string||"").slice(0,8)}: ${p.previous_status} → ${p.new_status}`,
          timestamp: (e.timestamp as string) || new Date().toISOString(),
          jobId: e.job_id as string,
        }]);
        return;
      }
    });
    return unsub;
  }, [connected, subscribe]);

  const copy = (text: string) => { navigator.clipboard.writeText(text).catch(() => {}); };

  const handleApprove = async (jobId: string) => {
    if (clickedJobs.has(jobId)) return;
    setClickedJobs((prev) => new Set(prev).add(jobId));
    const r = await fetch(`/api/v1/jobs/${jobId}/approve`, { method: "POST" });
    if (r.ok) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", content: `Job #${jobId.slice(0,8)} aprobado.`, timestamp: new Date().toISOString(), jobId }]);
    }
  };

  const handleReject = async (jobId: string) => {
    if (clickedJobs.has(jobId)) return;
    setClickedJobs((prev) => new Set(prev).add(jobId));
    const r = await fetch(`/api/v1/jobs/${jobId}/reject`, { method: "POST" });
    if (r.ok) {
      setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "system", content: `Job #${jobId.slice(0,8)} rechazado.`, timestamp: new Date().toISOString(), jobId }]);
    }
  };
  const handleSend = useCallback(async () => {
    if (!input.trim()) return;
    const isStream = input.startsWith("/stream ");
    const prompt = isStream ? input.slice(8) : input;

    // Task commands need approval checkpoint
    const taskVerbs = ["crea", "hace", "haz", "genera", "construye", "diseña", "implementa",
                       "desarrolla", "codifica", "modifica", "refactoriza", "corrige", "arregla"];
    const first = prompt.split(" ")[0].toLowerCase();
    const requireApproval = taskVerbs.includes(first);

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
    setThinking(true);
    const chatHistory = messages.slice(-10).map(m => ({
      role: m.role === "user" ? "user" : "assistant",
      content: m.content
    }));
    send({ type: "chat", content: prompt, require_approval: requireApproval, history: chatHistory });
    setInput("");
  }, [input, send, subscribe]);

  return (
    <div className="flex flex-col h-[calc(100dvh-120px)]">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Chat</h2>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
          <span className="text-xs text-slate-500">{connected ? "online" : "reconectando..."}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        {messages.map((m) => (
          <div key={m.id} className={`border-l-2 rounded-r-lg p-3 ${
            m.role === "intl" ? "border-amber-500 bg-amber-500/5" :
            m.role === "user" ? "border-blue-500 bg-blue-500/5" :
            "border-slate-600 bg-slate-800/30"
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span className={`text-xs font-medium ${m.role === "intl" ? "text-amber-400" : m.role === "user" ? "text-blue-400" : "text-slate-400"}`}>
                {m.role === "intl" ? "Inti" : m.role === "user" ? "Tu" : "Sistema"}
              </span>
              {m.jobId && <span className="text-xs text-slate-600">#{m.jobId.slice(0,8)}</span>}
              <span className="text-xs text-slate-600 ml-auto">{m.timestamp.slice(11, 19)}</span>
              <button onClick={() => copy(m.content)}
                className="text-xs text-slate-600 hover:text-slate-400 px-1.5 py-0.5 rounded hover:bg-slate-800 transition-colors"
                title="Copiar">
                📋
              </button>
            </div>
            <div className="text-sm text-slate-300 [&_strong]:text-amber-300 [&_code]:text-cyan-300 [&_pre]:my-2" dangerouslySetInnerHTML={{ __html: renderMd(m.content || "...") }} />

            {m.jobId && m.role === "intl" && (
              <div className="flex gap-2 mt-3">
                <button onClick={() => handleApprove(m.jobId!)}
                  disabled={clickedJobs.has(m.jobId)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900 disabled:text-emerald-500 text-white transition-colors">
                  {clickedJobs.has(m.jobId) ? "Aprobado" : "Approve"}
                </button>
                <button onClick={() => handleReject(m.jobId!)}
                  disabled={clickedJobs.has(m.jobId)}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-600 hover:bg-red-500 disabled:bg-red-900 disabled:text-red-500 text-white transition-colors">
                  {clickedJobs.has(m.jobId) ? "Rechazado" : "Reject"}
                </button>
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 mt-3">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="crea landing page / Hola Inti / git status"
          className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-4 py-2.5 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50" />
        <button onClick={handleSend} disabled={!input.trim()}
          className="rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold px-4 py-2.5 transition-colors text-sm">
          Send
        </button>
      </div>
      {thinking && (
        <div className="text-xs text-slate-500 text-center mt-1 animate-pulse">Inti esta pensando...</div>
      )}
    </div>
  );
}
