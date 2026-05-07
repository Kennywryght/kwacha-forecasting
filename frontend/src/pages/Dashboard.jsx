// src/pages/Dashboard.jsx
import React, { useState } from 'react'
import { useDashboardData } from '../hooks/useForecasts'
import RateCard from '../components/RateCard'
import ForecastChart from '../components/ForecastChart'
import HistoryChart from '../components/HistoryChart'
import ModelMetricsTable from '../components/ModelMetricsTable'
import { getForecasts } from '../utils/api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Area, ComposedChart
} from 'recharts'

// ------------------------------------------
// Mini Components
// ------------------------------------------

function ModelConsensus({ models, latestRate, horizon }) {
  if (!models || !latestRate || models.length === 0) return null
  const directions = models.map(m => {
    const lastPred = m.prediction?.[horizon - 1] ?? m.prediction?.[0] ?? 0
    return lastPred > latestRate ? 'up' : 'down'
  })
  const upCount = directions.filter(d => d === 'up').length
  const downCount = directions.length - upCount
  const consensus = upCount > downCount ? 'Kukwera (Appreciation)' : 'Kutsika (Depreciation)'

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
        Model Consensus
      </h3>
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <span className="text-green-400 text-xl font-bold">{upCount}</span>
          <span className="text-slate-400">Up</span>
          <span className="text-red-400 text-xl font-bold ml-3">{downCount}</span>
          <span className="text-slate-400">Down</span>
        </div>
        <div className="text-right">
          <p className="text-white font-bold text-lg">{consensus}</p>
          <p className="text-slate-400 text-xs">{models.length} models reporting</p>
        </div>
      </div>
    </div>
  )
}

function AnomalyBanner({ anomalies, language }) {
  if (!anomalies || anomalies.length === 0) return null
  const texts = {
    en: { title: 'Recent Anomaly Detected', viewAll: 'View details' },
    ny: { title: 'Zodabwitsa Zapezeka', viewAll: 'Onani zambiri' }
  }
  const t = texts[language] || texts.en

  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-4 backdrop-blur">
      <div className="flex items-start gap-3">
        <span className="text-amber-400 text-xl">⚠️</span>
        <div className="flex-1">
          <h4 className="text-amber-300 font-semibold">{t.title}</h4>
          <p className="text-slate-300 text-sm mt-1">
            {anomalies[0].description || 'Model residuals spiked, possible structural break.'}
          </p>
          <span className="text-xs text-slate-400 mt-2 inline-block">
            {new Date(anomalies[0].detected_at).toLocaleDateString()}
          </span>
        </div>
        <button className="text-amber-300 text-sm hover:underline self-center ml-2">
          {t.viewAll}
        </button>
      </div>
    </div>
  )
}

