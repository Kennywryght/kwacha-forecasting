import {
  ResponsiveContainer, ComposedChart, Line, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts'

export default function ForecastChart({ forecasts, allForecasts, horizon }) {
  if (!forecasts) return (
    <div className="bg-slate-800 rounded-2xl p-6 flex items-center justify-center h-72">
      <p className="text-slate-500">No forecast data available. Run /api/v1/forecasts/generate</p>
    </div>
  )

  // Merge all model forecasts into one chart dataset
  const ensembleData = forecasts?.forecasts ?? []

  const chartData = ensembleData.map((point, i) => {
    const row = {
      date:     point.target_date,
      ensemble: point.predicted_rate,
      lower:    point.lower_bound,
      upper:    point.upper_bound,
    }
    if (allForecasts?.arima?.forecasts?.[i])  row.arima  = allForecasts.arima.forecasts[i].predicted_rate
    if (allForecasts?.arimax?.forecasts?.[i]) row.arimax = allForecasts.arimax.forecasts[i].predicted_rate
    if (allForecasts?.lstm?.forecasts?.[i])   row.lstm   = allForecasts.lstm.forecasts[i].predicted_rate
    return row
  })

  return (
    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
      <h3 className="text-white font-semibold text-lg mb-4">
        {horizon}-Day Forecast — All Models
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={v => v?.slice(5)} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }}
            domain={['auto', 'auto']}
            tickFormatter={v => v?.toLocaleString()} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(val, name) => [`${val?.toLocaleString()} MWK`, name.toUpperCase()]}
          />
          <Legend wrapperStyle={{ color: '#94a3b8' }} />
          <Area dataKey="upper" fill="#1d4ed820" stroke="none" />
          <Area dataKey="lower" fill="#0f172a"   stroke="none" />
          <Line dataKey="ensemble" stroke="#3b82f6" strokeWidth={2.5} dot={false} name="Ensemble" />
          <Line dataKey="arima"    stroke="#f59e0b" strokeWidth={1.5} dot={false} name="ARIMA"    strokeDasharray="4 2" />
          <Line dataKey="arimax"   stroke="#10b981" strokeWidth={1.5} dot={false} name="ARIMAX"   strokeDasharray="4 2" />
          <Line dataKey="lstm"     stroke="#a78bfa" strokeWidth={1.5} dot={false} name="LSTM"     strokeDasharray="4 2" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}