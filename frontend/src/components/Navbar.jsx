import React, { useState } from "react";
import { useLanguage } from "../context/LanguageContext";
import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);

  const { lang, setLang } = useLanguage();

  const links = [
    { to: "/home", label: lang === "ny" ? "Kunyumba" : "Home" },
    { to: "/", label: lang === "ny" ? "Dashibodi" : "Dashboard" },
    { to: "/history", label: lang === "ny" ? "Mbiri" : "History" },
    { to: "/models", label: lang === "ny" ? "Ma Model" : "Models" },
    { to: "/api-docs", label: "API Docs" },
    { to: "/about", label: lang === "ny" ? "Za ife" : "About" },
  ];

  const active =
    "text-blue-400 font-semibold px-3 py-1 rounded-md";
  const inactive =
    "text-slate-300 hover:text-white px-3 py-1 rounded-md";

  return (
    <nav className="bg-slate-900 border-b border-slate-700 px-4 py-3">

      <div className="flex items-center justify-between">

        {/* BRAND */}
        <h1 className="text-xl font-bold text-white">
          KwachaCast
        </h1>

        {/* DESKTOP LINKS */}
        <div className="hidden md:flex items-center gap-3">

          {links.map(l => (
            <Link
              key={l.to}
              to={l.to}
              className={pathname === l.to ? active : inactive}
            >
              {l.label}
            </Link>
          ))}

          {/* ✅ LANGUAGE TOGGLE BUTTON (THIS IS WHERE IT GOES) */}
          <button
            onClick={() => setLang(lang === "en" ? "ny" : "en")}
            className="text-xs px-3 py-1 bg-slate-700 rounded-md text-white ml-2"
          >
            {lang === "en" ? "NY" : "EN"}
          </button>

        </div>

        {/* MOBILE BUTTON */}
        <button
          onClick={() => setOpen(!open)}
          className="md:hidden text-slate-300"
        >
          ☰
        </button>
      </div>

      {/* MOBILE MENU */}
      {open && (
        <div className="md:hidden mt-3 flex flex-col gap-2">

          {links.map(l => (
            <Link
              key={l.to}
              to={l.to}
              onClick={() => setOpen(false)}
              className="text-slate-300 hover:text-white px-2 py-1"
            >
              {l.label}
            </Link>
          ))}

          {/* MOBILE LANGUAGE BUTTON */}
          <button
            onClick={() => setLang(lang === "en" ? "ny" : "en")}
            className="text-xs px-3 py-1 bg-slate-700 rounded-md text-white w-fit mt-2"
          >
            {lang === "en" ? "NY" : "EN"}
          </button>

        </div>
      )}

    </nav>
  );
}