function FanChart({ forecasts, history, horizon }) {
  if (!forecasts || !forecasts.dates) return null
  const histData = history?.slice(-60)?.map(d => ({ date: d.date, rate: d.rate })) || []
  const fcData = forecasts.dates.map((d, i) => ({
    date: d,
    predicted: forecasts.prediction[i],
    lower_80: forecasts.lower_80?.[i],
    upper_80: forecasts.upper_80?.[i],
    lower_95: forecasts.lower_95?.[i],
    upper_95: forecasts.upper_95?.[i]
  }))

  const lastHist = histData[histData.length - 1]
  const combined = [
    ...histData.map(h => ({ ...h, type: 'actual' })),
    ...(lastHist ? [{ date: lastHist.date, predicted: lastHist.rate, lower_80: lastHist.rate, upper_80: lastHist.rate, lower_95: lastHist.rate, upper_95: lastHist.rate }] : []),
    ...fcData.map(f => ({ ...f, type: 'forecast' }))
  ]

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
        Forecast Fan (80% / 95% Confidence)
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={combined} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 12 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} domain={['auto', 'auto']} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }} />
          <Area type="monotone" dataKey="upper_95" stroke="none" fill="#ef4444" fillOpacity={0.1} />
          <Area type="monotone" dataKey="lower_95" stroke="none" fill="#ef4444" fillOpacity={0.1} />
          <Area type="monotone" dataKey="upper_80" stroke="none" fill="#f97316" fillOpacity={0.15} />
          <Area type="monotone" dataKey="lower_80" stroke="none" fill="#f97316" fillOpacity={0.15} />
          <Line type="monotone" dataKey="rate" stroke="#60a5fa" strokeWidth={2} dot={false} name="Actual" />
          <Line type="monotone" dataKey="predicted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecast" />
          <ReferenceLine y={lastHist?.rate} stroke="#64748b" strokeDasharray="3 3" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function ModelInterpretation({ forecasts, allForecasts, language, horizon, latestRate }) {
  if (!forecasts || !forecasts.prediction || forecasts.prediction.length === 0 || !latestRate) return null
  
  const futureValue = forecasts.prediction[forecasts.prediction.length - 1]
  const diff = futureValue - latestRate
  const direction = diff > 0 ? 'weaken' : 'strengthen'
  const pct = Math.abs((diff / latestRate) * 100).toFixed(2) + '%'
  
  const directionText = language === 'ny'
    ? (direction === 'weaken' ? 'kutsika' : 'kukwera')
    : (direction === 'weaken' ? 'weaken' : 'strengthen')
  
  const summary = language === 'ny'
    ? `M'tsogolo mwa masiku ${horizon}, Kwacha iku${directionText} ndi ${pct}.`
    : `The ${horizon}-day outlook suggests the Kwacha will ${directionText} by ${pct}.`

  const details = language === 'ny'
    ? 'Zochokera ku gulu la ma model a ARIMA, ARIMAX ndi Ensemble.'
    : 'Based on ensemble of ARIMA, ARIMAX, and Ensemble.'

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur mt-4">
      <p className="text-white font-medium">{summary}</p>
      <p className="text-slate-400 text-sm mt-1">{details}</p>
    </div>
  )
}

