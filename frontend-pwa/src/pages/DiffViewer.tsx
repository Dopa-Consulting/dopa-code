import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { syncDiffs, getLocalDiffs, approveJob, rejectJob, type Diff } from "../services/sync";
import useDeploy from "../hooks/useDeploy";

const STATUS_COLORS: Record<string, string> = {
  generated: "bg-blue-500/20 text-blue-400",
  qa_approved: "bg-emerald-500/20 text-emerald-400",
  qa_failed: "bg-red-500/20 text-red-400",
  awaiting_approval: "bg-amber-500/20 text-amber-400",
  planned: "bg-slate-500/20 text-slate-400",
  executing: "bg-blue-500/20 text-blue-400",
  approved: "bg-emerald-600/20 text-emerald-300",
  cancelled: "bg-red-800/20 text-red-300",
};

const CI_COLORS: Record<string, string> = {
  pending: "bg-slate-500 text-slate-300",
  running: "bg-amber-500/20 text-amber-400",
  passed: "bg-emerald-500/20 text-emerald-400",
  failed: "bg-red-500/20 text-red-400",
};

export default function DiffViewer() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [diffs, setDiffs] = useState<Diff[]>([]);
  const [jobInfo, setJobInfo] = useState<Record<string,unknown>>({});
  const [actionStatus, setActionStatus] = useState<"idle" | "sending" | "sent" | "offline">("idle");
  const { ciStatus, deploy, merge, setEasyPanelToken } = useDeploy(jobId || "");

  useEffect(() => {
    if (!jobId) return;
    (async () => {
      const local = await getLocalDiffs(jobId);
      if (local.length > 0) setDiffs(local);
      const remote = await syncDiffs(jobId);
      if (remote.length > 0) setDiffs(remote);
      try {
        const r = await fetch(`/api/v1/jobs/${jobId}`);
        if (r.ok) setJobInfo(await r.json());
      } catch {}
    })();
  }, [jobId]);

  const handleApprove = async () => {
    if (!jobId) return;
    setActionStatus("sending");
    const ok = await approveJob(jobId);
    setActionStatus(ok ? "sent" : "offline");
  };

  const handleReject = async () => {
    if (!jobId) return;
    setActionStatus("sending");
    const ok = await rejectJob(jobId);
    setActionStatus(ok ? "sent" : "offline");
  };

  const renderDiffText = (text: string) => {
    return text.split("\n").map((line, i) => {
      let cls = "text-slate-400";
      if (line.startsWith("+") && !line.startsWith("+++")) cls = "text-emerald-400 bg-emerald-400/5";
      else if (line.startsWith("-") && !line.startsWith("---")) cls = "text-red-400 bg-red-400/5";
      else if (line.startsWith("@@")) cls = "text-cyan-400";
      else if (line.startsWith("diff --git")) cls = "text-amber-400 font-semibold";
      else if (line.startsWith("---") || line.startsWith("+++")) cls = "text-amber-300";
      return (
        <div key={i} className={`font-mono text-xs leading-5 px-2 ${cls}`}>
          <span className="select-none text-slate-700 mr-3 w-8 inline-block text-right">{i + 1}</span>
          {line}
        </div>
      );
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Job #{jobId?.slice(0, 8)}</h2>
        <button onClick={() => navigate("/jobs")} className="text-xs text-slate-500">← Jobs</button>
      </div>

      {jobInfo && Object.keys(jobInfo).length > 0 && (
        <div className="rounded-lg bg-slate-900 border border-slate-800 p-3 space-y-1">
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[jobInfo.status as string] || "bg-slate-700"}`}>
              {(jobInfo.status as string) || "unknown"}
            </span>
            <span className="text-sm font-medium text-slate-300">{jobInfo.title as string}</span>
          </div>
          {jobInfo.profile && <p className="text-xs text-slate-500">Perfil: {String(jobInfo.profile)}</p>}
          {jobInfo.description && <p className="text-xs text-slate-600 mt-1">{String(jobInfo.description).slice(0, 200)}</p>}
        </div>
      )}

      {diffs.length > 0 ? (
        diffs.map((diff) => (
          <div key={diff.id} className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[diff.status] || "bg-slate-700"}`}>{diff.status}</span>
              <span className="text-xs text-slate-500">{diff.summary}</span>
            </div>
            {diff.filesChanged && diff.filesChanged.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {(Array.isArray(diff.filesChanged) ? diff.filesChanged as string[] : String(diff.filesChanged).replace(/[\[\]'\"]/g, "").split(",")).filter(Boolean).map((f: string) => (
                  <span key={f} className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">{f}</span>
                ))}
              </div>
            )}
            {diff.diffText && (
              <div className="rounded-lg bg-slate-950 border border-slate-800 overflow-x-auto max-h-96 overflow-y-auto">
                {renderDiffText(diff.diffText)}
              </div>
            )}
          </div>
        ))
      ) : (
        <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 text-center">
          <p className="text-sm text-slate-500">No hay diffs de codigo para este job.</p>
          <p className="text-xs text-slate-600 mt-1">Este job puede haber sido de consulta o generacion sin cambios en archivos.</p>
        </div>
      )}

      <div className="flex gap-3">
        <button onClick={handleApprove} disabled={actionStatus === "sending"}
          className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold py-3 px-4 transition-colors">
          {actionStatus === "sent" ? "Aprobado!" : actionStatus === "offline" ? "Pendiente" : "Approve"}
        </button>
        <button onClick={handleReject} disabled={actionStatus === "sending"}
          className="flex-1 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-semibold py-3 px-4 transition-colors">
          {actionStatus === "sent" ? "Rechazado!" : actionStatus === "offline" ? "Pendiente" : "Reject"}
        </button>
      </div>
    </div>
  );
}
