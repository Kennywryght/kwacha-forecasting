with open('frontend/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the TrustChart function and replace it
old_start = 'function TrustChart({ history, forecasts }) {'
old_end = '// ── Forecast Outlook'

# Extract the old TrustChart function
start_idx = content.find(old_start)
end_idx = content.find(old_end, start_idx)

new_trust = '''function TrustChart({ history, forecasts }) {
  if (!history?.length) return null;
  
  // Convert forecast data to a lookup map by date
  const forecastMap = {};
  if (forecasts?.forecasts) {
    // New format from /7-day endpoint
    forecasts.forecasts.forEach(f => {
      const d = String(f.target_date).slice(0, 10);
      forecastMap[d] = Number(f.predicted_rate?.toFixed(2));
    });
  } else if (forecasts?.prediction && forecasts?.dates) {
    // Old format from useDashboardData
    forecasts.dates.forEach((d, i) => {
      const dateStr = String(d).slice(0, 10);
      forecastMap[dateStr] = Number(forecasts.prediction[i]?.toFixed(2));
    });
  }
  
  const data = history.slice(-30).map((h) => {
    const histDate = String(h.date).slice(0, 10);
    return {
      date: fmtDate(h.date),
      actual: Number(h.rate?.toFixed(2)),
      forecasted: forecastMap[histDate] || null,
    };
  });
  
  const hasForecasts = data.some(d => d.forecasted != null);
  
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center gap-2 mb-3"><Shield className="w-4 h-4 text-emerald-400" /><h3 className="text-sm font-semibold text-slate-300">Accuracy & transparency</h3></div>
      <p className="text-xs text-slate-500 mb-4">{hasForecasts ? "Our forecasts (dotted) vs actual rates." : "Historical rates for the last 30 days."}</p>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={4} angle={-30} textAnchor="end" />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }} 
            formatter={(v, name) => v != null ? [MWK , name === 'actual' ? 'Actual rate' : 'Our forecast'] : ['N/A', name]} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#34d399" strokeWidth={2} dot={false} name="Actual rate" />
          {hasForecasts && <Line type="monotone" dataKey="forecasted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} name="Our forecast" connectNulls={false} />}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}'''

content = content[:start_idx] + new_trust + '\n\n' + content[end_idx:]

with open('frontend/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('TrustChart completely replaced')
