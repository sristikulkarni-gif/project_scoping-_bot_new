import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Menu,
  Database,
  Wallet,
  GitBranch,
  ChevronLeft,
  Bot,
  User2,
  LogOut,
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useProjects } from "../../contexts/ProjectContext";

export default function Sidebar({ isOpen, setIsOpen, mobileOpen }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { projects } = useProjects();

  const baseNavItems = [
    { path: "/dashboard", label: "Dashboard", icon: <LayoutDashboard className="w-5 h-5" /> },
    { path: "/ratecards", label: "Pricing", icon: <Wallet className="w-5 h-5" /> },
  ];

  const navItems = user?.is_superuser
    ? [
      ...baseNavItems,
      { path: "/blobs", label: "Knowledge Base", icon: <Database className="w-5 h-5" /> },
      { path: "/etl", label: "ETL Pipeline", icon: <GitBranch className="w-5 h-5" /> },
    ]
    : baseNavItems;

  const initials = user?.username?.[0]?.toUpperCase() || "?";

  const handleLogout = () => {
    logout();
    window.location.href = "/login";
  };

  return (
    <>
      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden backdrop-blur-sm"
          onClick={() => setIsOpen(false)}
        />
      )}

      <aside
        style={{ background: "rgba(10,13,26,0.95)", borderRight: "1px solid rgba(255,255,255,0.06)" }}
        className={`fixed md:static top-0 left-0 h-screen flex flex-col z-40
          backdrop-blur-2xl
          transition-all duration-300 ease-in-out
          ${isOpen ? "w-64" : "w-[72px]"}
          ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        {/* ── Brand Header ── */}
        <div className="flex items-center h-16 px-4 shrink-0" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
          {isOpen ? (
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
                <Bot className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-sm text-white truncate tracking-wide">Project Scoping Bot</span>
            </div>
          ) : (
            <div className="w-9 h-9 rounded-xl flex items-center justify-center mx-auto shrink-0"
              style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
              <Bot className="w-5 h-5 text-white" />
            </div>
          )}
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="ml-auto hidden md:flex items-center justify-center w-7 h-7 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all shrink-0"
          >
            {isOpen ? <ChevronLeft className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>

        {/* ── Navigation ── */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto scrollbar-thin">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `group flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 relative
                ${isActive
                  ? "text-white font-semibold"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                }`
              }
              style={({ isActive }) => isActive ? {
                background: "linear-gradient(135deg, rgba(124,58,237,0.25), rgba(6,182,212,0.12))",
                boxShadow: "inset 0 0 0 1px rgba(139,92,246,0.3)"
              } : {}}
            >
              {/* Active left bar */}
              {({ isActive }) => (
                <>
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full"
                      style={{ background: "linear-gradient(180deg, #7c3aed, #06b6d4)" }} />
                  )}
                  <div className={isOpen ? "" : "mx-auto"}>{item.icon}</div>
                  <span className={`text-sm font-medium whitespace-nowrap transition-all duration-200 ${isOpen ? "opacity-100" : "opacity-0 w-0 overflow-hidden"}`}>
                    {item.label}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* ── User Profile ── */}
        {user && (
          <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }} className="p-3 space-y-1 shrink-0">
            <button
              onClick={() => navigate("/profile")}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all group"
            >
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
                style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
                {initials}
              </div>
              {isOpen && (
                <div className="flex flex-col items-start min-w-0 flex-1">
                  <span className="text-sm font-semibold text-slate-200 truncate w-full">{user.username}</span>
                  <span className="text-xs text-slate-500">View Profile</span>
                </div>
              )}
            </button>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
            >
              <LogOut className={`w-4 h-4 ${isOpen ? "" : "mx-auto"}`} />
              {isOpen && <span className="text-sm font-medium">Logout</span>}
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
