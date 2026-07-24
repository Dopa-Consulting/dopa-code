import { useState, useEffect } from "react";

const API_BASE = "http://localhost:8000/api/v1";

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_length?: number;
  max_output?: number;
  pricing_per_1m_tokens?: { prompt: number; completion: number };
  capabilities?: string[];
}

export default function ModelSelector() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [testResult, setTestResult] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("deepseek/deepseek-chat");

  useEffect(() => {
    fetchModels();
    fetchHealth();
  }, []);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/openrouter/health`);
      const data = await res.json();
      setHealth(data);
    } catch { /* offline */ }
  };

  const fetchModels = async () => {
    try {
      const res = await fetch(`${API_BASE}/openrouter/models/catalog`);
      const data = await res.json();
      setModels(data.catalog || []);
    } catch { /* offline */ }
  };

  const configure = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/openrouter/config?api_key=${encodeURIComponent(apiKey)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      });
      const data = await res.json();
      setHealth(data);
      if (data.status === "configured") fetchModels();
    } finally {
      setLoading(false);
    }
  };

  const testChat = async () => {
    setTestResult("Testing...");
    try {
      const res = await fetch(`${API_BASE}/openrouter/chat/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: selectedModel,
          prompt: "Respond with exactly 'OK' and nothing else.",
        }),
      });
      const data = await res.json();
      if (data.error) {
        setTestResult(`Error: ${data.error}`);
      } else {
        const cost = data.cost;
        setTestResult(
          `${data.content?.slice(0, 100)}\nTokens: ${data.usage?.total_tokens} | Cost: $${cost?.total_cost_usd}`
        );
      }
    } catch {
      setTestResult("Connection failed");
    }
  };

  const formatPrice = (price: number) => {
    return `$${price.toFixed(2)}/1M`;
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Modelos OpenRouter</h2>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">Estado</span>
          <span className={`text-xs px-2 py-0.5 rounded-full ${
            health?.status === "ok" ? "bg-emerald-500/20 text-emerald-400" : "bg-slate-700 text-slate-400"
          }`}>
            {health?.status === "ok" ? "Conectado" : health?.status === "error" ? "Error" : "No configurado"}
          </span>
        </div>

        {(() => {
          const credits = health?.credits as Record<string, unknown> | undefined;
          if (credits && !("error" in credits) && credits.credits_remaining != null) {
            return (
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Creditos</span>
                <span className="text-sm text-amber-400 font-mono">
                  ${String(credits.credits_remaining)}
                </span>
              </div>
            );
          }
          return null;
        })()}

        <input
          type="password"
          placeholder="sk-or-v1-..."
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="w-full rounded bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50"
        />
        <button
          onClick={configure}
          disabled={loading || !apiKey}
          className="w-full rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold py-2 px-4 transition-colors text-sm"
        >
          {loading ? "Configurando..." : "Conectar OpenRouter"}
        </button>
      </div>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-3">
        <div className="flex items-center gap-2">
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="flex-1 rounded bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-amber-500/50"
          >
            {models.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.provider})
              </option>
            ))}
          </select>
          <button
            onClick={testChat}
            className="rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 font-medium py-2 px-4 transition-colors text-sm"
          >
            Test
          </button>
        </div>
        {testResult && (
          <p className="text-xs font-mono text-slate-400 whitespace-pre-wrap">{testResult}</p>
        )}
      </div>

      <div className="space-y-2">
        {models.map((m) => (
          <div
            key={m.id}
            onClick={() => setSelectedModel(m.id)}
            className={`rounded-lg border p-3 cursor-pointer transition-colors ${
              selectedModel === m.id
                ? "border-amber-500/30 bg-amber-500/5"
                : "border-slate-800 bg-slate-900/50"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{m.name}</p>
                <p className="text-xs text-slate-500">{m.provider}</p>
              </div>
              <div className="text-right">
                {m.pricing_per_1m_tokens && (
                  <p className="text-xs text-slate-400">
                    {formatPrice(m.pricing_per_1m_tokens.prompt)} in
                    {" / "}
                    {formatPrice(m.pricing_per_1m_tokens.completion)} out
                  </p>
                )}
                {m.context_length && (
                  <p className="text-xs text-slate-600">{Math.round(m.context_length / 1000)}k ctx</p>
                )}
              </div>
            </div>
            {m.capabilities && (
              <div className="flex gap-1 mt-1.5">
                {m.capabilities.map((c) => (
                  <span key={c} className="text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">{c}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
