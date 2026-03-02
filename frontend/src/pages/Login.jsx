import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import authApi from "../api/authApi";
import { Bot } from "lucide-react";

export default function Login() {
  const [email, setEmail] = useState("karan.moreshwar@sigmoidanalytics.com");
  const [password, setPassword] = useState("1234");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await authApi.login(email, password);
      localStorage.setItem("access_token", res.data.access_token);
      if (res.data.refresh_token) localStorage.setItem("refresh_token", res.data.refresh_token);
      localStorage.setItem("isAuthenticated", "true");
      try {
        const userRes = await authApi.getMe();
        localStorage.setItem("user", JSON.stringify(userRes.data));
      } catch { }
      navigate("/dashboard");
    } catch (err) {
      setError("Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{ background: "#0a0d1a" }}
    >
      {/* Animated glow orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full opacity-20 blur-3xl animate-pulse"
          style={{ background: "radial-gradient(circle, #7c3aed, transparent 70%)" }} />
        <div className="absolute -bottom-40 -right-40 w-[500px] h-[500px] rounded-full opacity-15 blur-3xl animate-pulse"
          style={{ background: "radial-gradient(circle, #06b6d4, transparent 70%)", animationDelay: "2s" }} />
        {/* Grid pattern */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: "linear-gradient(rgba(255,255,255,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.5) 1px, transparent 1px)",
            backgroundSize: "40px 40px"
          }} />
      </div>

      {/* Login Card */}
      <form
        onSubmit={handleSubmit}
        className="relative w-full max-w-md mx-4 p-8 rounded-2xl animate-fade-in"
        style={{
          background: "rgba(19,25,41,0.85)",
          border: "1px solid rgba(139,92,246,0.2)",
          backdropFilter: "blur(24px)",
          boxShadow: "0 0 80px rgba(124,58,237,0.1), 0 32px 80px rgba(0,0,0,0.5)",
        }}
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl mx-auto mb-4 flex items-center justify-center"
            style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)", boxShadow: "0 8px 24px rgba(124,58,237,0.4)" }}>
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-extrabold text-white mb-1">Welcome Back</h1>
          <p className="text-sm text-slate-400">Sign in to Project Scoping Bot</p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 px-4 py-3 rounded-xl text-sm text-red-400"
            style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)" }}>
            {error}
          </div>
        )}

        {/* Fields */}
        <div className="space-y-4 mb-5">
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Email</label>
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full"
              style={{ marginBottom: 0 }}
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Password</label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full"
              style={{ marginBottom: 0 }}
            />
          </div>
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 px-4 rounded-xl font-semibold text-white text-sm transition-all disabled:opacity-50 mb-5"
          style={{
            background: "linear-gradient(135deg, #7c3aed, #06b6d4)",
            boxShadow: "0 4px 24px rgba(124,58,237,0.4)",
          }}
          onMouseOver={e => e.currentTarget.style.opacity = "0.9"}
          onMouseOut={e => e.currentTarget.style.opacity = "1"}
        >
          {loading ? "Signing in..." : "Sign In →"}
        </button>

        {/* Links */}
        <div className="flex justify-between text-sm">
          <Link to="/register" className="text-violet-400 hover:text-violet-300 font-medium transition-colors">
            Create Account
          </Link>
          <Link to="/forgot-password" className="text-slate-500 hover:text-slate-300 transition-colors">
            Forgot Password?
          </Link>
        </div>
      </form>
    </div>
  );
}
