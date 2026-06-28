import React, { useState, useEffect } from "react";
import { getForecasts, getModelMetrics, getRateStats, getForecastAccuracy } from "../utils/api";
import { RefreshCw, Loader2, TrendingUp, BarChart3, Shield, Zap, Activity, Database, Clock, Cpu } from "lucide-react";

function StatusBadge({ status }) {
  const colors = {
    success: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    error: "bg-red-500/20 text-red-400 border-red-500/30",
    info: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  };
  return <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${colors[status] || colors.info}`}>{status}</span>;
}

function StatCard({ icon: Icon, title, value, subtitle, color }) {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-start justify-between mb-3"><p className="text-slate-400 text-xs uppercase tracking-wider">{title}</p><Icon className={`w-5 h-5 ${color}`} /></div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function ModelMetricsTable({ metrics }) {
  if (!metrics?.length) return null;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="border-b border-slate-700"><th className="text-left py-3 px-4 font-semibold text-slate-300">Model</th><th className="text-right py-3 px-4 font-semibold text-slate-300">MAPE</th><th className="text-right py-3 px-4 font-semibold text-slate-300">RMSE</th><th className="text-right py-3 px-4 font-semibold text-slate-300">MAE</th><th className="text-center py-3 px-4 font-semibold text-slate-300">Status</th></tr></thead>
        <tbody>
          {metrics.map((m, i) => (
            <tr key={i} className="border-b border-slate-700/50 hover:bg-slate-700/30">
              <td className="py-3 px-4 font-medium text-white uppercase">{m.model_name}</td>
              <td className="text-right py-3 px-4 text-slate-300">{m.mape?.toFixed(4)}%</td>
              <td className="text-right py-3 px-4 text-slate-300">{m.rmse?.toFixed(2)}</td>
              <td className="text-right py-3 px-4 text-slate-300">{m.mae?.toFixed(2)}</td>
              <td className="text-center py-3 px-4"><StatusBadge status={m.mape < 1 ? "success" : m.mape < 5 ? "warning" : "error"} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ActivityLog({ activities }) {
  if (!activities?.length) return null;
  return (
    <div className="space-y-2 max-h-64 overflow-y-auto">
      {activities.map((a, i) => (
        <div key={i} className="flex items-start gap-3 p-2 bg-slate-700/30 rounded-lg">
          <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${a.type === 'success' ? 'bg-emerald-400' : a.type === 'error' ? 'bg-red-400' : 'bg-blue-400'}`} />
          <div><p className="text-xs text-slate-300">{a.message}</p><p className="text-xs text-slate-500">{a.time}</p></div>
        </div>
      ))}
    </div>
  );
}

