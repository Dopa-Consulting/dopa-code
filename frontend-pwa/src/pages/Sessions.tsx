import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = `${location.protocol}//${location.host}/api/v1`;

interface Session {
  id: string;
  role: string;
  model: string;
  status: string;
  current_job_id: string | null;
  workspace_path: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export default function Sessions() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [workspace, setWorkspace] = useState(localStorage.getItem("dopa-workspace") || "D:\\Dopa\\01_Desarrollo\\dopa-code");
  const [role, setRole] = useState("builder");

  useEffect(() => {
    fetch(`${API_BASE}/sessions/`)
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []))
      .catch(() => {});
  }, []);

  const createSession = async (r: string) => {
    await fetch(`${API_BASE}/sessions/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: r, workspace_path: workspace }),
    });
    const res = await fetch(`${API_BASE}/sessions/`);
    const data = await res.json();
    setSessions(data.sessions || []);
  };

  const saveWorkspace = () => {
    localStorage.setItem("dopa-workspace", workspace);
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Sesiones y Workspace</h2>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-3">
        <h3 className="text-sm font-semibold text-slate-300">Workspace</h3>
        <input
          value={workspace}
          onChange={(e) => setWorkspace(e.target.value)}
          onBlur={saveWorkspace}
          className="w-full rounded bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-300 font-mono focus:outline-none focus:border-amber-500/50"
        />
        <p className="text-xs text-slate-500">Cambia la carpeta de trabajo. Se guarda automatico.</p>
      </div>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-3">
        <h3 className="text-sm font-semibold text-slate-300">Nueva sesion</h3>
        <select value={role} onChange={(e) => setRole(e.target.value)}
          className="w-full rounded bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-amber-500/50">
          <option value="architect">Architect (Opus 4.8)</option>
          <option value="builder">Builder (DeepSeek V4)</option>
          <option value="reviewer">Reviewer (Gemini Flash)</option>
        </select>
        <button onClick={() => createSession(role)}
          className="w-full rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold py-2 px-4 transition-colors text-sm">
          Crear sesion {role}
        </button>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-slate-300">Sesiones ({sessions.length})</h3>
        {sessions.length === 0 ? (
          <p className="text-xs text-slate-600">No hay sesiones. Crea una para empezar.</p>
        ) : (
          sessions.map((s) => (
            <div key={s.id}
              onClick={() => {
                if (s.workspace_path) localStorage.setItem("dopa-workspace", s.workspace_path);
                if (s.metadata?.title) localStorage.setItem("dopa-session-title", String(s.metadata.title));
                localStorage.setItem("dopa-session-id", s.id);
                navigate("/");
              }}
              className="rounded-lg bg-slate-900 border border-slate-800 p-3 cursor-pointer hover:bg-slate-800/50 transition-colors">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-200 truncate">
                  {String(s.metadata?.title || s.workspace_path?.split("\\").pop() || s.role)}
                </span>
                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${s.status === "running" ? "bg-emerald-400 animate-pulse" : "bg-slate-600"}`} />
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-amber-400">{s.role}</span>
                <span className="text-xs text-slate-500">{s.model?.split("/").pop()}</span>
                <span className="text-xs text-slate-600 ml-auto">{s.status}</span>
              </div>
              <p className="text-xs text-slate-600 mt-1 truncate">{s.workspace_path}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
