import React from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
} from 'recharts'

export default function HistoryChart({ history, loading, forecasts }) {
  // Debug: see what the component receives
  console.log('HistoryChart received history:', history)

  if (loading) {
    return (
      <div className="text-center text-slate-400 py-10">
        <p>Loading history...</p>
      </div>
    )
  }

  // Ensure history is a valid array with at least one point
  if (!Array.isArray(history) || history.length === 0) {
    return (
      <div className="text-center text-slate-400 py-10">
        <p>No historical data available</p>
      </div>
    )
  }

  // Normalise field names: accept objects with 'date'/'rate' or 'target_date'/'predicted_rate'
  const chartData = history.map(item => ({
    date: item.date || item.target_date,
    rate: item.rate ?? item.predicted_rate,
  }))

  // If after mapping we still have invalid data, show a message
  if (chartData.every(d => d.date == null || d.rate == null)) {
    return (
      <div className="text-center text-slate-400 py-10">
        <p>Historical data format is not recognised</p>
      </div>
    )
  }

  const forecastData = forecasts?.dates?.map((date, i) => ({
    date,
    forecast: forecasts.prediction[i],
  })) || []

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart
        data={chartData}
        margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
      >
        <defs>
          <linearGradient id="rateGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#1d4ed8" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="date"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          tickFormatter={(val) => {
            if (!val) return ''
            const d = new Date(val)
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
          }}
        />
        <YAxis
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          domain={['auto', 'auto']}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: 'none',
            borderRadius: '8px',
            color: '#e2e8f0',
          }}
        />
        <Area
          type="monotone"
          dataKey="rate"
          stroke="#60a5fa"
          strokeWidth={2}
          fill="url(#rateGrad)"
          name="Historical Rate"
        />
        {forecastData.length > 0 && (
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#fbbf24"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            name="Forecast"
            data={forecastData}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  )
}