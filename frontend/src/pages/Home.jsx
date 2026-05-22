import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, BarChart3, AlertCircle, Zap } from 'lucide-react'
import { getLatestRate } from '../utils/api'   // ← reuse the same helper

export default function Home() {
  const [latestRate, setLatestRate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    async function fetchLatestRate() {
      try {
        const data = await getLatestRate()    // ← no hard‑coded URL
        setLatestRate(data)
      } catch (err) {
        console.error('Home fetch error:', err)
        setError(err.message || 'Failed to load data')
      } finally {
        setLoading(false)
      }
    }
    fetchLatestRate()
  }, [])

  const features = [
    { icon: TrendingUp, title: 'Accurate Forecasts', description: 'Advanced models: ARIMA, ARIMAX, ensemble.' },
    { icon: BarChart3, title: 'Historical Analysis', description: 'Long-term MWK/USD trends and correlations.' },
    { icon: Zap, title: 'Real-time Updates', description: 'Daily data refresh from multiple sources.' },
    { icon: AlertCircle, title: 'Decision Support', description: 'Built for businesses, researchers, and individuals.' },
  ]

  return (
    <div className="bg-slate-950 min-h-screen text-white">
      {/* HERO */}
      <section className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-20">
          <div className="grid lg:grid-cols-2 gap-14 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-2 rounded-full mb-6 text-sm">
                Live MWK/USD Monitoring
              </div>
              <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6">
                Malawi Kwacha Forecasting System
              </h1>
              <p className="text-slate-400 text-lg leading-relaxed mb-8">
                Professional exchange rate forecasting platforms.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link
                  to="/dashboard"
                  className="bg-emerald-600 hover:bg-emerald-700 transition px-6 py-3 rounded-xl font-semibold"
                >
                  Open Dashboard
                </Link>
                <Link
                  to="/about"
                  className="border border-slate-700 hover:border-slate-500 transition px-6 py-3 rounded-xl font-semibold"
                >
                  Learn More
                </Link>
              </div>
            </div>

            {/* Live rate card */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
              <p className="text-slate-400 mb-3">Latest Exchange Rate</p>
              {loading ? (
                <div className="animate-pulse">
                  <div className="h-14 bg-slate-800 rounded w-48 mb-4"></div>
                  <div className="h-5 bg-slate-800 rounded w-32"></div>
                </div>
              ) : error ? (
                <div className="text-red-400">Failed to load data</div>
              ) : (
                <>
                  <h2 className="text-6xl font-bold mb-4 text-white">
                    {latestRate?.rate?.toFixed(2)}
                  </h2>
                  <p className="text-xl text-slate-300">MWK per USD</p>

                  <div
                    className={`mt-6 text-lg font-semibold ${
                      (latestRate?.daily_return ?? 0) >= 0
                        ? 'text-emerald-400'
                        : 'text-red-400'
                    }`}
                  >
                    {(latestRate?.daily_return ?? 0) >= 0 ? '+' : ''}
                    {latestRate?.daily_return?.toFixed(3) ?? '—'}%
                  </div>

                  <div className="mt-6 space-y-2 text-sm text-slate-400">
                    <p>
                      Date:{' '}
                      <span className="text-slate-300 ml-2">
                        {latestRate?.date ?? '—'}
                      </span>
                    </p>
                    <p>
                      Source:{' '}
                      <span className="text-slate-300 ml-2">
                        {latestRate?.source ?? '—'}
                      </span>
                      {latestRate?.stale && (
                        <span className="ml-2 text-amber-400 text-xs">
                          (stale)
                        </span>
                      )}
                    </p>
                    <p>
                      Interpolated:{' '}
                      <span className="text-slate-300 ml-2">
                        {latestRate?.is_interpolated ? 'Yes' : 'No'}
                      </span>
                    </p>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold mb-4">Platform Capabilities</h2>
            <p className="text-slate-400 max-w-3xl mx-auto">
              Advanced forecasting infrastructure for Malawi's economic
              intelligence.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, idx) => {
              const Icon = feature.icon
              return (
                <div
                  key={idx}
                  className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-emerald-500/50 transition-all"
                >
                  <Icon className="w-12 h-12 text-emerald-500 mb-5" />
                  <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                  <p className="text-slate-400 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* INFO SECTION */}
      <section className="bg-slate-900 border-y border-slate-800 py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-3 gap-12">
            <div>
              <h3 className="text-2xl font-bold mb-4">
                Why Forecasting Matters
              </h3>
              <p className="text-slate-400 leading-relaxed">
                Exchange rate fluctuations affect imports, inflation, fuel
                prices, and household budgets.
              </p>
            </div>
            <div>
              <h3 className="text-2xl font-bold mb-4">Forecasting Models</h3>
              <p className="text-slate-400 leading-relaxed">
                
              </p>
            </div>
            <div>
              <h3 className="text-2xl font-bold mb-4">Research Driven</h3>
              <p className="text-slate-400 leading-relaxed">
                Built for Malawi’s unique economic environment and
                decision‑making needs.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA SECTION */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="bg-gradient-to-r from-blue-900/30 to-slate-800 border-2 border-blue-500/30 rounded-2xl p-8 sm:p-12 text-center">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Make Informed Decisions?
          </h2>
          <p className="text-lg text-slate-400 mb-8 max-w-2xl mx-auto">
            Explore interactive dashboards, 7/30-day forecasts, historical
            trends, and model performance.
          </p>
          <Link
            to="/dashboard"
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-3 rounded-lg font-semibold transition-colors inline-block"
          >
            Go to Dashboard
          </Link>
        </div>
      </section>
    </div>
  )
}