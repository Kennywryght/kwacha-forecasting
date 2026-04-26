import { useState } from 'react'
import { getRates } from '../utils/api'
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip } from 'recharts'

export default function History() {
  const [start, setStart]   = useState('2023-01-01')
  const [end,   setEnd]     = useState(new Date().toISOString().slice(0, 10))
  const [data,  setData]    = useState(null)
  const [loading, setLoading] = useState(false)

  const fetch = async () => {
    setLoading(true)
    try {
      const res = await getRates.history(start, end)
      setData(res.data)
    } catch(e) {
      alert('Failed to load history')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <h1 className="text-2xl font-bold text-white">Historical Rates</h1>

      <div className="flex gap-4 items-end">
        <div>
          <label className="text-slate-400 text-sm block mb-1">Start Date</label>
          <input type="date" value={start} onChange={e => setStart(e.target.value)}
            className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600" />
        </div>
        <div>
          <label className="text-slate-400 text-sm block mb-1">End Date</label>
          <input type="date" value={end} onChange={e => setEnd(e.target.value)}
            className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600" />
        </div>
        <button onClick={fetch}
          className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium">
          {loading ? 'Loading...' : 'Load'}
        </button>
      </div>

      {data && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: 'Total Records', value: data.total },
              { label: 'Latest Rate',  value: `${data.latest_rate?.toLocaleString()} MWK` },
              { label: 'Date Range',   value: `${data.start_date} → ${data.end_date}` },
            ].map(s => (
              <div key={s.label} className="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <p className="text-slate-400 text-xs uppercase">{s.label}</p>
                <p className="text-white font-bold text-lg mt-1">{s.value}</p>
              </div>
            ))}
          </div>

          <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
            <ResponsiveContainer width="100%" height={350}>
              <AreaChart data={data.data}>
                <defs>
                  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickFormatter={v => v?.slice(0, 7)} interval="preserveStartEnd" />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }}
                  tickFormatter={v => v?.toLocaleString()} domain={['auto','auto']} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                  formatter={val => [`${val?.toLocaleString()} MWK`, 'Rate']} />
                <Area type="monotone" dataKey="rate" stroke="#3b82f6" strokeWidth={2} fill="url(#g)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}