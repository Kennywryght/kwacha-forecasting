import {
  ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip
} from 'recharts'

export default function HistoryChart({ history, loading }) {
  if (loading) return (
    <div className="bg-slate-800 rounded-2xl p-6 animate-pulse h-72" />
  )
  if (!history?.data) return null

  // Sample every 5th point for performance
  const data = history.data.filter((_, i) => i % 5 === 0).map(r => ({
    date: r.date,
    rate: r.rate,
  }))

  return (
    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
      <h3 className="text-white font-semibold text-lg mb-4">
        Historical MWK/USD Rate (1 Year)
      </h3>
      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="rateGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickFormatter={v => v?.slice(0, 7)} interval="preserveStartEnd" />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }}
            domain={['auto', 'auto']}
            tickFormatter={v => v?.toLocaleString()} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            formatter={(val) => [`${val?.toLocaleString()} MWK`, 'Rate']}
          />
          <Area type="monotone" dataKey="rate" stroke="#3b82f6"
            strokeWidth={2} fill="url(#rateGrad)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}