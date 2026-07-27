import { useState, useEffect } from "react";

interface Change {
  status: string;
  path: string;
}

export default function Cambios() {
  const [data, setData] = useState<{ is_git?: boolean; branch?: string; files?: Change[]; raw?: string; error?: string }>({});
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const workspace = localStorage.getItem("dopa-workspace") || "D:\\Dopa\\01_Desarrollo\\dopa-code\\backend-inti";

  const fetchChanges = async () => {
    if (!workspace) return;
    setLoading(true);
    try {
      const r = await fetch(`/api/v1/workspace/changes?path=${encodeURIComponent(workspace)}`);
      setData(await r.json());
    } catch {
      setData({ error: "Error de conexion" });
    }
    setLoading(false);
  };

  useEffect(() => { fetchChanges(); }, []);

  const copy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
              <span className={`text-xs font-mono w-6 ${
                f.status === "M " || f.status === "M" ? "text-amber-400" :
                f.status === "A " || f.status === "A" ? "text-emerald-400" :
                f.status === "D " || f.status === "D" ? "text-red-400" :
                "text-purple-400"
              }`}>{f.status}</span>
              <span className="text-xs font-mono text-slate-300 truncate">{f.path}</span>
            </div>
          ))}
        </div>
      )}

      {data.raw && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">Raw output</p>
            <button onClick={() => copy(data.raw || "")}
              className="text-xs px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors">
              {copied ? "Copiado!" : "Copiar"}
            </button>
          </div>
          <pre className="rounded-lg bg-slate-950 border border-slate-800 p-3 text-xs font-mono text-slate-400 overflow-x-auto max-h-80">
            {data.raw}
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
