import React from "react";
import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const { pathname } = useLocation();

  const links = [
    { to: "/", label: "Dashboard" },
    { to: "/history", label: "History" },
    { to: "/models", label: "Models" },
    { to: "/api-docs", label: "API Docs" },       // internal custom page
  ];

  const activeStyle = "text-blue-600 font-bold px-3 py-1 rounded-full hover:bg-blue-50";
  const inactiveStyle = "text-gray-500 font-medium px-3 py-1 rounded-full hover:text-gray-700";

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-bold text-blue-900 tracking-tight">
            KwachaCast
          </h1>
          <div className="hidden md:flex items-center gap-4">
            {links.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={pathname === link.to ? activeStyle : inactiveStyle}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>

        {/* Mobile Menu */}
        <div className="flex gap-4 md:hidden">
          {links.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className="text-gray-500 text-sm"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}