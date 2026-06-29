import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp, BarChart3, Zap, Shield, ArrowRight, RefreshCw, Download, Smartphone, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'

const LIVE_RATE_URL = 'https://open.er-api.com/v6/latest/USD'

export default function Home() {
  const [liveRate, setLiveRate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deferredPrompt, setDeferredPrompt] = useState(null)
  const [isInstallable, setIsInstallable] = useState(false)
  const [previousRate, setPreviousRate] = useState(null)
  const { t } = useLanguage()

  // Listen for PWA install prompt
  useEffect(() => {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault()
      setDeferredPrompt(e)
      setIsInstallable(true)
    })
    
    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsInstallable(false)
    }
  }, [])

  const handleInstall = async () => {
    if (!deferredPrompt) return
    deferredPrompt.prompt()
    const { outcome } = await deferredPrompt.userChoice
    if (outcome === 'accepted') {
      setIsInstallable(false)
    }
    setDeferredPrompt(null)
  }

  const fetchLiveRate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(LIVE_RATE_URL)
      const data = await res.json()
      if (data?.rates?.MWK) {
        // Store previous rate before updating
        if (liveRate?.rate) {
          setPreviousRate(liveRate.rate)
        }
        setLiveRate({
          rate: data.rates.MWK,
          date: data.time_last_update_utc?.split(' ')[0] || new Date().toISOString().split('T')[0],
          source: 'Live currency API',
        })
      } else {
        throw new Error('No MWK rate')
      }
    } catch (err) {
      setError('Unable to fetch live rate')
      try {
        const res = await fetch('https://kwachacast-api.onrender.com/api/v1/rates/latest')
        const data = await res.json()
        if (data?.rate) {
          if (liveRate?.rate) {
            setPreviousRate(liveRate.rate)
          }
          setLiveRate(data)
        }
      } catch {}
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchLiveRate() }, [])

  // Calculate rate change
  const getRateChange = () => {
    if (!previousRate || !liveRate?.rate) return null
    const diff = liveRate.rate - previousRate
    const pct = (diff / previousRate) * 100
    return {
      direction: diff > 0.01 ? 'up' : diff < -0.01 ? 'down' : 'stable',
      diff: Math.abs(diff).toFixed(2),
      pct: Math.abs(pct).toFixed(3)
    }
  }

  const rateChange = getRateChange()

  const features = [
    { icon: TrendingUp, title: t('dailyForecasts', { default: 'Daily forecasts' }), description: t('dailyForecastsDesc', { default: 'Next day, 7-day, and 30-day exchange rate predictions updated every business day.' }) },
    { icon: BarChart3, title: t('historicalData', { default: 'Historical data' }), description: t('historicalDataDesc', { default: 'Interactive charts showing MWK/USD rates from 2013 to present.' }) },
    { icon: Zap, title: t('liveRate', { default: 'Live rate' }), description: t('liveRateDesc', { default: 'Real-time exchange rate so you always know the current value of the Kwacha.' }) },
    { icon: Shield, title: t('provenAccuracy', { default: 'Proven accuracy' }), description: t('provenAccuracyDesc', { default: 'Our system achieves 0.30% average error — that is within 5 MWK of the actual rate.' }) },
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
                Know where the Kwacha is heading. Get daily exchange rate forecasts 
                powered by AI, built specifically for Malawi.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link to="/dashboard" className="bg-emerald-600 hover:bg-emerald-500 transition px-6 py-3 rounded-xl font-semibold flex items-center gap-2">
                  {t('openDashboard', { default: 'Open dashboard' })} <ArrowRight className="w-4 h-4" />
                </Link>
                <Link to="/about" className="border border-slate-600 hover:border-slate-400 transition px-6 py-3 rounded-xl font-semibold">
                  {t('learnMore', { default: 'Learn more' })}
                </Link>
                {/* PWA Install Button - Gray */}
                {isInstallable && (
                  <button onClick={handleInstall} className="bg-slate-600 hover:bg-slate-500 transition px-6 py-3 rounded-xl font-semibold flex items-center gap-2">
                    <Download className="w-4 h-4" /> {t('installApp', { default: 'Install App' })}
                  </button>
                )}
              </div>
            </div>

            {/* LIVE RATE CARD - ENHANCED */}
            <div className="bg-slate-900 border border-slate-700 rounded-3xl p-8 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <p className="text-slate-400 text-sm uppercase tracking-wider">{t('liveExchangeRate', { default: 'Live exchange rate' })}</p>
                <button onClick={fetchLiveRate} className="text-slate-500 hover:text-white transition" title="Refresh">
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
              
              {loading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-14 bg-slate-800 rounded w-48"></div>
                  <div className="h-4 bg-slate-800 rounded w-32"></div>
                  <div className="h-4 bg-slate-800 rounded w-40"></div>
                </div>
              ) : error && !liveRate ? (
                <div className="text-red-400 text-sm">{error}</div>
              ) : (
                <>
                  {/* Rate Display with Trend Indicator */}
                  <div className="flex items-baseline gap-3 mb-2">
                    <h2 className="text-5xl lg:text-6xl font-bold text-white">
                      {liveRate?.rate?.toFixed(2)}
                    </h2>
                    {rateChange && (
                      <div className={`flex items-center gap-1 text-sm font-semibold ${
                        rateChange.direction === 'up' ? 'text-red-400' : 
                        rateChange.direction === 'down' ? 'text-emerald-400' : 'text-slate-400'
                      }`}>
                        {rateChange.direction === 'up' && <ArrowUpRight className="w-4 h-4" />}
                        {rateChange.direction === 'down' && <ArrowDownRight className="w-4 h-4" />}
                        {rateChange.direction === 'stable' && <Minus className="w-4 h-4" />}
                        <span>
                          {rateChange.direction === 'up' ? '+' : rateChange.direction === 'down' ? '-' : ''}
                          {rateChange.diff} ({rateChange.pct}%)
                        </span>
                      </div>
                    )}
                  </div>
                  
                  <p className="text-lg text-slate-300 mb-4">MWK per USD</p>
                  
                  {/* Rate Change Details */}
                  {rateChange && (
                    <div className={`mb-4 p-3 rounded-xl text-xs font-medium ${
                      rateChange.direction === 'up' ? 'bg-red-500/10 border border-red-500/20 text-red-400' :
                      rateChange.direction === 'down' ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' :
                      'bg-slate-800 border border-slate-700 text-slate-400'
                    }`}>
                      {rateChange.direction === 'up' && '↗ Kwacha weakening — rate has increased since last update'}
                      {rateChange.direction === 'down' && '↘ Kwacha strengthening — rate has decreased since last update'}
                      {rateChange.direction === 'stable' && '→ Rate is stable — no significant change since last update'}
                    </div>
                  )}
                  
                  <div className="space-y-2 text-sm text-slate-400">
                    <p>{t('source', { default: 'Source' })}: <span className="text-slate-300">{liveRate?.source || '—'}</span></p>
                    <p>{t('updated', { default: 'Updated' })}: <span className="text-slate-300">{liveRate?.date || '—'}</span></p>
                  </div>
                  <p className="text-xs text-slate-500 mt-4">
                    {t('rateDisclaimer', { default: 'Rate sourced from open.er-api.com. For reference only.' })}
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
            <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">{t('whatYouCanDo', { default: 'What you can do' })}</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              {t('simpleTools', { default: 'Simple tools to help you make better decisions about the Kwacha.' })}
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, idx) => {
              const Icon = feature.icon
              return (
                <div key={idx} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 hover:border-emerald-500/30 transition-all group">
                  <Icon className="w-10 h-10 text-emerald-500 mb-4 group-hover:scale-110 transition" />
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
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
            <h2 className="text-3xl font-bold text-white mb-4">{t('whyTrust', { default: 'Why trust KwachaCast?' })}</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">
              {t('builtWithRealData', { default: 'Built with real data and proven methods to give you reliable forecasts.' })}
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 text-center">
            {[
              { value: '0.30%', label: t('avgErrorRate', { default: 'Average error rate' }) },
              { value: '13+', label: t('yearsOfData', { default: 'Years of data' }) },
              { value: t('daily', { default: 'Daily' }), label: t('forecastUpdates', { default: 'Forecast updates' }) },
            ].map((stat, i) => (
              <div key={i}>
                <p className="text-4xl font-bold text-emerald-400">{stat.value}</p>
                <p className="text-slate-400 mt-2">{stat.label}</p>
              </div>
            ))}
          </div>
          
          {/* Mobile App Download Section */}
          <div className="mt-12 bg-slate-800/60 rounded-2xl p-8 border border-slate-700/60 text-center">
            <Smartphone className="w-12 h-12 text-emerald-400 mx-auto mb-4" />
            <h3 className="text-2xl font-bold text-white mb-2">{t('getTheApp', { default: 'Get the App' })}</h3>
            <p className="text-slate-400 mb-6 max-w-lg mx-auto">
              {t('installOnPhone', { default: 'Install KwachaCast on your phone for quick access. No app store needed — just tap the button below.' })}
            </p>
            {isInstallable ? (
              <button onClick={handleInstall} className="bg-slate-600 hover:bg-slate-500 text-white px-8 py-4 rounded-xl font-bold text-lg transition inline-flex items-center gap-2">
                <Download className="w-5 h-5" /> {t('installNow', { default: 'Install KwachaCast' })}
              </button>
            ) : (
              <div className="space-y-3">
                <p className="text-slate-400 text-sm">
                  {t('howToInstall', { default: 'To install: open this site in Chrome, tap the menu (⋮), and select "Add to Home Screen".' })}
                </p>
                <p className="text-slate-500 text-xs">
                  {t('noAppStore', { default: 'No app store required. The app works offline and updates automatically.' })}
                </p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">{t('readyToSee', { default: 'Ready to see the forecasts?' })}</h2>
          <p className="text-slate-400 mb-8">
            {t('viewPredictions', { default: 'View daily, weekly, and monthly predictions for the Malawi Kwacha.' })}
          </p>
          <Link to="/dashboard" className="bg-emerald-600 hover:bg-emerald-500 text-white px-8 py-4 rounded-xl font-semibold text-lg transition inline-flex items-center gap-2">
            {t('openDashboard', { default: 'Open dashboard' })} <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  )
}