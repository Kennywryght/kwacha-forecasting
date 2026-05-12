import React from 'react'

export default function Card({ title, value, subtitle }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4">

      {title && (
        <p className="text-slate-400 text-xs uppercase">
          {title}
        </p>
      )}

      <p className="text-white font-bold text-lg mt-1">
        {value}
      </p>

      {subtitle && (
        <p className="text-slate-500 text-xs mt-1">
          {subtitle}
        </p>
      )}

    </div>
  )
}