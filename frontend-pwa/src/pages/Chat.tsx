import { useState, useRef, useEffect, useCallback } from "react";
import useWebSocket from "../hooks/useWebSocket";
import ChatMessage from "../components/ChatMessage";
import { approveJob, rejectJob, syncJobs } from "../services/sync";

const WS_URL = "ws://localhost:8000/ws";

interface Message {
  id: string;
  role: "intl" | "user" | "architect" | "builder" | "reviewer" | "system";
  content: string;
  timestamp: string;
  jobId?: string;
  actions?: Array<{ id: string; label: string; variant: "approve" | "reject" | "deploy" | "merge" | "default" }>;
}

export default function Chat() {
  const { connected, subscribe, send } = useWebSocket(WS_URL);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "intl",
      content: "Bienvenido a Dopa Code. Soy **Inti**, tu agente andino de orquestacion.\n\nPuedo ayudarte con:\n\n| Comando | Descripcion |\n|---------|-------------|\n| `crea un job` | Planificar una tarea |\n| `ejecuta el job` | Ejecutar cambios |\n| `revisa el diff` | Revisar codigo |\n| `deploy` | Desplegar cambios |\n\nEscribe un comando o crea una sesion de agente para empezar.",
      timestamp: new Date().toISOString(),
      actions: [
        { id: "create_session_builder", label: "Nueva sesion Builder", variant: "default" },
        { id: "create_session_architect", label: "Nueva sesion Architect", variant: "default" },
        { id: "view_jobs", label: "Ver Jobs", variant: "default" },
      ],
    },
  ]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  useEffect(() => {
    if (!connected) return;
    const unsub = subscribe("*", (e) => {
      const ts = e.timestamp || new Date().toISOString();
      const jobId = e.job_id;
      let content = "";
      let role: Message["role"] = "system";
      let actions: Message["actions"] = undefined;

    if (e.event_type === "chat_response") {
      const payload = e.payload as Record<string,unknown>;
      content = (payload.content as string) || "Sin respuesta";
      if (payload.usage) {
        const usage = payload.usage as Record<string,number>;
        content += `\n\n*Tokens: ${usage.total_tokens || "?"} | Modelo: ${payload.model || "openrouter"}*`;
      }
      role = "intl";
    } else if (e.event_type === "step.delta") {
      // Streaming text accumulation - handled by handleSend
      return;
    } else {
      switch (e.event_type) {
        case "JobStateChanged":
          content = `Job **#${jobId.slice(0, 8)}** cambio de estado:\n\n\`${e.payload.previous_status}\` → **${e.payload.new_status}**`;
          role = "system";
          break;
        case "DiffReadyForApproval":
          content = `**Diff listo para revision**\n\n${e.payload.summary}\n\nArchivos cambiados: **${e.payload.files_count || "?"}**`;
          role = "builder";
          actions = [
            { id: "approve", label: "Approve", variant: "approve" },
            { id: "reject", label: "Reject", variant: "reject" },
          ];
          break;
        case "ArchitectPlanGenerated":
          content = `**Plan generado**\n\nSe crearon **${e.payload.steps_count}** pasos para modificar **${e.payload.estimated_files}** archivos.`;
          role = "architect";
          break;
        case "TestsFinished":
          content = e.payload.passed
            ? `**Tests pasaron** correctamente (${e.payload.total} tests, 0 fallos)`
            : `**Tests fallaron** (${e.payload.failed} de ${e.payload.total} fallaron)`;
          role = "builder";
          break;
        case "CiStatusUpdated":
          content = `**CI ${e.payload.status}**\n\nProveedor: ${e.payload.provider}`;
          role = "system";
          if (e.payload.status === "passed") {
            actions = [
              { id: "merge", label: "Merge PR", variant: "merge" },
              { id: "deploy", label: "Deploy", variant: "deploy" },
            ];
          }
          break;
        case "QaReviewCompleted":
          content = e.payload.passed
            ? `**QA aprobado** con score ${e.payload.score}`
            : `**QA rechazado** con score ${e.payload.score}`;
          role = "reviewer";
          break;
        default:
          content = `Evento: ${e.event_type}`;
      }
    }

    setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role, content, timestamp: ts, jobId, actions },
      ]);
    });
    return unsub;
  }, [connected, subscribe]);

  const handleSend = useCallback(async () => {
    if (!input.trim()) return;

    const isStreamCmd = input.startsWith("/stream ") || input.startsWith("/gemini ");
    const prompt = isStreamCmd ? input.replace(/^\/(stream|gemini)\s*/, "") : input;

    const msg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
      timestamp: new Date().toISOString(),
    };

    if (isStreamCmd && connected) {
      const streamMsg: Message = {
        id: crypto.randomUUID(),
        role: "intl",
        content: "",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, msg, streamMsg]);
      setInput("");

      send({ type: "chat", content: prompt, stream: true, model: "gemini-2.5-flash" });
      const unsub = subscribe("*", (e) => {
        const d = (e as Record<string,unknown>).data as Record<string,string> || e.payload as Record<string,string>;
        const text = d?.text || "";
        if (e.event_type === "step.delta" && text) {
          setMessages((prev) => prev.map((m) =>
            m.id === streamMsg.id ? { ...m, content: m.content + text } : m
          ));
        } else if (e.event_type === "interaction.completed" || e.event_type === "done") {
          unsub();
        }
      });
      return;
    }

    setMessages((prev) => [...prev, msg]);
    send({ type: "chat", content: prompt });
    setInput("");

    const lower = prompt.toLowerCase();
    if (lower.includes("crea") && lower.includes("sesion")) {
      const role = lower.includes("builder") || lower.includes("build") ? "builder" : "architect";
      try {
        await fetch("http://localhost:8000/api/v1/sessions/", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role }),
        });
      } catch {}
    }
    if (lower.includes("job") || lower.includes("lista")) await syncJobs();
  }, [input, send, connected, subscribe]);

  const handleAction = useCallback(async (action: string, jobId: string) => {
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: `Accion: **${action}**`, timestamp: new Date().toISOString(), jobId },
    ]);
    if (action === "approve") await approveJob(jobId);
    else if (action === "reject") await rejectJob(jobId);
    else if (action === "view_jobs") window.location.hash = "/jobs";
    else if (action === "create_session_builder" || action === "create_session_architect") {
      const role = action === "create_session_builder" ? "builder" : "architect";
      try {
        const res = await fetch("http://localhost:8000/api/v1/sessions/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role }),
        });
        const data = await res.json();
        if (data.session_id) {
          setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "system", content: `Sesion **${role}** creada: \`${data.session_id}\``, timestamp: new Date().toISOString() },
          ]);
        }
      } catch {}
    }
  }, []);

  return (
    <div className="flex flex-col h-[calc(100dvh-120px)]">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold">Chat</h2>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
          <span className="text-xs text-slate-500">{connected ? "Inti online" : "Reconnecting..."}</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto pr-1 space-y-1">
        {messages.map((msg) => (
          <ChatMessage
            key={msg.id}
            role={msg.role}
            content={msg.content}
            timestamp={msg.timestamp?.slice(11, 19)}
            jobId={msg.jobId}
            actions={msg.actions}
            onAction={handleAction}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="flex gap-2 mt-3">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Escribe un comando... (Inti, crea una sesion builder)"
          className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-4 py-2.5 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim()}
          className="rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:bg-slate-700 text-slate-950 font-semibold px-4 py-2.5 transition-colors text-sm"
        >
          Send
        </button>
      </div>
    </div>
  );
}
