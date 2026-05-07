// src/components/RateCard.jsx
import React from 'react'

export default function RateCard({ latestRate, loading }) {
  if (loading) {
    return (
      <div className="bg-slate-800/60 rounded-2xl border border-slate-700/60 backdrop-blur p-5 animate-pulse">
        <div className="h-4 w-28 bg-slate-700 rounded mb-2" />
        <div className="h-8 w-24 bg-slate-700 rounded" />
        <div className="h-3 w-16 bg-slate-700 rounded mt-2" />
      </div>
    )
  }

  if (!latestRate || typeof latestRate.rate !== 'number') {
    return (
      <div className="bg-slate-800/60 rounded-2xl border border-slate-700/60 backdrop-blur p-5">
        <p className="text-slate-400 text-sm">No current rate available</p>
      </div>
    )
  }

  const { rate, date, previous } = latestRate
  const prev = previous ?? rate
  const diff = rate - prev
  const direction = diff > 0 ? 'up' : diff < 0 ? 'down' : 'flat'
  const arrow = direction === 'up' ? '↗' : direction === 'down' ? '↘' : '→'
  const colorClass =
    direction === 'up' ? 'text-green-400' : direction === 'down' ? 'text-red-400' : 'text-slate-400'

  return (
    <div className="bg-slate-800/60 rounded-2xl border border-slate-700/60 backdrop-blur p-5">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wider text-slate-400">
            Current Rate
          </p>
          <p className="text-3xl font-bold text-white mt-1">
            {rate.toFixed(4)}
          </p>
          {date && (
            <p className="text-xs text-slate-500 mt-1">{date}</p>
          )}
        </div>
        <div className={`flex items-center gap-2 text-xl font-bold ${colorClass}`}>
          <span className="text-2xl">{arrow}</span>
          <span>{Math.abs(diff).toFixed(4)}</span>
        </div>
      </div>
    </div>
  )
}