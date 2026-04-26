export default function ModelMetricsTable({ metrics }) {
  if (!metrics?.models?.length) return (
    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
      <h3 className="text-white font-semibold text-lg mb-2">Model Performance</h3>
      <p className="text-slate-500 text-sm">No model metrics yet. Train models first.</p>
    </div>
  )

  const colors = { arima: '#f59e0b', arimax: '#10b981', lstm: '#a78bfa', ensemble: '#3b82f6' }

  return (
    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
      <h3 className="text-white font-semibold text-lg mb-4">Model Performance</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-slate-400 border-b border-slate-700">
              <th className="text-left py-2 pr-4">Model</th>
              <th className="text-right py-2 pr-4">RMSE</th>
              <th className="text-right py-2 pr-4">MAE</th>
              <th className="text-right py-2 pr-4">MAPE %</th>
              <th className="text-right py-2">R²</th>
            </tr>
          </thead>
          <tbody>
            {metrics.models.map(m => (
              <tr key={m.model_name} className="border-b border-slate-700/50 hover:bg-slate-700/30">
                <td className="py-3 pr-4">
                  <span className="font-semibold uppercase text-xs px-2 py-1 rounded"
                    style={{ backgroundColor: colors[m.model_name] + '30', color: colors[m.model_name] }}>
                    {m.model_name}
                  </span>
                </td>
                <td className="text-right py-3 pr-4 text-slate-300">{m.rmse?.toFixed(2) ?? '—'}</td>
                <td className="text-right py-3 pr-4 text-slate-300">{m.mae?.toFixed(2)  ?? '—'}</td>
                <td className="text-right py-3 pr-4 text-slate-300">{m.mape?.toFixed(2) ?? '—'}%</td>
                <td className="text-right py-3 text-slate-300">{m.r_squared?.toFixed(4) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}