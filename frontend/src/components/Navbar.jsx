import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Home, LayoutDashboard, History, Cpu, BookOpen, Code, Menu, X } from "lucide-react";

export default function Navbar() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);

  const links = [
    { to: "/", label: "Home", icon: Home },
    { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/history", label: "History", icon: History },
    { to: "/models", label: "Models", icon: Cpu },
    { to: "/api-docs", label: "API Docs", icon: Code },
    { to: "/about", label: "About", icon: BookOpen },
  ];

  return (
    <nav className="bg-slate-900/80 backdrop-blur border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
        {/* BRAND */}
        <Link to="/" className="flex items-center gap-2">
          <span className="text-xl font-bold text-white tracking-tight">
            Kwacha<span className="text-emerald-400">Cast</span>
          </span>
          <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-medium">v1.0</span>
        </Link>

        {/* DESKTOP LINKS */}
        <div className="hidden md:flex items-center gap-1">
          {links.map(l => {
            const Icon = l.icon
            const isActive = pathname === l.to
            return (
              <Link
                key={l.to}
                to={l.to}
                className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  isActive
                    ? 'bg-slate-800 text-emerald-400'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/50'
                }`}
              >
                <Icon className="w-4 h-4" />
                {l.label}
              </Link>
            )
          })}
        </div>

        {/* MOBILE BUTTON */}
        <button onClick={() => setOpen(!open)} className="md:hidden text-slate-400 hover:text-white">
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* MOBILE MENU */}
      {open && (
        <div className="md:hidden border-t border-slate-800 px-4 py-3 space-y-1">
          {links.map(l => {
            const Icon = l.icon
            const isActive = pathname === l.to
            return (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  isActive ? 'bg-slate-800 text-emerald-400' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Icon className="w-4 h-4" />
                {l.label}
              </Link>
            )
          })}
        </div>
      )}
    </nav>
  );
}