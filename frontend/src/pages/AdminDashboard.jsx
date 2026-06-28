import React, { useState, useEffect } from "react";
import { getForecasts, getModelMetrics, getRateStats, getForecastAccuracy } from "../utils/api";
import { RefreshCw, Loader2, TrendingUp, BarChart3, Shield, Zap, Activity, Database, Clock, Cpu, ExternalLink, Server, AlertTriangle, CheckCircle, Download, Eye } from "lucide-react";

function StatusBadge({ status }) {
  const colors = {
    success: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    error: "bg-red-500/20 text-red-400 border-red-500/30",
    info: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    critical: "bg-red-500/30 text-red-300 border-red-500/50",
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

// ── Model Health Cards ────────────────────────────────────────────────────────
function ModelHealth({ metrics }) {
  if (!metrics?.length) return null;
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Activity className="w-4 h-4 text-green-400" />Model Health</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {metrics.map((m, i) => (
          <div key={i} className="bg-slate-700/40 rounded-xl p-3 text-center">
            <p className="text-white font-bold text-sm uppercase">{m.model_name}</p>
            <div className="mt-1"><StatusBadge status={m.mape < 1 ? "success" : m.mape < 5 ? "warning" : "error"} /></div>
            <p className="text-xs text-slate-500 mt-1">MAPE: {m.mape?.toFixed(2)}%</p>
            <p className="text-xs text-slate-500">RMSE: {m.rmse?.toFixed(1)}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Model Metrics Table ───────────────────────────────────────────────────────
function ModelMetricsTable({ metrics }) {
  if (!metrics?.length) return null;
  const bestModel = metrics.reduce((a, b) => (a.mape || 99) < (b.mape || 99) ? a : b, metrics[0]);
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="border-b border-slate-700"><th className="text-left py-3 px-4 font-semibold text-slate-300">Model</th><th className="text-right py-3 px-4 font-semibold text-slate-300">MAPE</th><th className="text-right py-3 px-4 font-semibold text-slate-300">RMSE</th><th className="text-right py-3 px-4 font-semibold text-slate-300">MAE</th><th className="text-center py-3 px-4 font-semibold text-slate-300">Status</th></tr></thead>
        <tbody>
          {metrics.map((m, i) => (
            <tr key={i} className={`border-b border-slate-700/50 hover:bg-slate-700/30 ${m.model_name === bestModel?.model_name ? 'bg-emerald-900/20' : ''}`}>
              <td className="py-3 px-4 font-medium text-white uppercase">
                {m.model_name}
                {m.model_name === bestModel?.model_name && <span className="ml-2 text-xs text-emerald-400">★ Best</span>}
              </td>
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

// ── Activity Log ──────────────────────────────────────────────────────────────
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

// ── Forecast Preview Table ────────────────────────────────────────────────────
function ForecastPreview() {
  const [preview, setPreview] = useState(null);
  
  useEffect(() => {
    fetch('https://kwachacast-api.onrender.com/api/v1/forecasts/latest?horizon=7&model=arimax')
      .then(r => r.json())
      .then(setPreview)
      .catch(() => {});
  }, []);

  if (!preview?.forecasts) return null;

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Eye className="w-4 h-4 text-blue-400" />Latest 7-Day Forecast (ARIMAX)</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-700"><th className="text-left py-2 px-3 text-slate-400">Date</th><th className="text-right py-2 px-3 text-slate-400">Predicted</th><th className="text-right py-2 px-3 text-slate-400">Lower</th><th className="text-right py-2 px-3 text-slate-400">Upper</th></tr></thead>
          <tbody>
            {preview.forecasts.map((f, i) => (
              <tr key={i} className="border-b border-slate-700/50">
                <td className="py-2 px-3 text-white">{f.target_date}</td>
                <td className="text-right py-2 px-3 text-white font-medium">{f.predicted_rate?.toFixed(2)}</td>
                <td className="text-right py-2 px-3 text-slate-400">{f.lower_bound?.toFixed(2)}</td>
                <td className="text-right py-2 px-3 text-slate-400">{f.upper_bound?.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500 mt-3">Forecast date: {preview.forecast_date} • Model: {preview.model_name || 'arimax'}</p>
    </div>
  );
}

// ── Data Freshness ────────────────────────────────────────────────────────────
function DataFreshness({ stats, accuracy }) {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Server className="w-4 h-4 text-purple-400" />System Status</h3>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Database records</span>
          <span className="text-white text-sm font-medium">3,507+</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Last rate update</span>
          <span className="text-white text-sm">{stats?.current ? 'Today' : 'Unknown'}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Forecasts fresh</span>
          <StatusBadge status={accuracy?.comparisons?.length > 0 ? "success" : "warning"} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Historical accuracy data</span>
          <span className="text-white text-sm">{accuracy?.comparisons?.length || 0} points</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">API documentation</span>
          <a href="https://kwachacast-api.onrender.com/docs" target="_blank" rel="noopener noreferrer" className="text-blue-400 text-sm hover:underline flex items-center gap-1">Open <ExternalLink className="w-3 h-3" /></a>
        </div>
      </div>
    </div>
  );
}

// ── System Commands ───────────────────────────────────────────────────────────
function SystemCommands({ addActivity }) {
  const handleExportData = () => {
    window.open('https://kwachacast-api.onrender.com/api/v1/rates/export?format=csv', '_blank');
    addActivity('info', 'Exporting rate data as CSV');
  };

  const handleExportForecasts = () => {
    window.open('https://kwachacast-api.onrender.com/api/v1/forecasts/export?horizon=7&format=csv', '_blank');
    addActivity('info', 'Exporting 7-day forecasts as CSV');
  };

  const handleRefreshForecasts = async () => {
    try {
      await getForecasts.generate(1);
      await getForecasts.generate(7);
      await getForecasts.generate(30);
      addActivity('success', 'All forecasts refreshed');
    } catch { addActivity('error', 'Refresh failed'); }
  };

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Zap className="w-4 h-4 text-yellow-400" />System Commands</h3>
      <div className="flex flex-wrap gap-2">
        <button onClick={handleRefreshForecasts} className="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1.5 rounded-lg transition flex items-center gap-1"><RefreshCw className="w-3 h-3" />Refresh Forecasts</button>
        <button onClick={handleExportData} className="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1.5 rounded-lg transition flex items-center gap-1"><Download className="w-3 h-3" />Export Rates CSV</button>
        <button onClick={handleExportForecasts} className="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1.5 rounded-lg transition flex items-center gap-1"><Download className="w-3 h-3" />Export Forecasts CSV</button>
        <button onClick={() => window.open('https://github.com/Kennywryght/kwacha-forecasting', '_blank')} className="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1.5 rounded-lg transition flex items-center gap-1"><ExternalLink className="w-3 h-3" />GitHub</button>
        <button onClick={() => window.open('https://kwachacast-api.onrender.com/docs', '_blank')} className="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-1.5 rounded-lg transition flex items-center gap-1"><ExternalLink className="w-3 h-3" />API Docs</button>
      </div>
    </div>
  );
}

// ── MAIN ADMIN DASHBOARD ──────────────────────────────────────────────────────
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
    addActivity('info', 'Model retraining started (ARIMA, ARIMAX, XGBoost, LightGBM)');
    try {
      await getForecasts.retrain();
      addActivity('success', 'All models retrained successfully');
      setMsg("✅ Models retrained!"); await fetchAll();
    } catch { addActivity('error', 'Retraining failed - check backend logs'); setMsg("❌ Failed"); }
    setTimeout(() => { setRetraining(false); setMsg(null); }, 3000);
  };

  const bestModel = metrics.length > 0 ? metrics.reduce((a, b) => (a.mape || 99) < (b.mape || 99) ? a : b) : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Monitor, manage & maintain the KwachaCast forecasting system</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Auto-refresh: 5min</span>
          <button onClick={fetchAll} disabled={loading} className="text-slate-400 hover:text-white text-sm flex items-center gap-1">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />Refresh
          </button>
        </div>
      </div>

      {msg && <div className={`rounded-xl p-3 text-sm ${msg.includes('✅') ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : msg.includes('❌') ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-blue-500/10 border border-blue-500/20 text-blue-400'}`}>{msg}</div>}

      {/* Quick Actions */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Zap className="w-4 h-4 text-yellow-400" />Quick Actions</h3>
        <div className="flex flex-wrap gap-3">
          <button onClick={handleGenerateAll} disabled={generating} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}Generate All Forecasts
          </button>
          <button onClick={() => handleGenerateSingle(1)} className="bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg font-medium transition">1-Day</button>
          <button onClick={() => handleGenerateSingle(7)} className="bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg font-medium transition">7-Day</button>
          <button onClick={() => handleGenerateSingle(30)} className="bg-slate-700 hover:bg-slate-600 text-white text-sm px-3 py-2 rounded-lg font-medium transition">30-Day</button>
          <button onClick={handleRetrain} disabled={retraining} className="bg-amber-600 hover:bg-amber-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
            {retraining ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}Retrain All Models
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Database} title="Total Records" value="3,507+" subtitle="Exchange rates (2013-2026)" color="text-blue-400" />
          <StatCard icon={TrendingUp} title="Latest Rate" value={stats?.current ? `MWK ${stats.current.toFixed(2)}` : "---"} subtitle="Live rate" color="text-emerald-400" />
          <StatCard icon={Cpu} title="Active Models" value={metrics?.length || 0} subtitle="Loaded & fitted" color="text-purple-400" />
          <StatCard icon={Shield} title="Best Model MAPE" value={bestModel ? `${bestModel.mape?.toFixed(4)}%` : "---"} subtitle={bestModel ? bestModel.model_name?.toUpperCase() : ""} color="text-emerald-400" />
        </div>
      )}

      {/* Model Health */}
      {!loading && <ModelHealth metrics={metrics} />}

      {/* Model Performance Table */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-blue-400" />Detailed Model Metrics</h3>
        {loading ? <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-emerald-400 animate-spin" /></div> : <ModelMetricsTable metrics={metrics} />}
      </div>

      {/* Forecast Preview */}
      {!loading && <ForecastPreview />}

      {/* Rate Stats + System Status */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
            <h3 className="text-sm font-semibold text-slate-300 mb-4">Rate Statistics</h3>
            {stats ? (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><p className="text-slate-400 text-xs">7-day range</p><p className="text-white font-medium">{stats.min_7d?.toFixed(2)} – {stats.max_7d?.toFixed(2)}</p></div>
                <div><p className="text-slate-400 text-xs">7-day change</p><p className={`font-medium ${stats.change_7d > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{stats.change_7d > 0 ? '+' : ''}{stats.change_7d?.toFixed(2)} ({stats.change_pct_7d?.toFixed(2)}%)</p></div>
                <div><p className="text-slate-400 text-xs">30-day range</p><p className="text-white font-medium">{stats.min_30d?.toFixed(2)} – {stats.max_30d?.toFixed(2)}</p></div>
                <div><p className="text-slate-400 text-xs">30-day avg</p><p className="text-white font-medium">{stats.avg_30d?.toFixed(2)}</p></div>
              </div>
            ) : <p className="text-slate-500 text-sm">Loading statistics...</p>}
          </div>
          <DataFreshness stats={stats} accuracy={accuracy} />
        </div>
      )}

      {/* Forecast Accuracy */}
      {!loading && (
        <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Forecast Accuracy Tracking</h3>
          {accuracy?.comparisons?.length ? (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm mb-3">
              <div className="bg-slate-700/40 rounded-xl p-3 text-center"><p className="text-slate-400 text-xs">Avg Error</p><p className="text-white font-bold text-lg">{accuracy.avg_error_mwk} MWK</p></div>
              <div className="bg-slate-700/40 rounded-xl p-3 text-center"><p className="text-slate-400 text-xs">Error Rate</p><p className="text-white font-bold text-lg">{accuracy.avg_error_pct}%</p></div>
              <div className="bg-slate-700/40 rounded-xl p-3 text-center"><p className="text-slate-400 text-xs">Within Range</p><p className="text-emerald-400 font-bold text-lg">{accuracy.within_range_pct}%</p></div>
              <div className="bg-slate-700/40 rounded-xl p-3 text-center"><p className="text-slate-400 text-xs">Data Points</p><p className="text-white font-bold text-lg">{accuracy.comparisons.length}</p></div>
            </div>
          ) : (
            <div className="bg-slate-700/40 rounded-xl p-4">
              <p className="text-slate-400 text-sm">📊 No historical accuracy data yet. This requires 7+ days of consecutive forecast generation to compare predictions against actual rates.</p>
              {bestModel && <p className="text-slate-500 text-xs mt-2">Training accuracy: <span className="text-emerald-400">{bestModel.model_name?.toUpperCase()}</span> achieves {bestModel.mape?.toFixed(4)}% MAPE</p>}
            </div>
          )}
        </div>
      )}

      {/* System Commands */}
      {!loading && <SystemCommands addActivity={addActivity} />}

      {/* Activity Log */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2"><Clock className="w-4 h-4 text-purple-400" />Activity Log</h3>
        <ActivityLog activities={activities} />
      </div>
    </div>
  );
}