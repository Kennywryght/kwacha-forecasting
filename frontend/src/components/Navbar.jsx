import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const { pathname } = useLocation();

  const links = [
    { to: "/", label: "Dashboard" },
    { to: "/history", label: "History" },
    { to: "/models", label: "Models" },
    { to: "/docs", label: "API Docs", href: "http://localhost:8000/docs" },
  ];

  const activeLinkStyle = "text-blue-600 font-bold px-3 py-1 rounded-full hover:bg-blue-50";
  const inactiveLinkStyle = "text-gray-500 font-medium px-3 py-1 rounded-full hover:text-gray-500";

  return (
    <nav className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-bold text-blue-900 tracking-tight">MWK/USD Forecasting System</h1>
          <div className="flex items-center gap-6">
            <Link 
              to="/"
              className={pathname === "/" ? activeLinkStyle : inactiveLinkStyle}
            >
              <TrendingUp size={24} className="text-blue-600" />
            </Link>
            <Link 
              to="/models"
              className={pathname === "/models" ? activeLinkStyle : inactiveLinkStyle}
            >
              <TrendingUp size={24} className="text-gray-400" />
            </Link>
          </div>
        </div>

        {/* Mobile Menu (Hidden on Desktop) */}
        <div className="flex gap-4 md:hidden flex-col"> {/* Show on small screens */}
          <Link to="/" className="text-gray-400">Dashboard</Link>
          <Link to="/history" className="rate-gray-300">History</Link>
          <Link to="/models" className="rate-gray-300">Models</Link>
        </div>
      </nav>
    </nav>
  );
};