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
  free?: boolean;
}

const PROVIDERS = [
  { id: "openrouter", name: "OpenRouter", key: "sk-or-v1-..." },
  { id: "openai", name: "OpenAI", key: "sk-..." },
  { id: "deepseek", name: "DeepSeek", key: "sk-..." },
  { id: "anthropic", name: "Anthropic", key: "sk-ant-..." },
  { id: "google", name: "Google AI", key: "AIza..." },
  { id: "groq", name: "Groq", key: "gsk_..." },
];

export default function ModelSelector() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [testResult, setTestResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedModel, setSelectedModel] = useState("deepseek/deepseek-chat");
  const [activeProvider, setActiveProvider] = useState("openrouter");
  const [providerStatus, setProviderStatus] = useState<Array<{ name: string; configured: boolean }>>([]);

  useEffect(() => {
    fetchModels();
    fetchHealth();
    fetchProviderStatus();
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

  const fetchProviderStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/openrouter/provider/status`);
      const data = await res.json();
      setProviderStatus(data.providers || []);
    } catch { /* offline */ }
  };

  const configure = async () => {
    setLoading(true);
    try {
      if (activeProvider === "openrouter") {
        const res = await fetch(`${API_BASE}/openrouter/config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ api_key: apiKey }),
        });
        const data = await res.json();
        setHealth(data);
      } else {
        const res = await fetch(`${API_BASE}/openrouter/provider/config`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ provider: activeProvider, api_key: apiKey }),
        });
        await res.json();
      }
      fetchProviderStatus();
    } finally {
      setLoading(false);
    }
  };

  const testChat = async () => {
    setTestResult("Testing...");
    try {
      const endpoint = activeProvider === "openrouter"
        ? `${API_BASE}/openrouter/chat/test`
        : `${API_BASE}/openrouter/provider/chat`;

      const body = activeProvider === "openrouter"
        ? { model: selectedModel, prompt: "Respond with exactly OK." }
        : { provider: activeProvider, model: selectedModel, prompt: "Respond with exactly OK." };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data.error) {
        setTestResult(`Error: ${data.error}`);
      } else {
        const tokens = data.usage?.total_tokens || "?";
        setTestResult(`${data.content?.slice(0, 100)}\nTokens: ${tokens}`);
      }
    } catch {
      setTestResult("Connection failed");
    }
  };

  const freeModels = models.filter((m) => m.free);
  const paidModels = models.filter((m) => !m.free);

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Modelos</h2>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {PROVIDERS.map((p) => {
          const status = p.id === "openrouter"
            ? health?.status === "ok"
            : providerStatus.find((s) => s.name === p.id)?.configured;
          return (
            <button
              key={p.id}
              onClick={() => setActiveProvider(p.id)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                activeProvider === p.id
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                  : "bg-slate-800 text-slate-400 border border-slate-700"
              }`}
            >
              {p.name}
              <span className={`ml-1.5 inline-block w-1.5 h-1.5 rounded-full ${status ? "bg-emerald-400" : "bg-slate-600"}`} />
            </button>
          );
        })}
      </div>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">{PROVIDERS.find(p => p.id === activeProvider)?.name}</span>
        </div>
        <input
          type="password"
          placeholder={PROVIDERS.find(p => p.id === activeProvider)?.key}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="w-full rounded bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50"
        />
        <button
          onClick={configure}
          disabled={loading || !apiKey}
          className="w-full rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold py-2 px-4 transition-colors text-sm"
        >
          {loading ? "Configurando..." : `Conectar ${PROVIDERS.find(p => p.id === activeProvider)?.name}`}
        </button>
        <p className="text-xs text-slate-600">
          OpenRouter cobra ~5% sobre el precio del proveedor. APIs directas = sin margen extra.
        </p>
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
                {m.name} {m.free ? "🆓" : `(${m.provider})`}
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

      {freeModels.length > 0 && (
        <>
          <h3 className="text-sm font-semibold text-slate-400">Gratuitos</h3>
          {freeModels.map((m) => (
            <ModelCard key={m.id} model={m} selected={selectedModel === m.id} onSelect={() => setSelectedModel(m.id)} />
          ))}
        </>
      )}

      <h3 className="text-sm font-semibold text-slate-400">Todos los modelos</h3>
      {paidModels.map((m) => (
        <ModelCard key={m.id} model={m} selected={selectedModel === m.id} onSelect={() => setSelectedModel(m.id)} />
      ))}
    </div>
  );
}

function ModelCard({ model, selected, onSelect }: { model: ModelInfo; selected: boolean; onSelect: () => void }) {
  const formatPrice = (price: number) => `$${price.toFixed(2)}/1M`;
  return (
    <div
      onClick={onSelect}
      className={`rounded-lg border p-3 cursor-pointer transition-colors ${
        selected ? "border-amber-500/30 bg-amber-500/5" : "border-slate-800 bg-slate-900/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium">
            {model.name}
            {model.free && <span className="ml-1 text-xs text-emerald-400">FREE</span>}
          </p>
          <p className="text-xs text-slate-500">{model.provider}</p>
        </div>
        <div className="text-right">
          {model.pricing_per_1m_tokens && (
            <p className="text-xs text-slate-400">
              {model.pricing_per_1m_tokens.prompt === 0
                ? "$0 (gratis)"
                : `${formatPrice(model.pricing_per_1m_tokens.prompt)} / ${formatPrice(model.pricing_per_1m_tokens.completion)}`}
            </p>
          )}
          {model.context_length && (
            <p className="text-xs text-slate-600">{Math.round(model.context_length / 1000)}k ctx</p>
          )}
        </div>
      </div>
      {model.capabilities && (
        <div className="flex gap-1 mt-1.5 flex-wrap">
          {model.capabilities.map((c) => (
            <span key={c} className="text-xs px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">{c}</span>
          ))}
        </div>
      )}
    </div>
  );
}
