import { Outlet } from "react-router-dom";
import { useState } from "react";
import Header from "./Header";
import Sidebar from "./Sidebar";

export default function Layout() {
  const [isOpen, setIsOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8fafc] dark:bg-dark-background">
      {/* Sidebar */}
      <Sidebar isOpen={isOpen} setIsOpen={setIsOpen} mobileOpen={mobileOpen} />

      {/* Main Content */}
      <div className="flex flex-col flex-1 h-screen overflow-hidden">
        <Header
          onToggleSidebar={() => setMobileOpen(!mobileOpen)}
          isSidebarOpen={mobileOpen}
        />
        <main className="flex-1 p-6 md:p-8 overflow-y-auto relative bg-[#f8fafc] dark:bg-dark-background">
          <div className="max-w-7xl mx-auto relative z-10 space-y-6">
            <Outlet /> {/* renders nested routes */}
          </div>
        </main>
      </div>
    </div>
  );
}