// ------------------------------------------
// Main Dashboard
// ------------------------------------------
export default function Dashboard() {
  const [horizon, setHorizon] = useState(7)
  const [generating, setGenerating] = useState(false)
  const [lang, setLang] = useState('en')
  const [showModelDetail, setShowModelDetail] = useState(false)

  const { latestRate, forecasts, allForecasts, history, metrics, anomalies, loading } = useDashboardData(horizon)

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await getForecasts.generate(horizon)
      window.location.reload()
    } catch (e) {
      alert('Failed to generate forecasts. Make sure models are trained.')
    } finally {
      setGenerating(false)
    }
  }

  const t = {
    en: { generate: 'Generate Forecasts', genLoad: 'Generating...', horizon: 'Horizon' },
    ny: { generate: 'Pangani Ma Forecast', genLoad: 'Tikupanga...', horizon: 'Nyengo' }
  }[lang] || { generate: 'Generate Forecasts', genLoad: 'Generating...', horizon: 'Horizon' }

  let direction = null, changePct = null
  if (latestRate && forecasts?.prediction?.length) {
    const future = forecasts.prediction[forecasts.prediction.length - 1]
    const diff = future - latestRate.rate
    direction = diff > 0 ? 'up' : 'down'
    changePct = ((diff / latestRate.rate) * 100).toFixed(2)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Header with language toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">
            {lang === 'ny' ? 'Dashibodi ya Mwawi wa Kwacha' : 'Kwacha Forecast Command'}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {lang === 'ny' ? 'Zolosera zogwirizana ndi ARIMA · ARIMAX · ENSEMBLE' : 'Real‑time ensemble forecasts'}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => setLang(l => l === 'en' ? 'ny' : 'en')}
            className="px-3 py-1.5 rounded-lg bg-slate-700 text-white text-xs font-medium hover:bg-slate-600 transition"
          >
            {lang === 'en' ? 'Chichewa' : 'English'}
          </button>
          <select
            value={horizon}
            onChange={e => setHorizon(Number(e.target.value))}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600"
          >
            <option value={1}>{lang === 'ny' ? 'Tsiku Limodzi' : 'Next Day'}</option>
            <option value={7}>{lang === 'ny' ? 'Masiku 7' : '7 Days'}</option>
            <option value={30}>{lang === 'ny' ? 'Masiku 30' : '30 Days'}</option>
          </select>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {generating ? t.genLoad : t.generate}
          </button>
        </div>
      </div>

      <AnomalyBanner anomalies={anomalies} language={lang} />

      {/* Hero Forecast Card */}
      <div className="relative">
        {loading ? (
          <div className="animate-pulse bg-slate-800/60 rounded-2xl h-32" />
        ) : latestRate ? (
          <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <p className="text-slate-400 text-xs uppercase tracking-wider">
                  {lang === 'ny' ? 'Mtengo Wapano' : 'Current Rate'}
                </p>
                <p className="text-3xl font-bold text-white mt-1">
                  {latestRate.rate.toFixed(4)}
                </p>
                <p className="text-slate-500 text-xs">{latestRate.date}</p>
              </div>
              {forecasts?.prediction && (
                <div className="text-right">
                  <p className="text-sm text-slate-400">
                    {lang === 'ny' ? 'Zolosera za masiku' : 'Forecast'} ({horizon}d)
                  </p>
                  <p className="text-2xl font-bold text-white">
                    {forecasts.prediction[forecasts.prediction.length - 1]?.toFixed(4)}
                  </p>
                  <p className={`text-sm font-medium ${direction === 'up' ? 'text-green-400' : 'text-red-400'}`}>
                    {direction === 'up' ? '↗' : '↘'} {changePct}%
                  </p>
                </div>
              )}
              <button
                onClick={() => setShowModelDetail(!showModelDetail)}
                className="text-blue-400 text-xs hover:underline self-start sm:self-center"
              >
                {showModelDetail ? 'Hide models' : 'Show individual models'}
              </button>
            </div>
            {showModelDetail && allForecasts?.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
                {allForecasts.map((model, idx) => (
                  <div key={idx} className="bg-slate-700/40 p-3 rounded-xl border border-slate-600/50">
                    <p className="text-slate-400 text-xs">{model.name}</p>
                    <p className="text-white font-bold">
                      {model.prediction?.[model.prediction.length - 1]?.toFixed(4)}
                    </p>
                    <p className={`text-xs ${model.prediction?.[model.prediction.length - 1] > latestRate.rate ? 'text-green-400' : 'text-red-400'}`}>
                      {model.prediction?.[model.prediction.length - 1] > latestRate.rate ? 'Up' : 'Down'}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : null}
      </div>

      <FanChart forecasts={forecasts} history={history} horizon={horizon} />

      {/* Interactive Sparkline */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-2">
          {lang === 'ny' ? 'Sankhani Nyengo' : 'Tap chart to set horizon'}
        </h3>
        <div className="flex gap-2 text-xs text-slate-400 mb-2">
          <span
            onClick={() => setHorizon(7)}
            className={`cursor-pointer px-2 py-1 rounded ${horizon === 7 ? 'bg-slate-600 text-white' : ''}`}
          >7d</span>
          <span
            onClick={() => setHorizon(14)}
            className={`cursor-pointer px-2 py-1 rounded ${horizon === 14 ? 'bg-slate-600 text-white' : ''}`}
          >14d</span>
          <span
            onClick={() => setHorizon(30)}
            className={`cursor-pointer px-2 py-1 rounded ${horizon === 30 ? 'bg-slate-600 text-white' : ''}`}
          >30d</span>
        </div>
        <ResponsiveContainer width="100%" height={100}>
          <LineChart data={
            forecasts?.dates?.map((d, i) => ({
              date: d,
              prediction: forecasts.prediction[i]
            })) || []
          }>
            <Line type="monotone" dataKey="prediction" stroke="#fbbf24" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ModelConsensus models={allForecasts} latestRate={latestRate?.rate} horizon={horizon} />
        <ModelInterpretation
          forecasts={forecasts}
          allForecasts={allForecasts}
          language={lang}
          horizon={horizon}
          latestRate={latestRate?.rate}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
            {lang === 'ny' ? 'Mbiri Yakale' : 'Historical Rate & Forecast'}
          </h3>
          <HistoryChart history={history} loading={loading} forecasts={forecasts} />
        </div>
        <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
            {lang === 'ny' ? 'Kuyerekeza kwa Model' : 'Model Accuracy'}
          </h3>
          <ModelMetricsTable metrics={metrics} lang={lang} />
        </div>
      </div>
    </div>
  )
}