export default function AdminDashboard() {
  const [generating, setGenerating] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [msg, setMsg] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [stats, setStats] = useState(null);
  const [accuracy, setAccuracy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState([{ type: 'info', message: 'Admin dashboard initialized', time: new Date().toLocaleTimeString() }]);

  const addActivity = (type, message) => {
    setActivities(prev => [{ type, message, time: new Date().toLocaleTimeString() }, ...prev].slice(0, 30));
  };

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [m, s, a] = await Promise.all([getModelMetrics(), getRateStats(), getForecastAccuracy()]);
      if (m) setMetrics(m);
      if (s) setStats(s);
      if (a) setAccuracy(a);
    } catch { addActivity('error', 'Failed to fetch data'); }
    setLoading(false);
  };

  useEffect(() => { fetchAll(); }, []);

  const handleGenerateAll = async () => {
    setGenerating(true); setMsg("Generating all forecasts...");
    addActivity('info', 'Starting forecast generation (1d, 7d, 30d)');
    try {
      await getForecasts.generate(1); await getForecasts.generate(7); await getForecasts.generate(30);
      addActivity('success', 'All forecasts generated');
      setMsg("✅ All forecasts generated!"); await fetchAll();
    } catch { addActivity('error', 'Generation failed'); setMsg("❌ Failed"); }
    setTimeout(() => { setGenerating(false); setMsg(null); }, 3000);
  };

  const handleGenerateSingle = async (horizon) => {
    try {
      await getForecasts.generate(horizon);
      addActivity('success', `Generated ${horizon}-day forecasts`);
      setMsg(`✅ ${horizon}-day done!`); setTimeout(() => setMsg(null), 2000);
    } catch { addActivity('error', `Failed: ${horizon}-day`); }
  };

  const handleRetrain = async () => {
    setRetraining(true); setMsg("Retraining all models... (5+ min)");
    addActivity('info', 'Model retraining started');
    try {
      await getForecasts.retrain();
      addActivity('success', 'All models retrained');
      setMsg("✅ Models retrained!"); await fetchAll();
    } catch { addActivity('error', 'Retraining failed'); setMsg("❌ Failed"); }
    setTimeout(() => { setRetraining(false); setMsg(null); }, 3000);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold text-white">Admin Dashboard</h1><p className="text-slate-400 text-sm mt-1">Monitor & manage the forecasting system</p></div>
        <button onClick={fetchAll} disabled={loading} className="text-slate-400 hover:text-white text-sm flex items-center gap-1"><RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />Refresh</button>
      </div>

      {msg && <div className={`rounded-xl p-3 text-sm ${msg.includes('✅') ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : msg.includes('❌') ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-blue-500/10 border border-blue-500/20 text-blue-400'}`}>{msg}</div>}

      {/* Quick Actions */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Zap className="w-4 h-4 text-yellow-400" />Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button onClick={handleGenerateAll} disabled={generating} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}Generate All
          </button>
          <button onClick={() => handleGenerateSingle(1)} className="bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg font-medium transition">1-Day</button>
          <button onClick={() => handleGenerateSingle(7)} className="bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg font-medium transition">7-Day</button>
          <button onClick={() => handleGenerateSingle(30)} className="bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg font-medium transition">30-Day</button>
          <button onClick={handleRetrain} disabled={retraining} className="bg-amber-600 hover:bg-amber-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
            {retraining ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}Retrain All
          </button>
        </div>
      </div>

      {/* Stats */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Database} title="Total Records" value={stats?.current ? "---" : stats?.total_rates || "---"} subtitle="Exchange rates" color="text-blue-400" />
          <StatCard icon={TrendingUp} title="Latest Rate" value={stats?.current ? `MWK ${stats.current.toFixed(2)}` : "---"} subtitle="Current" color="text-emerald-400" />
          <StatCard icon={Cpu} title="Active Models" value={metrics?.length || 0} subtitle="Loaded" color="text-purple-400" />
          <StatCard icon={Shield} title="Accuracy" value={accuracy?.avg_error_pct ? `${accuracy.avg_error_pct}%` : "---"} subtitle={`${accuracy?.comparisons?.length || 0} pts`} color="text-emerald-400" />
        </div>
      )}

      {/* Model Performance */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-blue-400" />Model Performance</h3>
        {loading ? <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-emerald-400 animate-spin" /></div> : <ModelMetricsTable metrics={metrics} />}
      </div>

      {/* Rate Stats + Accuracy */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Rate Statistics</h3>
            {stats && (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><p className="text-slate-400 text-xs">7-day range</p><p className="text-white font-medium">{stats.min_7d?.toFixed(2)} – {stats.max_7d?.toFixed(2)}</p></div>
                <div><p className="text-slate-400 text-xs">7-day change</p><p className={`font-medium ${stats.change_7d > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{stats.change_7d > 0 ? '+' : ''}{stats.change_7d?.toFixed(2)} ({stats.change_pct_7d?.toFixed(2)}%)</p></div>
                <div><p className="text-slate-400 text-xs">30-day range</p><p className="text-white font-medium">{stats.min_30d?.toFixed(2)} – {stats.max_30d?.toFixed(2)}</p></div>
                <div><p className="text-slate-400 text-xs">30-day avg</p><p className="text-white font-medium">{stats.avg_30d?.toFixed(2)}</p></div>
              </div>
            )}
          </div>
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Forecast Accuracy</h3>
            {accuracy?.comparisons?.length ? (
              <div className="grid grid-cols-2 gap-3 text-sm mb-3">
                <div><p className="text-slate-400 text-xs">Avg Error</p><p className="text-white font-medium">{accuracy.avg_error_mwk} MWK</p></div>
                <div><p className="text-slate-400 text-xs">Error Rate</p><p className="text-white font-medium">{accuracy.avg_error_pct}%</p></div>
                <div><p className="text-slate-400 text-xs">Within Range</p><p className="text-emerald-400 font-bold">{accuracy.within_range_pct}%</p></div>
                <div><p className="text-slate-400 text-xs">Data Points</p><p className="text-white font-medium">{accuracy.comparisons.length}</p></div>
              </div>
            ) : <p className="text-slate-500 text-sm">No historical comparisons yet.</p>}
          </div>
        </div>
      )}

      {/* Activity Log */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Clock className="w-4 h-4 text-purple-400" />Activity Log</h3>
        <ActivityLog activities={activities} />
      </div>
    </div>
  );
}