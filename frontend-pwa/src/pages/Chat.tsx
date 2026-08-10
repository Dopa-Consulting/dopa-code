import { useState, useRef, useEffect, useCallback } from "react";
import useWebSocket from "../hooks/useWebSocket";

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;

function renderMd(text: string): string {
  // Sanitizacion: escapar cualquier HTML inyectable en el texto original
  let safe = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  // Headers (la regex captura texto ya escapado)
  let html = safe
    .replace(/^#### (.+)$/gm, "<h4 class='text-sm font-semibold text-slate-200 mt-3 mb-1'>$1</h4>")
    .replace(/^### (.+)$/gm, "<h3 class='text-base font-semibold text-slate-100 mt-3 mb-1'>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2 class='text-lg font-bold text-white mt-4 mb-2'>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1 class='text-xl font-bold text-amber-300 mt-4 mb-2'>$1</h1>")
    // Code blocks (contenido ya escapado)
    .replace(/```(\w*)\n([\s\S]*?)```/g, "<pre class='bg-slate-950 border border-slate-700 rounded p-2 my-1 overflow-x-auto text-xs'><code>$2</code></pre>")
    // Inline code
    .replace(/`([^`]+)`/g, "<code class='bg-slate-700 px-1 rounded text-xs text-cyan-300'>$1</code>")
    // Bold
    .replace(/\*\*(.+?)\*\*/g, "<strong class='text-white'>$1</strong>")
    // Italic
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // Strikethrough
    .replace(/~~(.+?)~~/g, "<del>$1</del>")
    // Links (sanitizar href: solo http/https)
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m: string, label: string, href: string) => {
      if (/^(https?:|\/|\.)/i.test(href)) {
        return `<a href='${href}' class='text-amber-400 underline' target='_blank' rel='noopener noreferrer'>${label}</a>`;
      }
      return label;
    })
    // Horizontal rules
    .replace(/^---$/gm, "<hr class='border-slate-700 my-2'>")
    // Unordered lists
    .replace(/^- (.+)$/gm, "<li class='text-slate-300 text-sm ml-4'>$1</li>")
    // Blockquotes (&gt; viene escapado del paso 1)
    .replace(/^&gt; (.+)$/gm, "<blockquote class='border-l-2 border-amber-500 pl-3 italic text-slate-400 text-sm my-2'>$1</blockquote>");

  // Tables: parse markdown tables into HTML
  html = html.replace(/(\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)+)/g, (match) => {
    const lines = match.trim().split("\n").filter(l => l.includes("|"));
    if (lines.length < 2) return match;
    const headerCells = lines[0].split("|").filter(c => c.trim());
    const bodyLines = lines.slice(2);
    let table = "<table class='w-full text-xs border-collapse my-2'><thead><tr class='bg-slate-800'>";
    for (const cell of headerCells) {
      table += `<th class='border border-slate-700 px-2 py-1 text-left text-slate-200'>${cell.trim()}</th>`;
    }
    table += "</tr></thead><tbody>";
    for (const line of bodyLines) {
      const cells = line.split("|").filter(c => c.trim());
      table += "<tr class='border-t border-slate-800'>";
      for (const cell of cells) {
        table += `<td class='border border-slate-700 px-2 py-1 text-slate-400'>${cell.trim()}</td>`;
      }
      table += "</tr>";
    }
    table += "</tbody></table>";
    return table;
  });

  return html.replace(/\n/g, "<br>");
}

interface Message {
  id: string;
  role: "intl" | "user" | "system";
  content: string;
  timestamp: string;
  jobId?: string;
  diff?: string;
  awaitingApproval?: boolean;
  kind?: "tool";
  tool?: string;
  arg?: string;
  thinking?: boolean;
  streaming?: boolean;
}

// Etiqueta amigable por herramienta para el stream de actividad.
const TOOL_META: Record<string, { icon: string; verb: string }> = {
  read_file: { icon: "📖", verb: "Leyendo" },
  write_file: { icon: "✍️", verb: "Escribiendo" },
  list_dir: { icon: "📂", verb: "Listando" },
  run_command: { icon: "⚡", verb: "Ejecutando" },
  git_diff: { icon: "🔀", verb: "git diff" },
  run_opencode: { icon: "🤖", verb: "OpenCode" },
  generate_image: { icon: "🖼️", verb: "Generando imagen" },
  recall_memory: { icon: "🧠", verb: "Recordando" },
};

function getWelcome(): Message {
  const ws = localStorage.getItem("dopa-workspace") || "default";
  const st = localStorage.getItem("dopa-session-title");
  return {
    id: "welcome", role: "intl" as const,
    content: st ? `**${st}**\nWorkspace: \`${ws}\`` : `**Dopa Code** - Inti\nWorkspace: \`${ws}\`\n\nEscribe \`Hola\` o una tarea como \`Crea landing page\` para empezar.`,
    timestamp: new Date().toISOString(),
  };
}

