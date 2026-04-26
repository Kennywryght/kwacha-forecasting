import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function RateCard({ latestRate, loading }) {
  if (loading) return (
    <div className="bg-slate-800 rounded-2xl p-6 animate-pulse">
      <div className="h-4 bg-slate-700 rounded w-1/3 mb-4" />
      <div className="h-10 bg-slate-700 rounded w-1/2" />
    </div>
  )

  if (!latestRate) return null

  const change = latestRate.daily_return ?? 0
  const isUp   = change > 0
  const isDown = change < 0

  return (
    <div className="bg-gradient-to-br from-blue-900 to-slate-800 rounded-2xl p-6 border border-blue-700">
      <p className="text-slate-400 text-sm font-medium uppercase tracking-wider mb-1">
        Live MWK / USD Rate
      </p>
      <div className="flex items-end gap-4 mt-2">
        <h2 className="text-5xl font-bold text-white">
          {latestRate.rate?.toLocaleString('en-MW', { minimumFractionDigits: 2 })}
        </h2>
        <span className="text-slate-400 text-lg mb-1">MWK</span>
      </div>
      <div className="flex items-center gap-2 mt-3">
        {isUp   && <TrendingUp  className="text-red-400"   size={18} />}
        {isDown && <TrendingDown className="text-green-400" size={18} />}
        {!isUp && !isDown && <Minus className="text-slate-400" size={18} />}
        <span className={`text-sm font-medium ${
          isUp ? 'text-red-400' : isDown ? 'text-green-400' : 'text-slate-400'
        }`}>
          {change >= 0 ? '+' : ''}{change?.toFixed(4)}% today
        </span>
        <span className="text-slate-500 text-xs ml-2">as of {latestRate.date}</span>
      </div>
      {latestRate.is_interpolated && (
        <p className="text-yellow-500 text-xs mt-2">⚠ Estimated rate — live data pending</p>
      )}
    </div>
  )
}