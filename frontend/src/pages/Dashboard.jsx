import React, { useState, useEffect } from "react";
import { useDashboardData } from "../hooks/useForecasts";
import HistoryChart from "../components/HistoryChart";
import { getForecasts, getForecastSummary, getRateStats, getForecastAccuracy, exportForecasts, exportRates } from "../utils/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ComposedChart, Legend } from "recharts";
import { AlertCircle, RefreshCw, Loader2, Shield, Calendar, Download, TrendingUp, TrendingDown, BarChart3 } from "lucide-react";

const LIVE_RATE_URL = 'https://open.er-api.com/v6/latest/USD';

// ── Components ────────────────────────────────────────────────────────────────

function TrustChart({ history, forecasts }) {
  if (!history?.length) return null;
  const data = history.slice(-30).map((h, i) => ({
    date: h.date?.slice(5) || h.date,
    actual: Number(h.rate?.toFixed(2)),
    forecasted: forecasts?.prediction?.[i] ? Number(forecasts.prediction[i]?.toFixed(2)) : null,
  }));
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center gap-2 mb-3"><Shield className="w-4 h-4 text-emerald-400" /><h3 className="text-sm font-semibold text-slate-300">Accuracy & transparency</h3></div>
      <p className="text-xs text-slate-500 mb-4">Our forecasts against actual market rates.</p>
      <ResponsiveContainer width="100%" height={200}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={4} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }} formatter={(v, name) => [`MWK ${Number(v).toFixed(2)}`, name === 'actual' ? 'Actual' : 'Forecast']} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#34d399" strokeWidth={2} dot={false} name="Actual" />
          <Line type="monotone" dataKey="forecasted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Our forecast" connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function ForecastOutlook({ forecast1d, forecast7d, forecast30d }) {
  const horizons = [
    { label: "Next day", data: forecast1d, color: "#34d399" },
    { label: "7 days", data: forecast7d, color: "#60a5fa" },
    { label: "30 days", data: forecast30d, color: "#fbbf24" },
  ];
  const allData = [];
  horizons.forEach(h => {
    if (h.data?.forecasts) h.data.forecasts.forEach((v, i) => allData.push({ day: i + 1, value: Number(v?.predicted_rate?.toFixed(2)), horizon: h.label }));
    else if (h.data?.predicted_rate) allData.push({ day: 1, value: Number(h.data.predicted_rate?.toFixed(2)), horizon: h.label });
  });
  if (!allData.length) return null;
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Forecast outlook</h3>
      <p className="text-xs text-slate-500 mb-4">Expected movement across timeframes.</p>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={allData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }} formatter={(v) => [`MWK ${Number(v).toFixed(2)}`, undefined]} />
          <Legend />
          {horizons.map(h => (<Line key={h.label} type="monotone" dataKey="value" data={allData.filter(d => d.horizon === h.label)} stroke={h.color} strokeWidth={2} dot={false} name={h.label} />))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function WhenToAct({ nextDayChange, sevenDayChange, thirtyDayChange }) {
  const getAdvice = (label, change) => {
    const pct = parseFloat(change?.pct || 0);
    const dir = change?.direction;
    if (Math.abs(pct) < 0.3) return { level: "Stable", advice: "No action needed — rate is holding steady.", color: "text-emerald-400", bg: "bg-emerald-500/10" };
    if (dir === "up") return { level: "Weakening", advice: "Kwacha losing value. Buy USD now if needed urgently.", color: "text-red-400", bg: "bg-red-500/10" };
    return { level: "Strengthening", advice: "Kwacha gaining. Convert USD now if you hold any.", color: "text-emerald-400", bg: "bg-emerald-500/10" };
  };
  const stages = [{ label: "Today", change: nextDayChange }, { label: "This week", change: sevenDayChange }, { label: "This month", change: thirtyDayChange }];
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">What you should do</h3>
      <div className="space-y-3">
        {stages.map((stage, i) => {
          const advice = getAdvice(stage.label, stage.change);
          return (
            <div key={i} className={`${advice.bg} rounded-xl p-4`}>
              <div className="flex items-center justify-between mb-1"><span className="text-sm font-medium text-slate-300">{stage.label}</span><span className={`text-xs font-bold ${advice.color}`}>{advice.level}</span></div>
              <p className="text-xs text-slate-400">{advice.advice}</p>
              {stage.change && <p className="text-xs text-slate-500 mt-1">{stage.change.direction === "up" ? "↗" : "↘"} {stage.change.pct}%</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function RateStats({ stats }) {
  if (!stats) return null;
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center gap-2 mb-3"><BarChart3 className="w-4 h-4 text-blue-400" /><h3 className="text-sm font-semibold text-slate-300">Rate statistics</h3></div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><p className="text-slate-400 text-xs">7-day range</p><p className="text-white font-medium">{stats.min_7d?.toFixed(2)} – {stats.max_7d?.toFixed(2)}</p></div>
        <div><p className="text-slate-400 text-xs">7-day change</p><p className={`font-medium ${stats.change_7d > 0 ? 'text-red-400' : 'text-emerald-400'}`}>{stats.change_7d > 0 ? '+' : ''}{stats.change_7d?.toFixed(2)} ({stats.change_pct_7d?.toFixed(2)}%)</p></div>
        <div><p className="text-slate-400 text-xs">30-day range</p><p className="text-white font-medium">{stats.min_30d?.toFixed(2)} – {stats.max_30d?.toFixed(2)}</p></div>
        <div><p className="text-slate-400 text-xs">30-day avg</p><p className="text-white font-medium">{stats.avg_30d?.toFixed(2)}</p></div>
      </div>
    </div>
  );
}

function AccuracyCard({ accuracy }) {
  if (!accuracy?.comparisons?.length) return null;
  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center gap-2 mb-3"><Shield className="w-4 h-4 text-emerald-400" /><h3 className="text-sm font-semibold text-slate-300">Model accuracy</h3></div>
      <div className="grid grid-cols-2 gap-3 text-sm mb-3">
        <div><p className="text-slate-400 text-xs">Avg error</p><p className="text-white font-medium">{accuracy.avg_error_mwk} MWK</p></div>
        <div><p className="text-slate-400 text-xs">Error rate</p><p className="text-white font-medium">{accuracy.avg_error_pct}%</p></div>
        <div><p className="text-slate-400 text-xs">Within range</p><p className="text-white font-medium">{accuracy.within_range_pct}%</p></div>
        <div><p className="text-slate-400 text-xs">Forecast date</p><p className="text-white font-medium">{accuracy.forecast_date}</p></div>
      </div>
      <p className="text-xs text-slate-500">Based on {accuracy.comparisons.length} past forecasts compared to actual rates.</p>
    </div>
  );
}

function EmptyForecasts({ onGenerate, generating }) {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-12 border border-slate-700/60 flex flex-col items-center gap-4 text-center">
      <Calendar className="w-14 h-14 text-slate-500" />
      <h3 className="text-white font-semibold text-xl">No forecasts yet</h3>
      <p className="text-slate-400 text-sm max-w-md">Generate forecasts to see predictions.</p>
      <button onClick={onGenerate} disabled={generating} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-6 py-3 rounded-xl font-semibold transition flex items-center gap-2 mt-2">
        {generating && <Loader2 className="w-4 h-4 animate-spin" />}{generating ? "Generating..." : "Generate forecasts"}
      </button>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [generating, setGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState(null);
  const [liveRate, setLiveRate] = useState(null);
  const [forecast1d, setForecast1d] = useState(null);
  const [forecast7d, setForecast7d] = useState(null);
  const [forecast30d, setForecast30d] = useState(null);
  const [rateStats, setRateStats] = useState(null);
  const [accuracy, setAccuracy] = useState(null);

  const { latestRate, forecasts, history, loading, noForecasts, refetch } = useDashboardData(7);

  const fetchAllData = async () => {
    const [summary, stats, acc] = await Promise.all([
      getForecastSummary(), getRateStats(), getForecastAccuracy()
    ]);
    if (summary?.forecasts) {
      setForecast1d(summary.forecasts["1_day"]);
      setForecast7d(summary.forecasts["7_day"]);
      setForecast30d(summary.forecasts["30_day"]);
      if (summary.current_rate) setLiveRate({ rate: summary.current_rate });
    }
    if (stats) setRateStats(stats);
    if (acc) setAccuracy(acc);
  };

  useEffect(() => { fetchAllData(); }, [noForecasts]);

  useEffect(() => {
    fetch(LIVE_RATE_URL).then(r => r.json()).then(d => {
      if (d?.rates?.MWK) setLiveRate({ rate: d.rates.MWK });
    }).catch(() => {});
  }, []);

  const displayRate = liveRate || latestRate;

  const handleGenerate = async () => {
    setGenerating(true); setGenerateMsg("Generating forecasts...");
    try {
      await getForecasts.generate(1); await getForecasts.generate(7); await getForecasts.generate(30);
      await refetch(); await fetchAllData();
      setGenerateMsg("Forecasts updated!"); setTimeout(() => { setGenerating(false); setGenerateMsg(null); }, 2000);
    } catch { setGenerateMsg("Failed. Backend may be waking up — try again."); setGenerating(false); }
  };

  const getChange = (predictedRate) => {
    if (!displayRate?.rate || !predictedRate) return null;
    const diff = predictedRate - displayRate.rate;
    return { direction: diff > 0 ? "up" : "down", pct: ((diff / displayRate.rate) * 100).toFixed(2) };
  };

  const nextDayVal = forecast1d?.predicted_rate?.toFixed(2) ?? null;
  const nextDayChange = forecast1d ? getChange(forecast1d.predicted_rate) : null;
  const sevenDayVal = forecast7d?.predicted_rate?.toFixed(2) ?? null;
  const sevenDayChange = forecast7d ? getChange(forecast7d.predicted_rate) : null;
  const thirtyDayVal = forecast30d?.predicted_rate?.toFixed(2) ?? null;
  const thirtyDayChange = forecast30d ? getChange(forecast30d.predicted_rate) : null;

  const kpis = [
    { label: "Current rate", value: displayRate?.rate ? `MWK ${displayRate.rate.toFixed(2)}` : "--", change: null },
    { label: "Next day", value: nextDayVal ? `MWK ${nextDayVal}` : "--", change: nextDayChange },
    { label: "7 days", value: sevenDayVal ? `MWK ${sevenDayVal}` : "--", change: sevenDayChange },
    { label: "30 days", value: thirtyDayVal ? `MWK ${thirtyDayVal}` : "--", change: thirtyDayChange },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold text-white">KwachaCast</h1><p className="text-slate-400 text-sm mt-1">Exchange rate forecasts for the Malawi Kwacha</p></div>
        <div className="flex items-center gap-2">
          <button onClick={() => exportForecasts(7)} className="text-slate-400 hover:text-white text-sm flex items-center gap-1"><Download className="w-3.5 h-3.5" />Export</button>
          <button onClick={handleGenerate} disabled={generating} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}{generating ? "Generating..." : "Refresh"}
          </button>
        </div>
      </div>

      {generateMsg && <div className="rounded-xl p-3 text-sm bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">{generateMsg}</div>}
      {loading && <div className="grid grid-cols-4 gap-4 animate-pulse">{[...Array(4)].map((_, i) => <div key={i} className="bg-slate-800/60 rounded-2xl h-32 border border-slate-700/60" />)}</div>}
      {!loading && noForecasts && <EmptyForecasts onGenerate={handleGenerate} generating={generating} />}

      {/* KPI Cards */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((kpi, i) => (
            <div key={i} className={`bg-slate-800/60 border ${i === 0 ? 'border-emerald-500/20' : 'border-slate-700/60'} rounded-2xl p-5`}>
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">{kpi.label}</p>
              <p className="text-2xl font-bold text-white">{kpi.value}</p>
              {kpi.change && <p className={`text-sm font-medium mt-1 ${kpi.change.direction === "up" ? "text-red-400" : "text-emerald-400"}`}>{kpi.change.direction === "up" ? "↗" : "↘"} {kpi.change.pct}%</p>}
            </div>
          ))}
        </div>
      )}

      {/* Forecast Outlook + When to Act */}
      {!loading && !noForecasts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ForecastOutlook forecast1d={forecast1d} forecast7d={forecast7d} forecast30d={forecast30d} />
          <WhenToAct nextDayChange={nextDayChange} sevenDayChange={sevenDayChange} thirtyDayChange={thirtyDayChange} />
        </div>
      )}

      {/* Rate Stats + Accuracy */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RateStats stats={rateStats} />
          <AccuracyCard accuracy={accuracy} />
        </div>
      )}

      {/* Trust Chart + History */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {history?.length > 30 && <TrustChart history={history} forecasts={forecast7d || forecasts} />}
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Historical trends</h3>
            <HistoryChart history={history} loading={loading} forecasts={forecasts} />
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-4 flex gap-3">
        <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-amber-200/80 text-sm">Forecasts are for informational purposes. Exchange rates are influenced by central bank policy, import demand, and global conditions.</p>
      </div>
    </div>
  );
}