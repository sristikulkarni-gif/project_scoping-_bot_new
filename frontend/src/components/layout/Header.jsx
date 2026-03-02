import { useState, useRef, useEffect } from "react";
import { Sun, Moon, LogOut, Menu, X, Bell } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Header({ onToggleSidebar, isSidebarOpen }) {
  const [darkMode, setDarkMode] = useState(true);
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const handleLogout = () => { logout(); window.location.href = "/login"; };

  const toggleDarkMode = () => {
    document.documentElement.classList.toggle("dark");
    setDarkMode(!darkMode);
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target))
        setDropdownOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const initials = user?.username?.[0]?.toUpperCase() || "?";

  return (
    <header
      className="h-14 flex items-center justify-between px-5 shrink-0"
      style={{
        background: "rgba(10,13,26,0.7)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        backdropFilter: "blur(12px)",
      }}
    >
      {/* Mobile sidebar toggle */}
      <button
        onClick={onToggleSidebar}
        className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all"
      >
        {isSidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Right controls */}
      <div className="flex items-center gap-2">

        {/* Theme toggle */}
        <button
          onClick={toggleDarkMode}
          className="w-9 h-9 flex items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-all"
          aria-label="Toggle theme"
        >
          {darkMode ? <Sun className="w-4.5 h-4.5" /> : <Moon className="w-4.5 h-4.5" />}
        </button>

        {/* User avatar */}
        {user && (
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-xl hover:bg-white/10 transition-all"
            >
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
                style={{ background: "linear-gradient(135deg, #7c3aed, #06b6d4)" }}
              >
                {initials}
              </div>
              <span className="hidden md:inline text-sm font-medium text-slate-300">{user.username}</span>
            </button>

            {dropdownOpen && (
              <div
                className="absolute right-0 mt-2 w-48 rounded-2xl overflow-hidden z-50 animate-fade-in"
                style={{
                  background: "#131929",
                  border: "1px solid rgba(255,255,255,0.09)",
                  boxShadow: "0 20px 60px rgba(0,0,0,0.5)"
                }}
              >
                <button
                  onClick={() => { navigate("/profile"); setDropdownOpen(false); }}
                  className="w-full text-left px-4 py-3 text-sm font-medium text-slate-300 hover:text-white hover:bg-white/5 transition-all flex items-center gap-2.5"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-violet-500" />
                  Profile
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-3 text-sm font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-all flex items-center gap-2.5"
                  style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Logout
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
