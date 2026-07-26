import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import useWebSocket from "../hooks/useWebSocket";
import { syncJobs, getLocalJobs, flushPendingActions, type Job } from "../services/sync";

const WS_URL = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`;
const API_BASE = `${location.protocol}//${location.host}/api/v1`;

interface AgentSession {
  id: string;
  role: string;
  model: string;
  status: string;
  current_job_id: string | null;
  workspace_path: string;
}

const ROLE_ICONS: Record<string, string> = {
  architect: "P",
  builder: "B",
  reviewer: "R",
  deployer: "D",
  custom: "C",
};

const STATUS_COLORS: Record<string, string> = {
  idle: "bg-slate-600",
  running: "bg-emerald-400 animate-pulse",
  waiting: "bg-amber-400",
  completed: "bg-slate-500",
  error: "bg-red-400",
  disconnected: "bg-red-600",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { connected, lastEvent, subscribe } = useWebSocket(WS_URL);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [eventLog, setEventLog] = useState<string[]>([]);

  const pending = jobs.filter((j) => ["planned", "qa_pending", "awaiting_approval"].includes(j.status)).length;
  const inProgress = jobs.filter((j) => j.status === "executing").length;
  const inQA = jobs.filter((j) => ["qa", "qa_pending"].includes(j.status)).length;
  const deployed = jobs.filter((j) => j.status === "deployed").length;

  const loadAll = useCallback(async () => {
    setSyncing(true);
    const [local, _] = await Promise.all([getLocalJobs(), syncJobs()]);
    if (local.length > 0) setJobs(local);
    const remote = await syncJobs();
    if (remote.length > 0) setJobs(remote);
    await flushPendingActions();

    try {
      const res = await fetch(`${API_BASE}/sessions/`);
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch { /* offline */ }

    setSyncing(false);
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  useEffect(() => {
    if (!connected) return;
    const unsub1 = subscribe("JobStateChanged", (e) => {
      setJobs((prev) => prev.map((j) => j.id === e.job_id ? { ...j, status: e.payload.new_status as string || j.status, updatedAt: e.timestamp || j.updatedAt } : j));
      setEventLog((prev) => [`${e.event_type}: ${e.job_id.slice(0, 8)} -> ${e.payload.new_status}`, ...prev.slice(0, 9)]);
    });
    const unsub2 = subscribe("DiffReadyForApproval", (e) => {
      setEventLog((prev) => [`${e.event_type}: ${e.job_id.slice(0, 8)} - ${e.payload.summary}`, ...prev.slice(0, 9)]);
    });
    return () => { unsub1(); unsub2(); };
  }, [connected, subscribe]);

  useEffect(() => { if (lastEvent) loadAll(); }, [lastEvent, loadAll]);

  const createSession = async (role: string) => {
    try {
      await fetch(`${API_BASE}/sessions/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role }),
      });
      loadAll();
    } catch { /* offline */ }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Dashboard</h2>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
          <span className="text-xs text-slate-500">{connected ? "Inti online" : "Reconnecting..."}</span>
        </div>
      </div>

      {syncing && <div className="text-xs text-slate-500 text-center">Syncing...</div>}

      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Pendientes", value: pending, color: "text-amber-400" },
          { label: "En progreso", value: inProgress, color: "text-blue-400" },
          { label: "QA", value: inQA, color: "text-purple-400" },
          { label: "Desplegados", value: deployed, color: "text-emerald-400" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-lg bg-slate-900 border border-slate-800 p-3">
            <p className={`text-xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-3">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-slate-300">Agentes activos ({sessions.length})</p>
          <div className="flex gap-1">
            {["architect", "builder", "reviewer"].map((role) => (
              <button key={role} onClick={() => createSession(role)}
                className="text-xs px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
                title={`Crear sesion ${role}`}>
                + {role}
              </button>
            ))}
          </div>
        </div>

        {sessions.length === 0 ? (
          <p className="text-xs text-slate-600">No hay sesiones activas. Crea una para empezar.</p>
        ) : (
          <div className="space-y-2">
            {sessions.map((s) => (
              <div key={s.id} onClick={() => navigate(`/jobs/${s.current_job_id}/diff`)} className="flex items-center gap-3 p-2 rounded bg-slate-800/50 hover:bg-slate-800 cursor-pointer transition-colors">
                <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[s.status] || "bg-slate-600"}`} />
                <span className="text-xs font-mono text-amber-400 w-6 text-center">{ROLE_ICONS[s.role] || "?"}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-300 truncate">{s.id}</p>
                  <p className="text-xs text-slate-500">{s.role} - {s.model?.split("/").pop()}</p>
                </div>
                <span className="text-xs text-slate-600">{s.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {eventLog.length > 0 && (
        <div className="rounded-lg bg-slate-900 border border-slate-800 p-3">
          <p className="text-xs text-slate-500 mb-2">Eventos en vivo</p>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {eventLog.map((e, i) => (
              <p key={i} className="text-xs font-mono text-slate-400">{e}</p>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <button onClick={() => navigate("/jobs")} className="w-full rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold py-3 px-4 transition-colors">
          Ver Jobs ({jobs.length})
        </button>
        <button onClick={loadAll} className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-2 px-4 transition-colors text-sm">
          Refrescar
        </button>
      </div>
    </div>
  );
}
