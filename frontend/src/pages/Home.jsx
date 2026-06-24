import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, BarChart3, Zap, Shield, ArrowRight, RefreshCw } from 'lucide-react'

// Fetch live rate from free API - no backend needed
const LIVE_RATE_URL = 'https://open.er-api.com/v6/latest/USD'

export default function Home() {
  const [liveRate, setLiveRate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchLiveRate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(LIVE_RATE_URL)
      const data = await res.json()
      if (data?.rates?.MWK) {
        setLiveRate({
          rate: data.rates.MWK,
          date: data.time_last_update_utc?.split(' ')[0] || new Date().toISOString().split('T')[0],
          source: 'Open Exchange Rates',
        })
      } else {
        throw new Error('No MWK rate')
      }
    } catch (err) {
      setError('Unable to fetch live rate')
      // Fallback: try backend
      try {
        const res = await fetch('https://kwachacast-api.onrender.com/api/v1/rates/latest')
        const data = await res.json()
        if (data?.rate) setLiveRate(data)
      } catch {}
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLiveRate() }, [])

  const features = [
    { icon: TrendingUp, title: 'AI-Powered Forecasts', description: 'ARIMA, ARIMAX & Prophet ensemble models trained on 13+ years of MWK/USD data.' },
    { icon: BarChart3, title: 'Historical Analysis', description: 'Interactive charts from 2013 to present with macroeconomic indicators.' },
    { icon: Zap, title: 'Live Rate Updates', description: 'Real-time exchange rate from global currency APIs, refreshed on demand.' },
    { icon: Shield, title: 'Trust & Transparency', description: 'Compare forecasts against actual rates. See model accuracy metrics.' },
  ]

  return (
    <div className="min-h-screen">
      {/* HERO */}
      <section className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-6 py-16 lg:py-24">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-2 rounded-full mb-6 text-sm font-medium">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></span>
                Live MWK/USD • Malawi Kwacha
              </div>
              <h1 className="text-4xl lg:text-6xl font-bold leading-tight mb-6">
                Kwacha<span className="text-emerald-400">Cast</span>
              </h1>
              <p className="text-slate-400 text-lg leading-relaxed mb-8">
                Professional exchange rate forecasting for the Malawi Kwacha. 
                Powered by ensemble machine learning models trained on 13+ years of data.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link to="/dashboard" className="bg-emerald-600 hover:bg-emerald-500 transition px-6 py-3 rounded-xl font-semibold flex items-center gap-2">
                  Open Dashboard <ArrowRight className="w-4 h-4" />
                </Link>
                <Link to="/about" className="border border-slate-600 hover:border-slate-400 transition px-6 py-3 rounded-xl font-semibold">
                  Learn More
                </Link>
              </div>
            </div>

            {/* LIVE RATE CARD */}
            <div className="bg-slate-900 border border-slate-700 rounded-3xl p-8 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <p className="text-slate-400 text-sm uppercase tracking-wider">Live Exchange Rate</p>
                <button onClick={fetchLiveRate} className="text-slate-500 hover:text-white transition" title="Refresh">
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
              
              {loading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-14 bg-slate-800 rounded w-48"></div>
                  <div className="h-4 bg-slate-800 rounded w-32"></div>
                </div>
              ) : error && !liveRate ? (
                <div className="text-red-400 text-sm">{error}</div>
              ) : (
                <>
                  <h2 className="text-5xl lg:text-6xl font-bold text-white mb-2">
                    {liveRate?.rate?.toFixed(2)}
                  </h2>
                  <p className="text-lg text-slate-300 mb-4">MWK per USD</p>
                  <div className="space-y-2 text-sm text-slate-400">
                    <p>Source: <span className="text-slate-300">{liveRate?.source || '—'}</span></p>
                    <p>Updated: <span className="text-slate-300">{liveRate?.date || '—'}</span></p>
                  </div>
                  <p className="text-xs text-slate-500 mt-4">
                    * Rate sourced from open.er-api.com. For reference only.
                  </p>
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
            <h2 className="text-3xl lg:text-4xl font-bold mb-4">Platform Features</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Built for economists, businesses, and researchers who need reliable Kwacha exchange rate intelligence.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, idx) => {
              const Icon = feature.icon
              return (
                <div key={idx} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-emerald-500/30 transition-all group">
                  <Icon className="w-10 h-10 text-emerald-500 mb-4 group-hover:scale-110 transition" />
                  <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* TRUST SECTION */}
      <section className="bg-slate-900 border-y border-slate-800 py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">Why Trust KwachaCast?</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              Our models are continuously evaluated against real market data to ensure accuracy and reliability.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 text-center">
            {[
              { value: '13+', label: 'Years of Historical Data' },
              { value: '4', label: 'Ensemble ML Models' },
              { value: '99.9%', label: 'API Uptime' },
            ].map((stat, i) => (
              <div key={i}>
                <p className="text-4xl font-bold text-emerald-400">{stat.value}</p>
                <p className="text-slate-400 mt-2">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Explore the Dashboard?</h2>
          <p className="text-slate-400 mb-8">
            View 7-day and 30-day forecasts, historical trends, and model performance metrics.
          </p>
          <Link to="/dashboard" className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-4 rounded-xl font-semibold text-lg transition inline-flex items-center gap-2">
            Launch Dashboard <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  )
}