function loadMsgs(): Message[] {
  try { const s = localStorage.getItem("dopa-chat"); return s ? JSON.parse(s) : [getWelcome()]; } catch { return [getWelcome()]; }
}
function saveMsgs(msgs: Message[]) {
  try { localStorage.setItem("dopa-chat", JSON.stringify(msgs.slice(-50))); } catch {}
}

export default function Chat() {
  const { connected, subscribe, send } = useWebSocket(WS_URL);
  const [messages, setMessages] = useState<Message[]>(loadMsgs);
  const [input, setInput] = useState("");
  const [clickedJobs, setClickedJobs] = useState<Set<string>>(new Set());
  const [workspace, setWorkspace] = useState(() => localStorage.getItem("dopa-workspace") || "");
  const bottomRef = useRef<HTMLDivElement>(null);
  const toolRef = useRef<string | null>(null);
  const msgCountRef = useRef(0);

  // Al montar: si hay session_id, limpiar chat viejo y cargar historial
  useEffect(() => {
    const sid = localStorage.getItem("dopa-session-id");
    if (sid) {
      localStorage.removeItem("dopa-chat");
      setMessages([getWelcome()]);
      setClickedJobs(new Set());
      fetch(`/api/v1/sessions/${sid}/messages`)
        .then(r => r.json())
        .then(data => {
          if (data.messages?.length) {
            const loaded: Message[] = [getWelcome()];
            for (const m of data.messages) {
              loaded.push({
                id: crypto.randomUUID(),
                role: m.role === "user" ? "user" : "intl",
                content: m.content,
                timestamp: m.created_at || new Date().toISOString(),
              });
            }
            setMessages(loaded);
          }
        })
        .catch(() => {});
    }
  }, []);

  useEffect(() => {
    const isFirst = msgCountRef.current === 0;
    const isNew = messages.length > msgCountRef.current;
    msgCountRef.current = messages.length;
    if (isFirst) bottomRef.current?.scrollIntoView({ block: "end" });
    else if (isNew) bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    if (messages.length > 1) {
      saveMsgs(messages);
    }
  }, [messages]);

  useEffect(() => {
    if (!connected) return;
    const unsub = subscribe("*", (e: Record<string,unknown>) => {
      const et = e.event_type as string;

      // Stream de actividad: una tarjeta por herramienta con su resultado.
      // (Antes el resultado —step.delta— se tiraba y solo se veía "Ejecutando...".)
      if (et === "session_created") {
        const sid = (e.payload as Record<string,unknown>)?.session_id as string;
        if (sid) { localStorage.setItem("dopa-session-id", sid); }
        return;
      }
      if (et === "chat_history") {
        const historyMsgs = (e.payload as Record<string,unknown>)?.messages as Array<{role:string,content:string}> | undefined;
        if (historyMsgs && historyMsgs.length > 0 && messages.length <= 1) {
          const loaded: Message[] = [getWelcome()];
          for (const hm of historyMsgs) {
            loaded.push({
              id: crypto.randomUUID(),
              role: hm.role === "user" ? "user" : "intl",
              content: hm.content,
              timestamp: new Date().toISOString(),
            });
          }
          setMessages(loaded);
        }
        return;
      }
      if (et === "step.start" || et === "chat_response" || et === "error") {
        setMessages((prev) => prev.filter((m) => !m.thinking));
      }
      if (et === "loop.thinking") {
        const it = (e.payload as Record<string,unknown>)?.iteration as number || 0;
        const max = (e.payload as Record<string,unknown>)?.max as number || 20;
        setMessages((prev) => {
          if (prev.some((m) => m.thinking)) return prev.map((m) => m.thinking ? { ...m, content: `${it}/${max}` } : m);
          return [...prev, { id: crypto.randomUUID(), role: "intl", content: `${it}/${max}`, timestamp: new Date().toISOString(), thinking: true }];
        });
        return;
      }
      if (et === "stream.token") {
        const text = ((e.data || e.payload || {}) as Record<string,unknown>).text as string || "";
        setMessages((prev) => {
          const filtered = prev.filter((m) => !m.thinking);
          const last = filtered[filtered.length - 1];
          if (last && last.streaming) {
            return [...filtered.slice(0, -1), { ...last, content: last.content + text }];
          }
          return [...filtered, { id: crypto.randomUUID(), role: "intl", content: text, timestamp: new Date().toISOString(), streaming: true }];
        });
        return;
      }
      if (et === "step.start") {
        const d = (e.data || e.payload || {}) as Record<string,unknown>;
        const tool = (d.tool as string) || (d.step_type as string) || "";
        if (!tool) return;
        const args = (d.args || {}) as Record<string,unknown>;
        const arg = (args.path || args.command || args.task || args.prompt || "") as string;
        const mid = crypto.randomUUID();
        toolRef.current = mid;
        setMessages((prev) => [...prev, {
          id: mid, role: "system", kind: "tool", tool, arg: String(arg).slice(0, 200),
          content: "",
          timestamp: (e.timestamp as string) || new Date().toISOString(),
        }]);
        return;
      }
      if (et === "step.delta") {
        const d = (e.data || e.payload || {}) as Record<string,unknown>;
        let text = (d.text as string) || "";
        // El backend prefija "🔧 tool → resultado"; lo sacamos (el header ya dice la tool).
        text = text.replace(/^🔧\s+\S+\s+→\s+/, "");
        const tid = toolRef.current;
        if (text && tid) {
          setMessages((prev) => prev.map((m) =>
            m.id === tid ? { ...m, content: (m.content + (m.content ? "\n" : "") + text).slice(-4000) } : m));
        }
        return;
      }
      if (et === "step.stop") { toolRef.current = null; return; }
      if (["interaction.created","interaction.status_update","interaction.completed","done"].includes(et)) return;

      if (et === "chat_response") {
        const p = (e.payload || {}) as Record<string,unknown>;
        const jid = (p.job_id as string) || (e.job_id as string) || "";
        const content = (p.content as string) || "Sin respuesta";
        // El card con diff + approve/reject lo renderiza DiffReadyForApproval; acá
        // evitamos duplicar el texto "Propuse cambios".
        if (content.includes("Propuse cambios")) return;
        setMessages((prev) => {
          // Si hay un mensaje en streaming, finalizarlo en vez de duplicar
          const hasStreaming = prev.some((m) => m.streaming);
          if (hasStreaming) {
            return prev.map((m) => m.streaming ? { ...m, streaming: false, content: content || m.content } : m);
          }
          return [...prev, {
            id: crypto.randomUUID(), role: "intl",
            content,
            timestamp: (e.timestamp as string) || new Date().toISOString(),
            jobId: jid,
          }];
        });
        return;
      }
      if (et === "DiffReadyForApproval") {
        const p = (e.payload || {}) as Record<string,unknown>;
        const jid = (p.job_id as string) || (e.job_id as string) || "";
        const mid = crypto.randomUUID();
        setMessages((prev) => [...prev, {
          id: mid, role: "intl",
          content: `Propuse cambios (job #${jid.slice(0,8)}). Revisá el diff y aprobá o rechazá:`,
          timestamp: (e.timestamp as string) || new Date().toISOString(),
          jobId: jid, awaitingApproval: true, diff: "",
        }]);
        // Traer el diff REAL del backend y adjuntarlo al card (inline, como OpenCode).
        fetch(`/api/v1/jobs/${jid}/diffs`)
          .then((r) => r.json())
          .then((data) => {
            const dt = (data?.diffs?.[0]?.diff_text as string) || "";
            if (dt) setMessages((prev) => prev.map((m) => (m.id === mid ? { ...m, diff: dt } : m)));
          })
          .catch(() => {});
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
    const thinkingId = crypto.randomUUID();
    setMessages((prev) => [...prev, { id: thinkingId, role: "intl", content: "", timestamp: new Date().toISOString(), thinking: true }]);
    const chatHistory = messages.slice(-10).map(m => ({
      role: m.role === "user" ? "user" : "assistant",
      content: m.content
    }));
    const allowedDirs = JSON.parse(localStorage.getItem("dopa-dirs") || "[]");
    const sessionId = localStorage.getItem("dopa-session-id") || "";
    const currentWorkspace = workspace || localStorage.getItem("dopa-workspace") || "";
    send({ type: "chat", content: prompt, require_approval: requireApproval, history: chatHistory, workspace: currentWorkspace, allowed_dirs: allowedDirs, session_id: sessionId });
    setInput("");
  }, [input, send, subscribe, workspace, messages]);

  return (
    <div className="flex flex-col h-[calc(100dvh-120px)]">
      <div className="flex items-center justify-between mb-3">
        <button onClick={() => { setMessages([getWelcome()]); setClickedJobs(new Set()); localStorage.removeItem("dopa-chat"); localStorage.removeItem("dopa-session-id"); send({ type: "chat", content: "", new_session: true }); }}
          className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
          title="Nuevo chat">
          + Nuevo
        </button>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
          <span className="text-xs text-slate-500">{connected ? "online" : "reconectando..."}</span>
        </div>
      </div>

      <div className="mb-2 flex items-center gap-2">
        <input
          value={workspace}
          onChange={(e) => { setWorkspace(e.target.value); localStorage.setItem("dopa-workspace", e.target.value); }}
          placeholder="D:\proyectos\mi-repo"
          className="flex-1 rounded bg-slate-800 border border-slate-700 px-2 py-1 text-xs text-slate-400 font-mono placeholder-slate-600 focus:outline-none focus:border-amber-500/50"
        />
        <button onClick={() => {
          const ws = localStorage.getItem("dopa-workspace") || "";
          const p = prompt("Ruta completa del workspace:", ws || "D:\\proyectos\\mi-repo");
          if (p) { setWorkspace(p); localStorage.setItem("dopa-workspace", p); }
        }}
          className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
          title="Explorar carpetas">
          📁
        </button>
        <span className="text-xs text-slate-600">ws</span>
      </div>

      <DirsAdicionales />      <div className="flex-1 overflow-y-auto space-y-2">
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
            {m.thinking ? (
              <div className="flex items-center gap-2 text-sm text-amber-400 animate-pulse">
                <span className="w-2 h-2 bg-amber-400 rounded-full inline-block" style={{ animation: "pulse 1s infinite" }} />
                Inti esta pensando...
                {m.content && <span className="text-xs text-slate-600">{m.content}</span>}
              </div>
            ) : m.streaming ? (
              <div className="text-sm text-slate-300">{m.content}<span className="inline-block w-1.5 h-4 bg-amber-400 ml-0.5 animate-pulse align-middle" /></div>
            ) : m.kind === "tool" ? (
              <details className="text-xs">
                <summary className="cursor-pointer text-slate-400 hover:text-slate-200">
                  <span>{TOOL_META[m.tool || ""]?.icon || "🔧"}</span>{" "}
                  <span className="text-slate-300">{TOOL_META[m.tool || ""]?.verb || m.tool}</span>
                  {m.arg && <span className="font-mono text-cyan-300"> {m.arg}</span>}
                  {!m.content && <span className="text-slate-600"> …</span>}
                </summary>
                {m.content && (
                  <pre className="mt-1 bg-slate-950 border border-slate-800 rounded p-2 overflow-auto max-h-60 text-slate-400 whitespace-pre-wrap text-[11px]">{m.content}</pre>
                )}
              </details>
            ) : (
              <div className="text-sm text-slate-300 [&_strong]:text-amber-300 [&_code]:text-cyan-300 [&_pre]:my-2" dangerouslySetInnerHTML={{ __html: renderMd(m.content || "...") }} />
            )}

            {m.awaitingApproval && (
              <pre className="bg-slate-950 border border-slate-700 rounded p-2 my-2 overflow-auto text-xs max-h-80 leading-tight">
                {m.diff
                  ? m.diff.split("\n").map((line, i) => (
                      <div key={i} className={
                        line.startsWith("+") && !line.startsWith("+++") ? "text-emerald-400" :
                        line.startsWith("-") && !line.startsWith("---") ? "text-red-400" :
                        line.startsWith("@@") ? "text-cyan-400" : "text-slate-500"
                      }>{line || " "}</div>
                    ))
                  : <span className="text-slate-600">Cargando diff…</span>}
              </pre>
            )}

            {m.jobId && m.role === "intl" && m.awaitingApproval && (
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
        <MicButton onTranscript={(text) => { setInput(text); }} />
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="crea landing page / Hola Inti / git status"
          autoComplete="off" autoCorrect="off" autoCapitalize="off" spellCheck="false"
          className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-4 py-2.5 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50" />
        <button onClick={handleSend} disabled={!input.trim()}
          className="rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold px-4 py-2.5 transition-colors text-sm">
          Send
        </button>
      </div>
    </div>
  );
}

function DirsAdicionales() {
  const [dirs, setDirs] = useState<string[]>(() => {
    try { return JSON.parse(localStorage.getItem("dopa-dirs") || "[]"); } catch { return []; }
  });
  const [dirInput, setDirInput] = useState("");
  const add = () => {
    if (dirInput && !dirs.includes(dirInput)) {
      const next = [...dirs, dirInput];
      setDirs(next);
      localStorage.setItem("dopa-dirs", JSON.stringify(next));
      setDirInput("");
    }
  };
  return (
    <details className="text-xs mb-2">
      <summary className="cursor-pointer text-slate-500 hover:text-slate-400">Dirs permitidos ({dirs.length})</summary>
      <div className="flex gap-1 mt-1">
        <input value={dirInput} onChange={e => setDirInput(e.target.value)} onKeyDown={e => e.key === "Enter" && add()}
          placeholder="D:\otra\carpeta"
          className="flex-1 rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-xs text-slate-400 font-mono placeholder-slate-600" />
        <button onClick={add} className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 hover:bg-slate-700">+</button>
      </div>
      {dirs.map(d => (
        <div key={d} className="flex items-center gap-1 mt-1">
          <span className="text-xs text-slate-500 font-mono truncate flex-1">{d}</span>
          <button onClick={() => { const n = dirs.filter(x => x !== d); setDirs(n); localStorage.setItem("dopa-dirs", JSON.stringify(n)); }} className="text-xs text-slate-600 hover:text-red-400">x</button>
        </div>
      ))}
    </details>
  );
}

function MicButton({ onTranscript }: { onTranscript: (t: string) => void }) {
  const [recording, setRecording] = useState(false);
  const [unsupported, setUnsupported] = useState(false);
  const [error, setError] = useState("");
  const mediaRef = useRef<MediaRecorder | null>(null);
  const srRef = useRef<unknown>(null);

  const tryWebSpeech = useCallback(() => {
    try {
      const SRClass = (window as unknown as Record<string,unknown>).SpeechRecognition
        || (window as unknown as Record<string,unknown>).webkitSpeechRecognition;
      if (!SRClass) { setUnsupported(true); setError("Voz no soportada en este navegador"); return; }
      const sr = new (SRClass as { new(): { lang: string; continuous: boolean; interimResults: boolean; onresult: ((e: Record<string,unknown>) => void) | null; onerror: (() => void) | null; onend: (() => void) | null; start: () => void; stop: () => void } })();
      sr.lang = "es-PE";
      sr.continuous = false;
      sr.interimResults = false;
      sr.onresult = (e: Record<string,unknown>) => {
        const r = e as unknown as { results: Array<Array<{ transcript: string }>> };
        if (r.results?.[0]?.[0]?.transcript) {
          onTranscript(r.results[0][0].transcript);
        }
      };
      sr.onerror = () => { setRecording(false); setError("Error de reconocimiento de voz"); };
      sr.onend = () => setRecording(false);
      sr.start();
      setRecording(true);
      srRef.current = sr;
      setError("");
    } catch {
      setUnsupported(true); setError("Voz no disponible");
    }
  }, [onTranscript]);

  const startRecording = useCallback(async () => {
    setError("");
    // Intentar MediaRecorder + backend STT
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => chunks.push(e.data);
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunks, { type: "audio/webm" });
        const form = new FormData();
        form.append("audio", blob, "recording.webm");
        try {
          const res = await fetch("/api/v1/voice/transcribe", { method: "POST", body: form });
          const data = await res.json();
          if (data.transcript) { onTranscript(data.transcript); return; }
          // STT devolvio vacio → mostrar error
          setError(data.error ? "API key no configurada" : "No se detecto voz");
        } catch {
          setError("Error de conexion al transcribir");
        }
      };
      recorder.start();
      mediaRef.current = recorder;
      setRecording(true);
    } catch {
      // getUserMedia fallo → ir directo a Web Speech
      tryWebSpeech();
    }
  }, [onTranscript, tryWebSpeech]);

  const stopRecording = useCallback(() => {
    setRecording(false);
    if (mediaRef.current && mediaRef.current.state !== "inactive") {
      try { mediaRef.current.stop(); } catch {}
    }
    if (srRef.current) {
      try { (srRef.current as { stop: () => void }).stop(); } catch {}
    }
  }, []);

  if (unsupported && !recording) return null;

  return (
    <div className="relative">
      <button
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onMouseLeave={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        className={`rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors ${
          recording ? "bg-red-500 text-white animate-pulse" : "bg-slate-700 hover:bg-slate-600 text-slate-300"
        }`}
        title="Mantener presionado para grabar (voz)"
      >
        {recording ? "... " : "\uD83C\uDF99"}
      </button>
      {error && <div className="absolute top-full left-0 mt-1 text-xs text-red-400 whitespace-nowrap bg-slate-900 px-2 py-0.5 rounded">{error}</div>}
    </div>
  );
}
