import { Link, useLocation } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'

export default function Navbar() {
  const { pathname } = useLocation()

  const links = [
    { to: '/',        label: 'Dashboard' },
    { to: '/history', label: 'History'   },
    { to: '/models',  label: 'Models'    },
  ]

  return (
    <nav className="bg-slate-900 border-b border-slate-700 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="text-blue-400" size={24} />
          <span className="text-white font-bold text-lg">MWK/USD Forecast</span>
        </div>
        <div className="flex gap-6">
          {links.map(l => (
            <Link
              key={l.to}
              to={l.to}
              className={`text-sm font-medium transition-colors ${
                pathname === l.to
                  ? 'text-blue-400 border-b-2 border-blue-400 pb-1'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  )
}