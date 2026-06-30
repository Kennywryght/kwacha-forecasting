import React, { useState, useEffect } from "react";
import { getForecasts, getModelMetrics, getRateStats, getForecastAccuracy } from "../utils/api";
import { RefreshCw, Loader2, TrendingUp, BarChart3, Shield, Activity, Database, Cpu, ExternalLink, Server, Zap, Clock, Eye, Download } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

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
      <div className="flex items-start justify-between mb-3">
        <p className="text-slate-400 text-xs uppercase tracking-wider">{title}</p>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

// ── Model Performance Table ──────────────────────────────────────────────────
function ModelMetricsTable({ metrics }) {
  if (!metrics?.length) return null;
  const bestModel = metrics.reduce((a, b) => (a.mape || 99) < (b.mape || 99) ? a : b, metrics[0]);
  
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            <th className="text-left py-3 px-4 font-semibold text-slate-300">Model</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-300">MAPE (%)</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-300">RMSE</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-300">MAE</th>
            <th className="text-right py-3 px-4 font-semibold text-slate-300">Dir Acc</th>
            <th className="text-center py-3 px-4 font-semibold text-slate-300">Status</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m, i) => (
            <tr key={i} className={`border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors ${m.model_name === bestModel?.model_name ? 'bg-emerald-900/20' : ''}`}>
              <td className="py-3 px-4 font-medium text-white uppercase">
                {m.model_name}
                {m.model_name === bestModel?.model_name && (
                  <span className="ml-2 text-xs text-emerald-400 font-normal">★ Best</span>
                )}
              </td>
              <td className="text-right py-3 px-4 text-slate-300 font-mono">{m.mape?.toFixed(4)}</td>
              <td className="text-right py-3 px-4 text-slate-300 font-mono">{m.rmse?.toFixed(2)}</td>
              <td className="text-right py-3 px-4 text-slate-300 font-mono">{m.mae?.toFixed(2)}</td>
              <td className="text-right py-3 px-4 text-slate-300 font-mono">
                {m.directional_accuracy != null ? `${(m.directional_accuracy * 100).toFixed(1)}%` : '—'}
              </td>
              <td className="text-center py-3 px-4">
                <StatusBadge status={m.mape < 1 ? "success" : m.mape < 3 ? "warning" : "error"} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Forecast Preview Table ────────────────────────────────────────────────────
function ForecastPreview() {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('https://kwachacast-api.onrender.com/api/v1/forecasts/all?horizon=7')
      .then(r => r.json())
      .then(data => {
        const modelPreviews = {};
        if (data && typeof data === 'object' && !data.status) {
          Object.entries(data).forEach(([modelName, modelData]) => {
            if (modelData?.forecasts) {
              modelPreviews[modelName] = modelData;
            }
          });
        }
        setPreview(modelPreviews);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
        </div>
      </div>
    );
  }

  if (!preview || Object.keys(preview).length === 0) return null;

  const modelNames = Object.keys(preview);
  const firstModel = preview[modelNames[0]];
  const targetDates = firstModel?.forecasts?.map(f => f.target_date) || [];

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
        <Eye className="w-4 h-4 text-blue-400" />
        Latest 7-Day Forecast Comparison
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left py-2 px-3 text-slate-400 text-xs">Date</th>
              {modelNames.map(name => (
                <th key={name} className="text-right py-2 px-3 text-slate-400 text-xs uppercase">{name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {targetDates.map((date, i) => (
              <tr key={date} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                <td className="py-2 px-3 text-white text-xs">{date}</td>
                {modelNames.map(name => {
                  const forecast = preview[name]?.forecasts?.[i];
                  return (
                    <td key={name} className="text-right py-2 px-3 text-slate-300 font-mono text-xs">
                      {forecast ? forecast.predicted_rate?.toFixed(2) : '—'}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500 mt-3">
        Forecast date: {firstModel?.forecast_date || 'Unknown'} • 
        Comparing {modelNames.length} models
      </p>
    </div>
  );
}

// ── Model Forecast Chart ─────────────────────────────────────────────────────
function ModelForecastChart() {
  const [chartData, setChartData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedHorizon, setSelectedHorizon] = useState(7);

  useEffect(() => {
    setLoading(true);
    fetch(`https://kwachacast-api.onrender.com/api/v1/forecasts/all?horizon=${selectedHorizon}`)
      .then(r => r.json())
      .then(data => {
        if (data && typeof data === 'object' && !data.status) {
          const allDates = new Set();
          const modelData = {};
          
          Object.entries(data).forEach(([modelName, modelInfo]) => {
            if (modelInfo?.forecasts) {
              modelData[modelName] = {};
              modelInfo.forecasts.forEach(f => {
                allDates.add(f.target_date);
                modelData[modelName][f.target_date] = f.predicted_rate;
              });
            }
          });
          
          const sortedDates = Array.from(allDates).sort();
          const chartSeries = sortedDates.map(date => {
            const point = { date };
            Object.keys(modelData).forEach(model => {
              point[model] = modelData[model][date] || null;
            });
            return point;
          });
          
          setChartData({ series: chartSeries, models: Object.keys(modelData) });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selectedHorizon]);

  if (loading) {
    return (
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
        </div>
      </div>
    );
  }

  if (!chartData?.series?.length) return null;

  const modelColors = {
    arima: '#34d399',
    arimax: '#60a5fa',
    prophet: '#fbbf24',
    xgboost: '#f472b6',
    lightgbm: '#a78bfa',
    ensemble: '#ffffff',
  };

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          Model Forecast Comparison Chart
        </h3>
        <select
          value={selectedHorizon}
          onChange={(e) => setSelectedHorizon(Number(e.target.value))}
          className="bg-slate-700 border border-slate-600 text-slate-300 text-xs rounded-lg px-2 py-1 focus:outline-none focus:border-emerald-500"
        >
          <option value={1}>1 Day</option>
          <option value={7}>7 Days</option>
          <option value={30}>30 Days</option>
        </select>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData.series}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }}
            formatter={(v) => v != null ? [`MWK ${Number(v).toFixed(2)}`, undefined] : ['N/A', undefined]} 
          />
          <Legend />
          {chartData.models.map(model => (
            <Line
              key={model}
              type="monotone"
              dataKey={model}
              stroke={modelColors[model] || '#94a3b8'}
              strokeWidth={2}
              dot={{ r: 2 }}
              name={model.toUpperCase()}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
      <p className="text-xs text-slate-500 mt-3">
        Comparing {chartData.models.length} models • Horizon: {selectedHorizon} day{selectedHorizon > 1 ? 's' : ''}
      </p>
    </div>
  );
}

// ── Data Freshness ────────────────────────────────────────────────────────────
function DataFreshness({ stats, accuracy, metrics }) {
  const activeModels = metrics?.length || 0;
  
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
        <Server className="w-4 h-4 text-purple-400" />
        System Status
      </h3>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Active models</span>
          <span className="text-white text-sm font-medium">{activeModels} loaded</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Latest rate</span>
          <span className="text-white text-sm font-mono">
            {stats?.current ? `MWK ${stats.current.toFixed(2)}` : 'Unknown'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">7-day change</span>
          <span className={`text-sm font-medium ${stats?.change_7d > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
            {stats ? `${stats.change_7d > 0 ? '+' : ''}${stats.change_7d?.toFixed(2)} (${stats.change_pct_7d?.toFixed(2)}%)` : 'Unknown'}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Accuracy data points</span>
          <span className="text-white text-sm">{accuracy?.comparisons?.length || 0}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">Forecasts within range</span>
          <span className="text-emerald-400 text-sm font-medium">
            {accuracy?.within_range_pct ? `${accuracy.within_range_pct}%` : 'N/A'}
          </span>
        </div>
        <hr className="border-slate-700" />
        <div className="flex items-center justify-between">
          <span className="text-slate-400 text-sm">API documentation</span>
          <a 
            href="https://kwachacast-api.onrender.com/docs" 
            target="_blank" 
            rel="noopener noreferrer" 
            className="text-blue-400 text-sm hover:underline flex items-center gap-1"
          >
            Open docs <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}

// ── Accuracy Tracking ─────────────────────────────────────────────────────────
function AccuracyTracking({ accuracy, metrics }) {
  const bestModel = metrics?.length > 0 
    ? metrics.reduce((a, b) => (a.mape || 99) < (b.mape || 99) ? a : b) 
    : null;

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
        <Shield className="w-4 h-4 text-emerald-400" />
        Forecast Accuracy
      </h3>
      
      {accuracy?.comparisons?.length > 0 ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            {[
              { label: "Avg Error", value: `${accuracy.avg_error_mwk} MWK` },
              { label: "Error Rate", value: `${accuracy.avg_error_pct}%` },
              { label: "Within Range", value: `${accuracy.within_range_pct}%` },
              { label: "Data Points", value: accuracy.comparisons.length },
            ].map((item, i) => (
              <div key={i} className="bg-slate-700/40 rounded-xl p-3 text-center">
                <p className="text-slate-400 text-xs">{item.label}</p>
                <p className={`text-lg font-bold ${i === 2 ? 'text-emerald-400' : 'text-white'}`}>
                  {item.value}
                </p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="bg-slate-700/40 rounded-xl p-4">
          <p className="text-slate-400 text-sm">
            No historical accuracy data yet. Requires 7+ days of consecutive forecast generation to compare predictions against actual rates.
          </p>
          {bestModel && (
            <p className="text-slate-500 text-xs mt-2">
              Training accuracy: <span className="text-emerald-400 font-medium">{bestModel.model_name?.toUpperCase()}</span> achieves {bestModel.mape?.toFixed(4)}% MAPE
            </p>
          )}
        </div>
      )}
    </div>
  );
}

// ── Activity Log ──────────────────────────────────────────────────────────────
function ActivityLog({ activities }) {
  if (!activities?.length) return null;
  
  return (
    <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
      {activities.map((a, i) => (
        <div key={i} className="flex items-start gap-3 p-2.5 bg-slate-700/30 rounded-lg">
          <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${
            a.type === 'success' ? 'bg-emerald-400' : 
            a.type === 'error' ? 'bg-red-400' : 
            'bg-blue-400'
          }`} />
          <div className="min-w-0">
            <p className="text-xs text-slate-300">{a.message}</p>
            <p className="text-xs text-slate-500 mt-0.5">{a.time}</p>
          </div>
        </div>
      ))}
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
  const [activities, setActivities] = useState([
    { type: 'info', message: 'Admin dashboard initialized', time: new Date().toLocaleTimeString() }
  ]);

  const addActivity = (type, message) => {
    setActivities(prev => [{ type, message, time: new Date().toLocaleTimeString() }, ...prev].slice(0, 50));
  };

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [m, s, a] = await Promise.all([
        getModelMetrics().catch(() => []),
        getRateStats().catch(() => null),
        getForecastAccuracy().catch(() => null),
      ]);
      if (m) setMetrics(Array.isArray(m) ? m : []);
      if (s) setStats(s);
      if (a) setAccuracy(a);
      addActivity('success', 'Dashboard data refreshed');
    } catch {
      addActivity('error', 'Failed to fetch dashboard data');
    }
    setLoading(false);
  };

  useEffect(() => { fetchAll(); }, []);

  useEffect(() => {
    const interval = setInterval(fetchAll, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateAll = async () => {
    setGenerating(true);
    setMsg("Generating all forecasts (1d, 7d, 30d)...");
    addActivity('info', 'Starting forecast generation');
    try {
      await getForecasts.generate(1);
      await getForecasts.generate(7);
      await getForecasts.generate(30);
      addActivity('success', 'All forecasts generated successfully');
      setMsg("✅ All forecasts generated!");
      await fetchAll();
    } catch {
      addActivity('error', 'Forecast generation failed');
      setMsg("❌ Generation failed — check backend logs");
    }
    setTimeout(() => { setGenerating(false); setMsg(null); }, 3000);
  };

  const handleGenerateSingle = async (horizon) => {
    try {
      await getForecasts.generate(horizon);
      addActivity('success', `Generated ${horizon}-day forecasts`);
      setMsg(`✅ ${horizon}-day forecast generated`);
      setTimeout(() => setMsg(null), 2000);
    } catch {
      addActivity('error', `Failed to generate ${horizon}-day forecast`);
      setMsg(`❌ ${horizon}-day generation failed`);
      setTimeout(() => setMsg(null), 2000);
    }
  };

  const handleRetrain = async () => {
    setRetraining(true);
    setMsg("Retraining all models...");
    addActivity('info', 'Model retraining initiated');
    try {
      await getForecasts.retrain();
      addActivity('success', 'All models retrained successfully');
      setMsg("✅ Models retrained!");
      await fetchAll();
    } catch {
      addActivity('error', 'Retraining failed');
      setMsg("❌ Retraining failed — check backend logs");
    }
    setTimeout(() => { setRetraining(false); setMsg(null); }, 3000);
  };

  const bestModel = metrics.length > 0 
    ? metrics.reduce((a, b) => (a.mape || 99) < (b.mape || 99) ? a : b) 
    : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Admin Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">Monitor and manage the KwachaCast forecasting system</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">Auto-refresh: 5 min</span>
          <button 
            onClick={fetchAll} 
            disabled={loading} 
            className="text-slate-400 hover:text-white text-sm flex items-center gap-1 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Status Message */}
      {msg && (
        <div className={`rounded-xl p-3 text-sm font-medium ${
          msg.includes('✅') 
            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' 
            : msg.includes('❌') 
            ? 'bg-red-500/10 border border-red-500/20 text-red-400' 
            : 'bg-blue-500/10 border border-blue-500/20 text-blue-400'
        }`}>
          {msg}
        </div>
      )}

      {/* Quick Actions */}
      <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
        <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-400" />
          Quick Actions
        </h3>
        <div className="flex flex-wrap gap-2">
          <button 
            onClick={handleGenerateAll} 
            disabled={generating} 
            className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white text-xs px-4 py-2 rounded-lg font-medium transition flex items-center gap-2"
          >
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            {generating ? 'Generating...' : 'Generate All'}
          </button>
          {[1, 7, 30].map(h => (
            <button 
              key={h}
              onClick={() => handleGenerateSingle(h)} 
              className="bg-slate-700 hover:bg-slate-600 text-white text-xs px-3 py-2 rounded-lg font-medium transition"
            >
              {h}-Day
            </button>
          ))}
          <button 
            onClick={handleRetrain} 
            disabled={retraining} 
            className="bg-amber-600 hover:bg-amber-500 disabled:bg-slate-600 text-white text-xs px-4 py-2 rounded-lg font-medium transition flex items-center gap-2"
          >
            {retraining ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Activity className="w-3.5 h-3.5" />}
            {retraining ? 'Retraining...' : 'Retrain All'}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard icon={Database} title="Active Models" value={metrics.length} subtitle="Loaded & fitted" color="text-blue-400" />
          <StatCard icon={TrendingUp} title="Latest Rate" value={stats?.current ? `MWK ${stats.current.toFixed(2)}` : "—"} subtitle="Current MWK/USD" color="text-emerald-400" />
          <StatCard icon={Shield} title="Best MAPE" value={bestModel ? `${bestModel.mape?.toFixed(4)}%` : "—"} subtitle={bestModel?.model_name?.toUpperCase()} color="text-emerald-400" />
          <StatCard icon={Cpu} title="Accuracy Data" value={accuracy?.comparisons?.length || 0} subtitle="Historical comparisons" color="text-purple-400" />
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
        </div>
      )}

      {/* Model Performance */}
      {!loading && (
        <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
          <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-blue-400" />
            Model Performance
          </h3>
          <ModelMetricsTable metrics={metrics} />
        </div>
      )}

      {/* Model Forecast Chart */}
      {!loading && <ModelForecastChart />}

      {/* Forecast Preview Table */}
      {!loading && <ForecastPreview />}

      {/* System Status + Accuracy */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DataFreshness stats={stats} accuracy={accuracy} metrics={metrics} />
          <AccuracyTracking accuracy={accuracy} metrics={metrics} />
        </div>
      )}

      {/* Activity Log */}
      {!loading && (
        <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
          <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-purple-400" />
            Activity Log
          </h3>
          <ActivityLog activities={activities} />
        </div>
      )}
    </div>
  );
}