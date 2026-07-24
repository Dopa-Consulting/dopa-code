import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import useWebSocket from "../hooks/useWebSocket";
import { syncJobs, getLocalJobs, type Job } from "../services/sync";

const WS_URL = "ws://localhost:8000/ws";

const STATUS_COLORS: Record<string, string> = {
  planned: "bg-slate-700 text-slate-300",
  executing: "bg-blue-500/20 text-blue-400",
  qa_pending: "bg-purple-500/20 text-purple-400",
  qa_failed: "bg-red-500/20 text-red-400",
  awaiting_approval: "bg-amber-500/20 text-amber-400",
  approved: "bg-emerald-500/20 text-emerald-400",
  deploying: "bg-cyan-500/20 text-cyan-400",
  deployed: "bg-emerald-600/20 text-emerald-300",
  cancelled: "bg-red-800/20 text-red-300",
};

const STATUS_LABELS: Record<string, string> = {
  planned: "Planeado",
  executing: "Ejecutando",
  qa_pending: "QA pendiente",
  qa_failed: "QA fallo",
  awaiting_approval: "Esperando aprobacion",
  approved: "Aprobado",
  deploying: "Desplegando",
  deployed: "Desplegado",
  cancelled: "Cancelado",
};

export default function Jobs() {
  const navigate = useNavigate();
  const { subscribe } = useWebSocket(WS_URL);
  const [jobs, setJobs] = useState<Job[]>([]);

  const loadJobs = useCallback(async () => {
    const local = await getLocalJobs();
    if (local.length > 0) setJobs(local);
    const remote = await syncJobs();
    if (remote.length > 0) setJobs(remote);
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    const unsub = subscribe("JobStateChanged", (e) => {
      setJobs((prev) =>
        prev.map((j) =>
          j.id === e.job_id
            ? { ...j, status: (e.payload.new_status as string) || j.status }
            : j
        )
      );
    });
    return unsub;
  }, [subscribe]);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Jobs</h2>

      {jobs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-500">
          <p className="text-4xl mb-3">[ ]</p>
          <p className="text-sm">No hay jobs todavia</p>
          <p className="text-xs mt-1">Inti espera tus instrucciones desde la PC</p>
        </div>
      ) : (
        jobs.map((job) => (
          <div
            key={job.id}
            onClick={() => navigate(`/jobs/${job.id}/diff`)}
            className="rounded-lg bg-slate-900 border border-slate-800 p-4 active:bg-slate-800 transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between">
              <h3 className="font-medium flex-1">{job.title}</h3>
              <span className="text-xs text-slate-600 ml-2">{job.id.slice(0, 8)}</span>
            </div>
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[job.status] || "bg-slate-700 text-slate-300"}`}>
                {STATUS_LABELS[job.status] || job.status}
              </span>
              {job.profile && (
                <span className="text-xs text-slate-600">{job.profile}</span>
              )}
              {job.branchName && (
                <span className="text-xs text-slate-600">{job.branchName}</span>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
