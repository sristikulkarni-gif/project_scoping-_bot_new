import { Outlet } from "react-router-dom";
import { useState } from "react";
import Header from "./Header";
import Sidebar from "./Sidebar";

export default function Layout() {
  const [isOpen, setIsOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "#0a0d1a" }}>
      {/* Sidebar */}
      <Sidebar isOpen={isOpen} setIsOpen={setIsOpen} mobileOpen={mobileOpen} />

      {/* Main Content */}
      <div className="flex flex-col flex-1 h-screen overflow-hidden min-w-0">
        <Header
          onToggleSidebar={() => setMobileOpen(!mobileOpen)}
          isSidebarOpen={mobileOpen}
        />
        <main
          className="flex-1 overflow-y-auto scrollbar-thin"
          style={{ background: "#0a0d1a" }}
        >
          <div className="max-w-7xl mx-auto p-6 md:p-8 space-y-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
