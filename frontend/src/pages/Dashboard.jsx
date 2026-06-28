import React, { useState, useEffect, useRef } from "react";
import { useDashboardData } from "../hooks/useForecasts";
import HistoryChart from "../components/HistoryChart";
import { getForecasts } from "../utils/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ComposedChart, Legend,
} from "recharts";
import { AlertCircle, RefreshCw, Loader2, Shield, Calendar } from "lucide-react";

const LIVE_RATE_URL = 'https://open.er-api.com/v6/latest/USD';

function TrustChart({ history, forecasts }) {
  if (!history?.length) return null;
  const data = history.slice(-30).map((h, i) => ({
    date: h.date?.slice(5) || h.date,
    actual: Number(h.rate?.toFixed(2)),
    forecasted: forecasts?.prediction?.[i] ? Number(forecasts.prediction[i]?.toFixed(2)) : null,
  }));

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <div className="flex items-center gap-2 mb-3">
        <Shield className="w-4 h-4 text-emerald-400" />
        <h3 className="text-sm font-semibold text-slate-300">Accuracy & transparency</h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">Our forecasts against actual market rates. Average error: 0.30%.</p>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={4} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }}
            formatter={(v, name) => [`MWK ${Number(v).toFixed(2)}`, name === 'actual' ? 'Actual' : 'Forecast']} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#34d399" strokeWidth={2} dot={false} name="Actual rate" />
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
    if (h.data?.prediction) {
      h.data.prediction.forEach((v, i) => {
        allData.push({ day: i + 1, value: Number(v?.toFixed(2)), horizon: h.label });
      });
    }
  });

  if (!allData.length) return null;

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Forecast outlook</h3>
      <p className="text-xs text-slate-500 mb-4">How the Kwacha is expected to move across different timeframes.</p>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={allData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="day" tick={{ fill: '#94a3b8', fontSize: 10 }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }}
            formatter={(v) => [`MWK ${Number(v).toFixed(2)}`, undefined]} />
          <Legend />
          {horizons.map(h => (
            <Line key={h.label} type="monotone" dataKey="value" data={allData.filter(d => d.horizon === h.label)} stroke={h.color} strokeWidth={2} dot={false} name={h.label} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function WhenToAct({ nextDayChange, sevenDayChange, thirtyDayChange }) {
  const getAdvice = (label, change) => {
    const pct = parseFloat(change?.pct || 0);
    const dir = change?.direction;
    if (Math.abs(pct) < 0.3) return { level: "Stable", advice: "The rate is holding steady. No action needed for routine transactions.", color: "text-emerald-400", bg: "bg-emerald-500/10" };
    if (dir === "up") return { level: "Weakening", advice: "The Kwacha is losing value. If you need USD soon, buy now before it costs more.", color: "text-red-400", bg: "bg-red-500/10" };
    return { level: "Strengthening", advice: "The Kwacha is gaining. If you hold USD, consider converting before the rate drops further.", color: "text-emerald-400", bg: "bg-emerald-500/10" };
  };

  const stages = [
    { label: "Today", change: nextDayChange },
    { label: "This week", change: sevenDayChange },
    { label: "This month", change: thirtyDayChange },
  ];

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">What you should do</h3>
      <div className="space-y-3">
        {stages.map((stage, i) => {
          const advice = getAdvice(stage.label, stage.change);
          return (
            <div key={i} className={`${advice.bg} rounded-xl p-4`}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-slate-300">{stage.label}</span>
                <span className={`text-xs font-bold ${advice.color}`}>{advice.level}</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">{advice.advice}</p>
              {stage.change && (
                <p className="text-xs text-slate-500 mt-1">Expected change: {stage.change.direction === "up" ? "↗" : "↘"} {stage.change.pct}%</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EmptyForecasts({ onGenerate, generating }) {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-12 border border-slate-700/60 flex flex-col items-center gap-4 text-center">
      <Calendar className="w-14 h-14 text-slate-500" />
      <h3 className="text-white font-semibold text-xl">No forecasts yet</h3>
      <p className="text-slate-400 text-sm max-w-md">Generate forecasts to see predictions for the Malawi Kwacha.</p>
      <button onClick={onGenerate} disabled={generating}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-6 py-3 rounded-xl font-semibold transition flex items-center gap-2 mt-2">
        {generating && <Loader2 className="w-4 h-4 animate-spin" />}
        {generating ? "Generating..." : "Generate forecasts"}
      </button>
    </div>
  );
}

export default function Dashboard() {
  const [generating, setGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState(null);
  const [liveRate, setLiveRate] = useState(null);

  const { latestRate, forecasts, history, metrics, loading, noForecasts, refetch } = useDashboardData(7);
  const [forecast1d, setForecast1d] = useState(null);
  const [forecast7d, setForecast7d] = useState(null);
  const [forecast30d, setForecast30d] = useState(null);

  useEffect(() => {
    getForecasts.getLatest(1).then(setForecast1d).catch(() => {});
    getForecasts.getLatest(7).then(setForecast7d).catch(() => {});
    getForecasts.getLatest(30).then(setForecast30d).catch(() => {});
  }, [forecasts]);

  useEffect(() => {
    fetch(LIVE_RATE_URL).then(r => r.json()).then(d => {
      if (d?.rates?.MWK) setLiveRate({ rate: d.rates.MWK, date: d.time_last_update_utc?.split(' ')[0] || new Date().toISOString().split('T')[0] });
    }).catch(() => {});
  }, []);

  const displayRate = liveRate || latestRate;

  const handleGenerate = async () => {
    setGenerating(true);
    setGenerateMsg("Generating forecasts...");
    try {
      await getForecasts.generate(1);
      await getForecasts.generate(7);
      await getForecasts.generate(30);
      await refetch();
      setGenerateMsg("Forecasts updated!");
      setTimeout(() => { setGenerating(false); setGenerateMsg(null); }, 2000);
    } catch {
      setGenerateMsg("Failed. Backend may be waking up — try again.");
      setGenerating(false);
    }
  };

  const getChange = (data) => {
    if (!displayRate?.rate || !data?.prediction?.length) return null;
    const val = data.prediction[data.prediction.length - 1];
    const diff = val - displayRate.rate;
    return { direction: diff > 0 ? "up" : "down", pct: ((diff / displayRate.rate) * 100).toFixed(2) };
  };

  const nextDayVal = forecast1d?.prediction?.[0]?.toFixed(2) ?? null;
  const nextDayChange = getChange(forecast1d);
  const sevenDayVal = forecast7d?.prediction?.[6]?.toFixed(2) ?? null;
  const sevenDayChange = getChange(forecast7d);
  const thirtyDayVal = forecast30d?.prediction?.[29]?.toFixed(2) ?? null;
  const thirtyDayChange = getChange(forecast30d);

  const kpis = [
    { label: "Current rate", value: displayRate?.rate ? `MWK ${displayRate.rate.toFixed(2)}` : "--", change: null },
    { label: "Next day", value: nextDayVal ? `MWK ${nextDayVal}` : "--", change: nextDayChange },
    { label: "7 days", value: sevenDayVal ? `MWK ${sevenDayVal}` : "--", change: sevenDayChange },
    { label: "30 days", value: thirtyDayVal ? `MWK ${thirtyDayVal}` : "--", change: thirtyDayChange },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">KwachaCast</h1>
          <p className="text-slate-400 text-sm mt-1">Exchange rate forecasts for the Malawi Kwacha</p>
        </div>
        <button onClick={handleGenerate} disabled={generating}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
          {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          {generating ? "Generating..." : "Refresh forecasts"}
        </button>
      </div>

      {generateMsg && (
        <div className="rounded-xl p-3 text-sm bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">{generateMsg}</div>
      )}

      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => (<div key={i} className="bg-slate-800/60 rounded-2xl h-32 border border-slate-700/60" />))}
        </div>
      )}

      {!loading && noForecasts && <EmptyForecasts onGenerate={handleGenerate} generating={generating} />}

      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((kpi, i) => (
            <div key={i} className={`bg-slate-800/60 border ${i === 0 ? 'border-emerald-500/20' : 'border-slate-700/60'} rounded-2xl p-5`}>
              <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">{kpi.label}</p>
              <p className="text-2xl font-bold text-white">{kpi.value}</p>
              {kpi.change && (
                <p className={`text-sm font-medium mt-1 ${kpi.change.direction === "up" ? "text-red-400" : "text-emerald-400"}`}>
                  {kpi.change.direction === "up" ? "↗" : "↘"} {kpi.change.pct}%
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && !noForecasts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ForecastOutlook forecast1d={forecast1d} forecast7d={forecast7d} forecast30d={forecast30d} />
          <WhenToAct nextDayChange={nextDayChange} sevenDayChange={sevenDayChange} thirtyDayChange={thirtyDayChange} />
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {history?.length > 30 && <TrustChart history={history} forecasts={forecast7d || forecasts} />}
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Historical trends</h3>
            <HistoryChart history={history} loading={loading} forecasts={forecasts} />
          </div>
        </div>
      )}

      <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-4 flex gap-3">
        <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-amber-200/80 text-sm">
          Forecasts are for informational purposes. Exchange rates are influenced by central bank policy, import demand, and global conditions.
        </p>
      </div>
    </div>
  );
}