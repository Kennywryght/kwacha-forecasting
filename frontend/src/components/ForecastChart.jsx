import React from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts'

export default function ForecastChart({
  forecasts,
  historicalData = [],
  horizon,
}) {
  if (!forecasts?.dates || !forecasts?.prediction) {
    return (
      <div className="bg-stone-900/60 rounded-2xl border border-stone-700/60 backdrop-blur p-5">
        <p className="text-stone-400">
          No forecast data yet. Generate a forecast.
        </p>
      </div>
    )
  }

  // Historical actual values
  const historical = historicalData.map((item) => ({
    date: item.date,
    actual: item.rate,
  }))

  // Forecast values
  const future = forecasts.dates.map((date, i) => ({
    date,
    forecast: forecasts.prediction[i],
    ...(forecasts.lower_95 && {
      lower_95: forecasts.lower_95[i],
    }),
    ...(forecasts.upper_95 && {
      upper_95: forecasts.upper_95[i],
    }),
  }))

  // Merge both datasets
  const data = [...historical, ...future]

  return (
    <div className="bg-stone-900/60 rounded-2xl border border-stone-700/60 backdrop-blur p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-stone-100">
            Exchange Rate Forecast
          </h3>

          <p className="text-sm text-stone-400 mt-1">
            Historical vs Predicted MWK/USD Exchange Rates
          </p>
        </div>

        <div className="text-sm text-stone-400">
          {horizon}-Day Forecast
        </div>
      </div>

      <ResponsiveContainer width="100%" height={380}>
        <LineChart
          data={data}
          margin={{ top: 10, right: 25, left: 10, bottom: 10 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#2A332D"
          />

          <XAxis
            dataKey="date"
            tick={{ fill: '#8A968D', fontSize: 12 }}
          />

          <YAxis
            tick={{ fill: '#8A968D', fontSize: 12 }}
            domain={['auto', 'auto']}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: '#1A211D',
              border: '1px solid #3D4A41',
              borderRadius: '10px',
              color: '#D2D8D2',
            }}
          />

          <Legend
            wrapperStyle={{
              color: '#cbd5e1',
              paddingTop: '10px',
            }}
          />

          {/* Actual historical values */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke="#E0AC4F"
            strokeWidth={3}
            dot={false}
            name="Actual"
          />

          {/* Forecast values */}
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#D2693C"
            strokeWidth={3}
            strokeDasharray="6 6"
            dot={false}
            name="Forecast"
          />

          {/* Confidence intervals */}
          {forecasts.lower_95 && (
            <>
              <Line
                type="monotone"
                dataKey="lower_95"
                stroke="#fca5a5"
                strokeDasharray="3 3"
                strokeWidth={1}
                dot={false}
                name="95% Lower"
              />

              <Line
                type="monotone"
                dataKey="upper_95"
                stroke="#fca5a5"
                strokeDasharray="3 3"
                strokeWidth={1}
                dot={false}
                name="95% Upper"
              />
            </>
          )}

          <ReferenceLine
            y={0}
            stroke="#3D4A41"
            strokeDasharray="3 3"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}