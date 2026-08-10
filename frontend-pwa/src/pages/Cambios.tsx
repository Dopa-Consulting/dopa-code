import { useState, useEffect } from "react";

interface Change {
  status: string;
  path: string;
  stats?: string;
}

export default function Cambios() {
  const [data, setData] = useState<{ is_git?: boolean; branch?: string; files?: Change[]; raw?: string; diff?: string; error?: string }>({});
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const workspace = localStorage.getItem("dopa-workspace") || "";

  const fetchChanges = async (withDiff = false) => {
    if (!workspace) return;
    setLoading(true);
    try {
      const diffParam = withDiff ? "&diff=1" : "";
      const r = await fetch(`/api/v1/workspace/changes?path=${encodeURIComponent(workspace)}${diffParam}`);
      setData(await r.json());
    } catch {
      setData({ error: "Error de conexion" });
    }
    setLoading(false);
  };

  useEffect(() => { fetchChanges(); }, []);

  useEffect(() => {
    const onFocus = () => fetchChanges(expanded);
    const onStorage = (e: StorageEvent) => { if (e.key === "dopa-workspace") fetchChanges(expanded); };
    window.addEventListener("focus", onFocus);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const toggleDiff = () => {
    const next = !expanded;
    setExpanded(next);
    fetchChanges(next);
  };

  if (!workspace) {
    return (
      <div className="space-y-4">
        <h2 className="text-lg font-semibold">Cambios</h2>
        <div className="text-center py-8 text-slate-500 text-sm">
          Configura un workspace en el Chat para ver los cambios aqui.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Cambios</h2>
        <div className="flex items-center gap-2">
          <button onClick={toggleDiff}
            className={`text-xs px-3 py-1 rounded transition-colors ${expanded ? "bg-amber-900 text-amber-400" : "bg-slate-800 hover:bg-slate-700 text-slate-400"}`}>
            {expanded ? "Diff (+/-)" : "Solo lista"}
          </button>
          <button onClick={() => fetchChanges(expanded)} disabled={loading}
            className="text-xs px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors">
            {loading ? "..." : "Refrescar"}
          </button>
        </div>
      </div>

      <p className="text-xs text-slate-600 font-mono truncate">{workspace}</p>

      {data.error && <p className="text-sm text-red-400">{data.error}</p>}

      {data.is_git && data.branch && (
        <div className="rounded-lg bg-slate-900 border border-slate-800 p-3">
          <p className="text-xs text-slate-500">Branch</p>
          <p className="text-sm font-mono text-amber-400">{data.branch}</p>
        </div>
      )}

      {data.files && data.files.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-slate-500">{data.files.length} archivos modificados</p>
          {data.files.map((f, i) => (
            <div key={i} className="flex items-center gap-2 rounded bg-slate-900 border border-slate-800 px-3 py-1.5">
              <span className={`text-xs font-mono w-6 flex-shrink-0 ${
                f.status === "M " || f.status === "M" ? "text-amber-400" :
                f.status === "A " || f.status === "A" ? "text-emerald-400" :
                f.status === "D " || f.status === "D" ? "text-red-400" :
                "text-purple-400"
              }`}>{f.status}</span>
              <span className="text-xs font-mono text-slate-300 truncate flex-1">{f.path}</span>
              {f.stats && <span className="text-xs font-mono text-emerald-400 flex-shrink-0">{f.stats}</span>}
            </div>
          ))}
        </div>
      )}

      {data.diff && (
        <div className="space-y-2">
          <p className="text-xs text-slate-500">Diff completo</p>
          <pre className="rounded-lg bg-slate-950 border border-slate-800 p-3 text-xs font-mono text-slate-400 overflow-x-auto max-h-80 leading-tight">
            {data.diff.split("\n").map((line, i) => (
              <div key={i} className={
                line.startsWith("+") && !line.startsWith("+++") ? "text-emerald-400" :
                line.startsWith("-") && !line.startsWith("---") ? "text-red-400" :
                line.startsWith("@@") ? "text-cyan-400" :
                "text-slate-500"
              }>{line || " "}</div>
            ))}
          </pre>
        </div>
      )}

      {data.is_git && (!data.files || data.files.length === 0) && (
        <div className="text-center py-8 text-slate-500 text-sm">
          Working tree limpio. No hay cambios.
        </div>
      )}
    </div>
  );
}
