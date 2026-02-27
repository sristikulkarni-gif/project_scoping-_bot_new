import { useEffect, useMemo } from "react";
import { useProjects } from "../contexts/ProjectContext";
import { useAuth } from "../contexts/AuthContext";
import { Trash2, Eye, Folder, Zap, TrendingUp, BarChart2, Clock, CheckCircle2, Archive } from "lucide-react";
import { Link } from "react-router-dom";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";

/** Colored pill for project status */
function StatusBadge({ status }) {
  const map = {
    draft: { label: "Draft", bg: "rgba(139,92,246,0.15)", color: "#a78bfa", border: "rgba(139,92,246,0.3)" },
    active: { label: "Active", bg: "rgba(16,185,129,0.15)", color: "#34d399", border: "rgba(16,185,129,0.3)" },
    closed: { label: "Closed", bg: "rgba(100,116,139,0.15)", color: "#94a3b8", border: "rgba(100,116,139,0.3)" },
  };
  const s = map[status] || map.draft;
  return (
    <span className="text-xs font-semibold px-2 py-0.5 rounded-full"
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}>
      {s.label}
    </span>
  );
}

/** Relative time string */
function relativeTime(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

export default function Dashboard() {
  const { projects, fetchProjects, deleteProject } = useProjects();
  const { user } = useAuth();

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this project?"))
      await deleteProject(id);
  };

  const today = new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric", year: "numeric" });

  const complexityData = ["Simple", "Medium", "High"].map((c) => ({
    complexity: c,
    count: projects.filter((p) => p.complexity === c).length,
  }));

  const dailyData = projects.reduce((acc, p) => {
    const day = new Date(p.created_at).toLocaleDateString("en-US", { day: "2-digit", month: "short" });
    const existing = acc.find((d) => d.day === day);
    if (existing) existing.count += 1;
    else acc.push({ day, count: 1 });
    return acc;
  }, []).sort((a, b) => new Date(a.day) - new Date(b.day)).slice(-10);

  const weekProjects = projects.filter(p => {
    const created = new Date(p.created_at);
    const weekAgo = new Date(); weekAgo.setDate(weekAgo.getDate() - 7);
    return created >= weekAgo;
  });

  const domains = [...new Set(projects.map(p => p.domain).filter(Boolean))];
  const mostActiveDomain = domains.length
    ? domains.sort((a, b) =>
      projects.filter(p => p.domain === b).length - projects.filter(p => p.domain === a).length
    )[0]
    : "—";

  const topComplexity = complexityData.sort((a, b) => b.count - a.count)[0]?.complexity || "—";

  // Build activity feed from project events
  const activityFeed = useMemo(() => {
    const events = [];
    [...projects]
      .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      .slice(0, 15)
      .forEach(p => {
        if (p.scope_finalized_at) {
          events.push({
            id: `fin-${p.id}`,
            icon: <CheckCircle2 className="w-3.5 h-3.5" />,
            color: "#10b981",
            text: <>You generated a detailed scope for <span className="text-violet-400 font-semibold">{p.name || "Untitled"}</span></>,
            time: p.scope_finalized_at,
          });
        }
        if (p.status === "closed" && p.closed_at) {
          events.push({
            id: `cls-${p.id}`,
            icon: <Archive className="w-3.5 h-3.5" />,
            color: "#94a3b8",
            text: <>Project <span className="text-slate-300 font-semibold">{p.name || "Untitled"}</span> was closed</>,
            time: p.closed_at,
          });
        }
        events.push({
          id: `crt-${p.id}`,
          icon: <Folder className="w-3.5 h-3.5" />,
          color: "#7c3aed",
          text: <>Project <span className="text-violet-400 font-semibold">{p.name || "Untitled"}</span> was created</>,
          time: p.created_at,
        });
      });

    return events
      .sort((a, b) => new Date(b.time) - new Date(a.time))
      .slice(0, 8);
  }, [projects]);

  const tooltipStyle = {
    backgroundColor: "#131929",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "10px",
    color: "#e2e8f0",
    fontSize: "13px",
    boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
  };

  return (
    <div className="space-y-6 animate-fade-in">

      {/* ── Welcome Header ── */}
      <div className="rounded-2xl p-6 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, rgba(124,58,237,0.18) 0%, rgba(6,182,212,0.08) 100%)",
          border: "1px solid rgba(139,92,246,0.25)",
        }}>
        <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full opacity-20 blur-3xl pointer-events-none"
          style={{ background: "radial-gradient(circle, #7c3aed, transparent)" }} />
        <div className="absolute -bottom-10 -left-10 w-48 h-48 rounded-full opacity-10 blur-3xl pointer-events-none"
          style={{ background: "radial-gradient(circle, #06b6d4, transparent)" }} />
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-1">
            <span className="status-dot status-online" />
            <span className="text-xs text-slate-400 font-medium">{today} · {projects.length} scoping activities</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white mb-1">Project Scoping Bot</h1>
          <p className="text-slate-400 text-sm">
            Welcome back, <span className="text-violet-400 font-semibold">{user?.username || "..."}</span>
          </p>
        </div>
      </div>

      {/* ── Stats + Right Panel ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

        <div className="xl:col-span-2 space-y-5">

          {/* Stat Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { label: "Total Projects", value: projects.length, icon: <Folder className="w-4 h-4" />, color: "#7c3aed" },
              { label: "This Week", value: weekProjects.length, icon: <TrendingUp className="w-4 h-4" />, color: "#06b6d4" },
              { label: "Avg Accuracy", value: "93%", icon: <BarChart2 className="w-4 h-4" />, color: "#10b981" },
            ].map((stat) => (
              <div key={stat.label} className="rounded-2xl p-5 relative overflow-hidden"
                style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
                <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full blur-2xl opacity-15"
                  style={{ background: stat.color }} />
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center"
                    style={{ background: `${stat.color}22`, color: stat.color }}>
                    {stat.icon}
                  </div>
                  <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">{stat.label}</span>
                </div>
                <p className="text-4xl font-extrabold text-white">{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-2xl p-5" style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
              <h3 className="text-sm font-semibold text-slate-300 mb-4">Projects by Complexity</h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={complexityData} barSize={28}>
                  <XAxis dataKey="complexity" stroke="#475569" fontSize={12} tick={{ fill: "#64748b" }} />
                  <YAxis stroke="#475569" fontSize={12} allowDecimals={false} tick={{ fill: "#64748b" }} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgba(124,58,237,0.08)" }} />
                  <defs>
                    <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#7c3aed" />
                      <stop offset="100%" stopColor="#06b6d4" />
                    </linearGradient>
                  </defs>
                  <Bar dataKey="count" fill="url(#barGrad)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="rounded-2xl p-5" style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
              <h3 className="text-sm font-semibold text-slate-300 mb-4">Projects Timeline (Last 10 Days)</h3>
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={dailyData}>
                  <XAxis dataKey="day" stroke="#475569" fontSize={11} tick={{ fill: "#64748b" }} />
                  <YAxis stroke="#475569" fontSize={11} allowDecimals={false} tick={{ fill: "#64748b" }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <defs>
                    <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#7c3aed" />
                      <stop offset="100%" stopColor="#06b6d4" />
                    </linearGradient>
                  </defs>
                  <Line type="monotone" dataKey="count"
                    stroke="url(#lineGrad)" strokeWidth={2.5}
                    dot={{ r: 4, fill: "#7c3aed", strokeWidth: 2, stroke: "#0a0d1a" }}
                    activeDot={{ r: 6, fill: "#06b6d4", stroke: "#0a0d1a", strokeWidth: 2 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* ── Right Panel ── */}
        <div className="space-y-4">
          {/* ScopeBot card */}
          <div className="rounded-2xl p-5 text-center" style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="w-14 h-14 rounded-2xl mx-auto mb-3 flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}>
              <Zap className="w-7 h-7 text-white" />
            </div>
            <p className="font-semibold text-white mb-1">ScopeBot Assistant</p>
            <p className="text-xs text-slate-400 mb-3">AI is healthy and ready to assist you.</p>
            <div className="flex items-center justify-center gap-1.5 text-xs text-emerald-400">
              <span className="status-dot status-online" />
              <span>All systems operational</span>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="rounded-2xl p-5 space-y-2" style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Quick Actions</h3>
            {[
              { label: "Create New Project", to: "/projects" },
              { label: "Open Previous Scope", to: "/history" },
            ].map((a) => (
              <Link key={a.label} to={a.to}
                className="flex items-center justify-between w-full px-4 py-3 rounded-xl text-sm font-medium text-slate-300 hover:text-white transition-all group"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}>
                <span>{a.label}</span>
                <span className="text-slate-600 group-hover:text-violet-400 transition-colors">›</span>
              </Link>
            ))}
          </div>

          {/* AI Insights */}
          <div className="rounded-2xl p-5" style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">AI Insights</h3>
            <div className="space-y-2.5">
              <div className="flex items-center gap-2">
                <span className="status-dot status-online" />
                <span className="text-xs text-slate-400">Most Active Domain ·
                  <span className="text-violet-400 font-semibold ml-1">{mostActiveDomain}</span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="status-dot" style={{ background: "#06b6d4" }} />
                <span className="text-xs text-slate-400">Top Complexity ·
                  <span className="text-cyan-400 font-semibold ml-1">{topComplexity}</span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Activity Feed + Recent Projects (side by side on xl) ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

        {/* Activity Feed */}
        <div className="rounded-2xl overflow-hidden" style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="px-5 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <h2 className="text-sm font-semibold text-slate-200">Activity Feed</h2>
            <p className="text-xs text-slate-500 mt-0.5">Recent events across your projects</p>
          </div>
          <div className="divide-y" style={{ borderColor: "rgba(255,255,255,0.04)" }}>
            {activityFeed.length === 0 ? (
              <div className="px-5 py-10 text-center text-slate-500 text-xs">No activity yet</div>
            ) : activityFeed.map((event) => (
              <div key={event.id} className="flex items-start gap-3 px-5 py-3.5 hover:bg-white/[0.02] transition-colors">
                <div className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{ background: `${event.color}22`, color: event.color }}>
                  {event.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-400 leading-relaxed">{event.text}</p>
                  <div className="flex items-center gap-1 mt-1 text-slate-600 text-xs">
                    <Clock className="w-3 h-3" />
                    {relativeTime(event.time)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Projects Table */}
        <div className="xl:col-span-2 rounded-2xl overflow-hidden" style={{ background: "#131929", border: "1px solid rgba(255,255,255,0.06)" }}>
          <div className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div>
              <h2 className="text-sm font-semibold text-slate-200">Recent Projects</h2>
              <p className="text-xs text-slate-500 mt-0.5">Latest {Math.min(projects.length, 30)} of {projects.length}</p>
            </div>
            <Link to="/projects" className="text-xs font-semibold text-violet-400 hover:text-violet-300 transition-colors">
              + New Project
            </Link>
          </div>
          {projects.length === 0 ? (
            <div className="py-16 text-center text-slate-500 text-sm">No projects yet. Create one to get started.</div>
          ) : (
            <table className="w-full">
              <thead>
                <tr>
                  <th className="px-5 py-3 text-left">PROJECT</th>
                  <th className="px-5 py-3 text-left">DOMAIN</th>
                  <th className="px-5 py-3 text-left hidden md:table-cell">CREATED</th>
                  <th className="px-5 py-3 text-left hidden sm:table-cell">STATUS</th>
                  <th className="px-5 py-3 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {[...projects]
                  .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                  .slice(0, 30)
                  .map((p) => (
                    <tr key={p.id}>
                      <td className="px-5 py-3 font-medium">
                        <Link to={`/exports/${p.id}?mode=draft`} className="text-violet-400 hover:text-violet-300 transition-colors text-sm">
                          {p.name || "Untitled"}
                        </Link>
                      </td>
                      <td className="px-5 py-3">
                        <span className="badge badge-primary text-xs">{p.domain || "—"}</span>
                      </td>
                      <td className="px-5 py-3 text-slate-500 text-xs hidden md:table-cell">
                        {new Date(p.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3 hidden sm:table-cell">
                        <StatusBadge status={p.status || "draft"} />
                      </td>
                      <td className="px-5 py-3 text-right">
                        <div className="flex items-center justify-end gap-3">
                          <Link to={`/exports/${p.id}?mode=draft`}
                            className="text-xs text-slate-500 hover:text-violet-400 transition-colors flex items-center gap-1">
                            <Eye className="w-3.5 h-3.5" /> View
                          </Link>
                          <Link to={`/projects/${p.id}`}
                            className="text-xs text-slate-500 hover:text-cyan-400 transition-colors flex items-center gap-1">
                            <Folder className="w-3.5 h-3.5" /> Details
                          </Link>
                          <button onClick={() => handleDelete(p.id)}
                            className="text-xs text-slate-500 hover:text-red-400 transition-colors flex items-center gap-1">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
