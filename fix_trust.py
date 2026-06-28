with open('frontend/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

old_trust = '''function TrustChart({ history, forecasts }) {
  if (!history?.length) return null;
  const data = history.slice(-30).map((h, i) => ({
    date: fmtDate(h.date),
    actual: Number(h.rate?.toFixed(2)),
    forecasted: forecasts?.prediction?.[i] ? Number(forecasts.prediction[i]?.toFixed(2)) : null,
  }));
  const hasForecasts = data.some(d => d.forecasted != null);
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center gap-2 mb-3"><Shield className="w-4 h-4 text-emerald-400" /><h3 className="text-sm font-semibold text-slate-300">Accuracy & transparency</h3></div>
      <p className="text-xs text-slate-500 mb-4">Our forecasts (dotted) vs actual rates. 100% of forecasts fall within the predicted range.</p>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={4} angle={-30} textAnchor="end" />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }} formatter={(v, name) => [MWK , name === 'actual' ? 'Actual rate' : 'Our forecast']} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#34d399" strokeWidth={2} dot={false} name="Actual rate" />
          {hasForecasts && <Line type="monotone" dataKey="forecasted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={true} name="Our forecast" connectNulls={false} />}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}'''

new_trust = '''function TrustChart({ history, forecasts }) {
  if (!history?.length) return null;
  
  // Match forecasts to history dates properly
  const data = history.slice(-30).map((h) => {
    const histDate = String(h.date).slice(0, 10);
    // Find matching forecast by date
    let forecastedVal = null;
    if (forecasts?.forecasts) {
      const match = forecasts.forecasts.find(f => String(f.target_date).slice(0, 10) === histDate);
      if (match) forecastedVal = Number(match.predicted_rate?.toFixed(2));
    } else if (forecasts?.prediction && forecasts?.dates) {
      const idx = forecasts.dates.findIndex(d => String(d).slice(0, 10) === histDate);
      if (idx >= 0) forecastedVal = Number(forecasts.prediction[idx]?.toFixed(2));
    }
    return {
      date: fmtDate(h.date),
      actual: Number(h.rate?.toFixed(2)),
      forecasted: forecastedVal,
    };
  });
  
  const hasForecasts = data.some(d => d.forecasted != null);
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center gap-2 mb-3"><Shield className="w-4 h-4 text-emerald-400" /><h3 className="text-sm font-semibold text-slate-300">Accuracy & transparency</h3></div>
      <p className="text-xs text-slate-500 mb-4">{hasForecasts ? "Our forecasts (dotted) vs actual rates." : "Historical exchange rates for the last 30 days."}</p>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={4} angle={-30} textAnchor="end" />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }} 
            formatter={(v, name) => [MWK , name === 'actual' ? 'Actual rate' : (name === 'forecasted' ? 'Our forecast' : name)]} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#34d399" strokeWidth={2} dot={false} name="Actual rate" />
          {hasForecasts && <Line type="monotone" dataKey="forecasted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} name="Our forecast" connectNulls={false} />}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}'''

content = content.replace(old_trust, new_trust)

with open('frontend/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed TrustChart')
