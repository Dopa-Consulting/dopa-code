import { useState, useEffect, useCallback } from "react";

interface Change {
  status: string;
  path: string;
  stats?: string;
}

export default function Cambios() {
  const [data, setData] = useState<{ is_git?: boolean; branch?: string; files?: Change[]; diff?: string; error?: string }>({});
  const [loading, setLoading] = useState(false);
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  const workspace = localStorage.getItem("dopa-workspace") || "";

  const fetchChanges = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    try {
      const r = await fetch(`/api/v1/workspace/changes?path=${encodeURIComponent(workspace)}&diff=1`);
      setData(await r.json());
    } catch {
      setData({ error: "Error de conexion" });
    }
    setLoading(false);
  }, [workspace]);

  useEffect(() => { fetchChanges(); }, [fetchChanges]);

  useEffect(() => {
    const onFocus = () => fetchChanges();
    const onStorage = (e: StorageEvent) => { if (e.key === "dopa-workspace") fetchChanges(); };
    window.addEventListener("focus", onFocus);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("storage", onStorage);
    };
  }, [fetchChanges]);

  // Filtrar diff para un archivo especifico
  const getFileDiff = (filepath: string): string[] => {
    if (!data.diff) return [];
    const lines = data.diff.split("\n");
    const result: string[] = [];
    let inFile = false;
    for (const line of lines) {
      if (line.startsWith("diff --git") && line.includes(filepath)) {
        inFile = true;
      } else if (line.startsWith("diff --git") && inFile) {
        break;
      }
      if (inFile) result.push(line);
    }
    return result;
  };

  const toggleFile = (filepath: string) => {
    setExpandedFile(expandedFile === filepath ? null : filepath);
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
        <button onClick={fetchChanges} disabled={loading}
          className="text-xs px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors">
          {loading ? "..." : "Refrescar"}
        </button>
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
            <div key={i}>
              <div
                onClick={() => toggleFile(f.path)}
                className="flex items-center gap-2 rounded bg-slate-900 border border-slate-800 px-3 py-1.5 cursor-pointer hover:bg-slate-800/50 transition-colors"
              >
                <span className={`text-xs font-mono w-6 flex-shrink-0 ${
                  f.status === "M " || f.status === "M" ? "text-amber-400" :
                  f.status === "A " || f.status === "A" ? "text-emerald-400" :
                  f.status === "D " || f.status === "D" ? "text-red-400" :
                  "text-purple-400"
                }`}>{f.status}</span>
                <span className="text-xs font-mono text-slate-300 truncate flex-1">{f.path}</span>
                {f.stats && <span className="text-xs font-mono text-emerald-400 flex-shrink-0">{f.stats}</span>}
                <span className="text-xs text-slate-600">{expandedFile === f.path ? "▲" : "▼"}</span>
              </div>
              {expandedFile === f.path && (
                <pre className="mt-0.5 rounded-b-lg bg-slate-950 border border-slate-800 border-t-0 p-2 text-xs font-mono text-slate-400 overflow-x-auto max-h-60 leading-tight">
                  {getFileDiff(f.path).map((line, j) => (
                    <div key={j} className={
                      line.startsWith("+") && !line.startsWith("+++") ? "text-emerald-400" :
                      line.startsWith("-") && !line.startsWith("---") ? "text-red-400" :
                      line.startsWith("@@") ? "text-cyan-400" :
                      line.startsWith("diff") ? "text-amber-400" :
                      "text-slate-500"
                    }>{line || " "}</div>
                  ))}
                </pre>
              )}
            </div>
          ))}
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
