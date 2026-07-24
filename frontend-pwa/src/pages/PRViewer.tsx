import { useParams } from "react-router-dom";

export default function PRViewer() {
  const { jobId } = useParams();

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Pull Request #{jobId?.slice(0, 8)}</h2>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 space-y-3">
        <div className="flex items-center gap-3">
          <span className="w-3 h-3 rounded-full bg-amber-400" />
          <span className="font-medium">CI: Running...</span>
        </div>

        <div className="space-y-2 text-sm text-slate-400">
          <p>El visor de PRs se integrara con GitHub via Inti + n8n.</p>
          <p>Funcionalidades planeadas:</p>
          <ul className="list-disc pl-4 space-y-1 text-xs">
            <li>Estado de CI en tiempo real</li>
            <li>Comentarios del Arquitecto LLM y QA</li>
            <li>Merge manual con verificacion WebAuthn</li>
            <li>Auto-merge en staging (CI verde + confidence_high)</li>
          </ul>
        </div>
      </div>

      <div className="flex gap-3">
        <button className="flex-1 rounded-lg bg-slate-700 text-slate-300 font-semibold py-3 px-4" disabled>
          Ver en GitHub
        </button>
        <button className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 px-4 transition-colors">
          Merge (staging)
        </button>
      </div>
    </div>
  );
}
