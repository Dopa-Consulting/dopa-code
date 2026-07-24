import { Outlet, NavLink } from "react-router-dom";

export default function Layout() {
  return (
    <div className="flex flex-col min-h-dvh">
      <header className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <h1 className="text-lg font-bold tracking-tight">
          <span className="text-amber-400">Dopa</span> Code
        </h1>
        <span className="text-xs text-slate-500">Inti</span>
      </header>

      <main className="flex-1 overflow-auto px-4 py-4">
        <Outlet />
      </main>

      <nav className="flex border-t border-slate-800 bg-slate-900">
        {[
          { to: "/", label: "Dashboard", icon: "=" },
          { to: "/jobs", label: "Jobs", icon: "[]" },
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
