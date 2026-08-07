import { useState, useEffect } from "react";

interface Plugin {
  id: string;
  name: string;
  version: string;
  description: string;
  enabled: boolean;
  path: string;
  skills_count: number;
  installed_at: string | null;
}

const API_BASE = `${location.protocol}//${location.host}/api/v1`;

export default function PluginsPage() {
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  const fetchPlugins = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/plugins/`);
      const data = await res.json();
      setPlugins(data.plugins || []);
    } catch { /* offline */ }
    setLoading(false);
  };

  useEffect(() => { fetchPlugins(); }, []);

  const scanPlugins = async () => {
    setScanning(true);
    try {
      await fetch(`${API_BASE}/plugins/scan`, { method: "POST" });
      await fetchPlugins();
    } catch { /* offline */ }
    setScanning(false);
  };

  const togglePlugin = async (id: string, enabled: boolean) => {
    try {
      await fetch(`${API_BASE}/plugins/${id}?enabled=${!enabled}`, { method: "PATCH" });
      setPlugins((prev) => prev.map((p) => (p.id === id ? { ...p, enabled: !enabled } : p)));
    } catch { /* offline */ }
  };

  if (loading) {
    return <div className="text-center py-8 text-slate-500 text-sm">Cargando plugins...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Plugins</h2>
        <button
          onClick={scanPlugins}
          disabled={scanning}
          className="text-xs px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-400 transition-colors"
        >
          {scanning ? "Escaneando..." : "Escanear plugins"}
        </button>
      </div>

      {plugins.length === 0 ? (
        <div className="text-center py-8 text-slate-500 text-sm">
          No hay plugins instalados. Coloca plugins en la carpeta <code className="text-cyan-400">plugins/</code> y escanea.
        </div>
      ) : (
        <div className="space-y-2">
          {plugins.map((p) => (
            <div key={p.id} className="rounded-lg bg-slate-900 border border-slate-800 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-slate-200">{p.name}</span>
                  <span className="text-xs text-slate-500 ml-2">v{p.version}</span>
                </div>
                <button
                  onClick={() => togglePlugin(p.id, p.enabled)}
                  className={`text-xs px-2 py-0.5 rounded transition-colors ${
                    p.enabled
                      ? "bg-emerald-900 text-emerald-400 hover:bg-emerald-800"
                      : "bg-slate-800 text-slate-600 hover:bg-slate-700"
                  }`}
                >
                  {p.enabled ? "Activado" : "Desactivado"}
                </button>
              </div>
              {p.description && (
                <p className="text-xs text-slate-500 mt-1">{p.description}</p>
              )}
              <div className="flex items-center gap-4 mt-2">
                <span className="text-xs text-slate-600">{p.skills_count} skills</span>
                <span className="text-xs text-slate-600 font-mono truncate">{p.path}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
