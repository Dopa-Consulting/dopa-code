import { Outlet, NavLink } from "react-router-dom";
import { useState, useEffect } from "react";

function LoginGate() {
  const [token, setToken] = useState("");
  const [checked, setChecked] = useState(false);
  const [authed, setAuthed] = useState(() => {
    const saved = localStorage.getItem("dopa-token");
    return !!saved;  // optimistic: si hay token guardado, asumir autenticado
  });
  const [error, setError] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("dopa-token") || new URLSearchParams(location.search).get("token");
    if (saved) {
      setToken(saved);
      localStorage.setItem("dopa-token", saved);
      fetch(`/login?token=${encodeURIComponent(saved)}`)
        .then(r => {
          setAuthed(r.ok);
          setChecked(true);
        })
        .catch(() => setChecked(true));
    } else {
      setChecked(true);
    }
  }, []);

  // No mostrar login hasta verificar el token guardado
  if (!checked && authed) return null;  // loading state, mantener UI previa
  if (!checked) return null;

  const login = async () => {
    try {
      const r = await fetch(`/login?token=${encodeURIComponent(token)}`);
      if (r.ok) {
        localStorage.setItem("dopa-token", token);
        setAuthed(true);
        setError("");
      } else {
        setError("Token invalido");
      }
    } catch {
      setError("Error de conexion");
    }
  };

  if (authed) return <MainLayout />;

  return (
    <div className="flex flex-col items-center justify-center min-h-dvh p-6 text-center">
      <h1 className="text-2xl font-bold mb-2"><span className="text-amber-400">Dopa</span> Code</h1>
      <p className="text-slate-400 text-sm mb-6">Inti - Agente andino</p>
      <input type="password" value={token} onChange={(e) => setToken(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && login()}
        placeholder="Token de acceso..."
        className="w-full max-w-xs rounded-lg bg-slate-800 border border-slate-700 px-4 py-3 text-sm text-slate-300 placeholder-slate-600 focus:outline-none focus:border-amber-500/50 mb-3" />
      <button onClick={login}
        className="w-full max-w-xs rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold py-3 px-4 transition-colors text-sm">
        Entrar
      </button>
      {error && <p className="text-red-400 text-xs mt-3">{error}</p>}
      <p className="text-slate-600 text-xs mt-6">Configura DOPA_ACCESS_TOKEN en .env</p>
    </div>
  );
}

function MainLayout() {
  return (
    <div className="flex flex-col min-h-dvh">
      <header className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <h1 className="text-lg font-bold tracking-tight">
          <span className="text-amber-400">Dopa</span> Code
        </h1>
        <NavLink to="/models" className="text-xs text-slate-500 hover:text-amber-400 transition-colors">
          OpenRouter
        </NavLink>
      </header>

      <main className="flex-1 overflow-auto px-4 py-4">
        <Outlet />
      </main>

      <nav className="flex border-t border-slate-800 bg-slate-900">
        {[
          { to: "/", label: "Chat", icon: "O" },
          { to: "/jobs", label: "Jobs", icon: "[]" },
          { to: "/sessions", label: "Sesiones", icon: "S" },
          { to: "/models", label: "Modelos", icon: "AI" },
        ].map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center py-3 text-xs gap-1 transition-colors ${
                isActive ? "text-amber-400" : "text-slate-500"
              }`
            }
          >
            <span className="text-lg leading-none">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export default function Layout() {
  return <LoginGate />;
}
