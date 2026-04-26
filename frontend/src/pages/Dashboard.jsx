import { useState } from 'react'
import { useDashboardData } from '../hooks/useForecasts'
import RateCard from '../components/RateCard'
import ForecastChart from '../components/ForecastChart'
import HistoryChart from '../components/HistoryChart'
import ModelMetricsTable from '../components/ModelMetricsTable'
import { getForecasts } from '../utils/api'

export default function Dashboard() {
  const [horizon, setHorizon] = useState(7)
  const [generating, setGenerating] = useState(false)
  const { latestRate, forecasts, allForecasts, history, metrics, loading } = useDashboardData(horizon)

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

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">MWK/USD Exchange Rate Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Real-time forecasting powered by ARIMA · ARIMAX · LSTM</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={horizon}
            onChange={e => setHorizon(Number(e.target.value))}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600"
          >
            <option value={1}>Next Day</option>
            <option value={7}>7 Days</option>
            <option value={30}>30 Days</option>
          </select>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {generating ? 'Generating...' : 'Generate Forecasts'}
          </button>
        </div>
      </div>

      {/* Live Rate */}
      <RateCard latestRate={latestRate} loading={loading} />

      {/* Forecast Chart */}
      <ForecastChart forecasts={forecasts} allForecasts={allForecasts} horizon={horizon} />

      {/* History + Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <HistoryChart history={history} loading={loading} />
        <ModelMetricsTable metrics={metrics} />
      </div>

    </div>
  )
}