import { useEffect, useState } from 'react'
import { getModels, getPipeline } from '../utils/api'
import ModelMetricsTable from '../components/ModelMetricsTable'

export default function Models() {
  const [metrics,  setMetrics]  = useState(null)
  const [status,   setStatus]   = useState(null)
  const [retraining, setRetraining] = useState(false)

  useEffect(() => {
    getModels.performance().then(r => setMetrics(r.data)).catch(() => {})
    getPipeline.status().then(r => setStatus(r.data)).catch(() => {})
  }, [])

  const handleRetrain = async () => {
    setRetraining(true)
    try {
      await getPipeline.retrain()
      alert('Retraining started in background. Check terminal logs.')
    } catch(e) {
      alert('Failed to trigger retrain')
    } finally {
      setRetraining(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Model Performance</h1>
        <button onClick={handleRetrain} disabled={retraining}
          className="bg-green-700 hover:bg-green-600 disabled:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium">
          {retraining ? 'Starting...' : 'Retrain All Models'}
        </button>
      </div>

      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Latest Data',    value: status.data_latest_date },
            { label: 'Total Rates',    value: status.total_rates?.toLocaleString() },
            { label: 'Active Models',  value: status.active_models?.join(', ') || 'None' },
            { label: 'Models Trained', value: status.models_trained ? '✓ Yes' : '✗ No' },
          ].map(s => (
            <div key={s.label} className="bg-slate-800 rounded-xl p-4 border border-slate-700">
              <p className="text-slate-400 text-xs uppercase">{s.label}</p>
              <p className="text-white font-semibold mt-1 text-sm">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <ModelMetricsTable metrics={metrics} />
    </div>
  )
}