import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import useWebSocket from "../hooks/useWebSocket";
import { syncJobs, getLocalJobs, flushPendingActions, type Job } from "../services/sync";

const WS_URL = "ws://localhost:8000/ws";

export default function Dashboard() {
  const navigate = useNavigate();
  const { connected, lastEvent, subscribe } = useWebSocket(WS_URL);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [eventLog, setEventLog] = useState<string[]>([]);

  const pending = jobs.filter((j) => j.status === "planned" || j.status === "qa_pending" || j.status === "awaiting_approval").length;
  const inProgress = jobs.filter((j) => j.status === "executing").length;
  const inQA = jobs.filter((j) => j.status === "qa").length;
  const deployed = jobs.filter((j) => j.status === "deployed").length;

  const loadJobs = useCallback(async () => {
    setSyncing(true);
    const local = await getLocalJobs();
    setJobs(local);
    const remote = await syncJobs();
    if (remote.length > 0) setJobs(remote);
    await flushPendingActions();
    setSyncing(false);
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (!connected) return;
    const unsub1 = subscribe("JobStateChanged", (e) => {
      setJobs((prev) =>
        prev.map((j) =>
          j.id === e.job_id
            ? { ...j, status: (e.payload.new_status as string) || j.status, updatedAt: e.timestamp || j.updatedAt }
            : j
        )
      );
      setEventLog((prev) => [`${e.event_type}: ${e.job_id.slice(0, 8)} → ${e.payload.new_status}`, ...prev.slice(0, 9)]);
    });

    const unsub2 = subscribe("DiffReadyForApproval", (e) => {
      setEventLog((prev) => [`${e.event_type}: ${e.job_id.slice(0, 8)} - ${e.payload.summary}`, ...prev.slice(0, 9)]);
    });

    return () => { unsub1(); unsub2(); };
  }, [connected, subscribe]);

  useEffect(() => {
    if (lastEvent) {
      loadJobs();
    }
  }, [lastEvent, loadJobs]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Dashboard</h2>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
          <span className="text-xs text-slate-500">{connected ? "Inti online" : "Reconnecting..."}</span>
        </div>
      </div>

      {syncing && (
        <div className="text-xs text-slate-500 text-center">Syncing...</div>
      )}

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
        <button
          onClick={() => navigate("/jobs")}
          className="w-full rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold py-3 px-4 transition-colors"
        >
          Ver Jobs ({jobs.length})
        </button>
        <button
          onClick={loadJobs}
          className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium py-2 px-4 transition-colors text-sm"
        >
          Refrescar
        </button>
      </div>
    </div>
  );
}
