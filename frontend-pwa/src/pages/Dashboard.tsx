import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-gradient-to-br from-amber-500/20 to-amber-600/5 border border-amber-500/20 p-5">
        <h2 className="text-sm font-semibold text-amber-400 uppercase tracking-wider">
          Inti
        </h2>
        <p className="text-2xl font-bold mt-1">Online</p>
        <p className="text-slate-400 text-sm mt-1">
          Agente andino de orquestacion listo
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {[
          { label: "Pendientes", value: "0", color: "text-amber-400" },
          { label: "En progreso", value: "0", color: "text-blue-400" },
          { label: "QA", value: "0", color: "text-purple-400" },
          { label: "Desplegados", value: "0", color: "text-emerald-400" },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            className="rounded-lg bg-slate-900 border border-slate-800 p-3"
          >
            <p className={`text-xl font-bold ${color}`}>{value}</p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <button
        onClick={() => navigate("/jobs")}
        className="w-full rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold py-3 px-4 transition-colors"
      >
        Ver Jobs
      </button>
    </div>
  );
}
