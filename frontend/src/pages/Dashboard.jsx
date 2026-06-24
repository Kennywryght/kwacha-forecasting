import React, { useState, useEffect, useRef } from "react";
import { useDashboardData } from "../hooks/useForecasts";
import HistoryChart from "../components/HistoryChart";
import ModelMetricsTable from "../components/ModelMetricsTable";
import { getForecasts } from "../utils/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, ComposedChart, Legend,
} from "recharts";
import { AlertCircle, TrendingDown, TrendingUp, Clock, RefreshCw, Loader2, Target, Shield, Zap } from "lucide-react";

// ── Trust Chart: Last 30 Days Actual vs Forecast ─────────────────────────────
function TrustChart({ history, forecasts }) {
  if (!history?.length) return null;
  
  const data = history.slice(-30).map((h, i) => ({
    date: h.date?.slice(5) || h.date, // MM-DD format
    actual: h.rate,
    forecasted: forecasts?.prediction?.[i] || null,
  }));

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <div className="flex items-center gap-2 mb-3">
        <Shield className="w-4 h-4 text-emerald-400" />
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Trust & Transparency — Last 30 Days
        </h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">Compare our forecasts against actual market rates</p>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={4} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#60a5fa" strokeWidth={2} dot={false} name="Actual Rate" />
          <Line type="monotone" dataKey="forecasted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecasted" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Fan Chart ─────────────────────────────────────────────────────────────────
function FanChart({ forecasts, history }) {
  if (!forecasts?.dates?.length) return null;
  const histData = history?.slice(-60).map((d) => ({ date: d.date, rate: d.rate })) || [];
  const fcData = forecasts.dates.map((d, i) => ({
    date: d,
    predicted: forecasts.prediction[i],
    lower_80: forecasts.lower_80?.[i] ?? null,
    upper_80: forecasts.upper_80?.[i] ?? null,
  }));
  const lastHist = histData[histData.length - 1];
  const bridge = lastHist
    ? [{ date: lastHist.date, predicted: lastHist.rate, lower_80: lastHist.rate, upper_80: lastHist.rate }]
    : [];
  const combined = [
    ...histData.map((h) => ({ ...h, type: "actual" })),
    ...bridge,
    ...fcData.map((f) => ({ ...f, type: "forecast" })),
  ];

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <div className="flex items-center gap-2 mb-3">
        <Target className="w-4 h-4 text-orange-400" />
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Forecast Fan (80% Confidence)
        </h3>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={combined}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} domain={["auto", "auto"]} />
          <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "none", borderRadius: "8px", color: "#e2e8f0" }} />
          <Area type="monotone" dataKey="upper_80" stroke="none" fill="#f97316" fillOpacity={0.12} />
          <Area type="monotone" dataKey="lower_80" stroke="none" fill="#f97316" fillOpacity={0.12} />
          <Line type="monotone" dataKey="rate" stroke="#60a5fa" strokeWidth={2} dot={false} name="Actual" />
          <Line type="monotone" dataKey="predicted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecast" />
          {lastHist && <ReferenceLine y={lastHist.rate} stroke="#64748b" strokeDasharray="3 3" />}
          <Legend />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────
function EmptyForecasts({ onGenerate, generating }) {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-12 border border-slate-700/60 backdrop-blur flex flex-col items-center gap-4 text-center">
      <Zap className="w-14 h-14 text-slate-500" />
      <h3 className="text-white font-semibold text-xl">No Forecasts Yet</h3>
      <p className="text-slate-400 text-sm max-w-md">
        Generate today's forecasts to see predictions from ARIMA, ARIMAX, Prophet, and Ensemble models.
      </p>
      <button
        onClick={onGenerate}
        disabled={generating}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-6 py-3 rounded-xl font-semibold transition-colors flex items-center gap-2 mt-2"
      >
        {generating && <Loader2 className="w-4 h-4 animate-spin" />}
        {generating ? "Generating..." : "Generate Forecasts"}
      </button>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [horizon, setHorizon] = useState(7);
  const [generating, setGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState(null);
  const [generateStatus, setGenerateStatus] = useState(null);
  const pollRef = useRef(null);
  const attemptsRef = useRef(0);

  const {
    latestRate, forecasts, allForecasts, history,
    metrics, loading, isStale, forecastDate, noForecasts,
    loadedModelNames, refetch,
  } = useDashboardData(horizon);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const stopPolling = () => {
    clearInterval(pollRef.current);
    pollRef.current = null;
    attemptsRef.current = 0;
    setGenerating(false);
    setGenerateStatus(null);
    setTimeout(() => setGenerateMsg(null), 3000);
  };

  const handleGenerate = async () => {
    if (pollRef.current) return;
    setGenerating(true);
    setGenerateStatus("starting");
    setGenerateMsg("Starting generation...");

    try {
      const result = await getForecasts.generate(horizon);
      if (result?.status === "already_fresh") {
        setGenerateStatus("complete");
        setGenerateMsg("✅ Forecasts are already up to date.");
        setTimeout(stopPolling, 3000);
        return;
      }
      setGenerateStatus("generating");
      setGenerateMsg("Generating — checking every 5s...");
      attemptsRef.current = 0;

      pollRef.current = setInterval(async () => {
        attemptsRef.current += 1;
        try {
          const status = await getForecasts.getStatus(horizon);
          if (status?.is_fresh) {
            await refetch();
            setGenerateStatus("complete");
            setGenerateMsg("✅ Forecasts updated!");
            setTimeout(stopPolling, 2000);
          } else if (attemptsRef.current >= 24) {
            setGenerateStatus("error");
            setGenerateMsg("⏰ Timed out. Please refresh and try again.");
            stopPolling();
          }
        } catch {
          if (attemptsRef.current >= 24) stopPolling();
        }
      }, 5000);
    } catch {
      setGenerateStatus("error");
      setGenerateMsg("Failed to start. Is the backend running?");
      setGenerating(false);
    }
  };

  // ── Derived values ─────────────────────────────────────────────────────────
  let direction = null, changePct = null;
  if (latestRate?.rate && forecasts?.prediction?.length) {
    const future = forecasts.prediction[forecasts.prediction.length - 1];
    const diff = future - latestRate.rate;
    direction = diff > 0 ? "up" : "down";
    changePct = ((diff / latestRate.rate) * 100).toFixed(2);
  }

  const forecastValue = forecasts?.prediction?.[forecasts.prediction.length - 1]?.toFixed(2) ?? null;
  const bestModel = metrics.length > 0
    ? metrics.reduce((best, m) => (!best || (m.mape ?? 999) < (best.mape ?? 999)) ? m : best, null)
    : null;

  const statusBadgeColor =
    generateStatus === "generating" ? "border-blue-500/30 bg-blue-500/10 text-blue-300" :
    generateStatus === "complete" ? "border-green-500/30 bg-green-500/10 text-green-300" :
    generateStatus === "error" ? "border-red-500/30 bg-red-500/10 text-red-300" :
    "border-blue-500/30 bg-blue-500/10 text-blue-300";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">Forecast Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">
            Ensemble forecasts · ARIMA · ARIMAX · Prophet · MWK/USD
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600">
            <option value={1}>Next Day</option>
            <option value={7}>7 Days</option>
            <option value={30}>30 Days</option>
          </select>
          <button onClick={handleGenerate} disabled={generating}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            {generating ? "Generating..." : "Generate"}
          </button>
        </div>
      </div>

      {/* ── Status message ── */}
      {generateMsg && (
        <div className={`rounded-xl p-3 text-sm flex items-center gap-2 border ${statusBadgeColor}`}>
          {generateStatus === "generating" && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
          {generateMsg}
        </div>
      )}

      {/* ── Stale banner ── */}
      {isStale && !generating && !noForecasts && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-4 flex items-center gap-3">
          <Clock className="w-5 h-5 text-yellow-400 shrink-0" />
          <p className="text-yellow-300 text-sm">
            Showing forecasts from {forecastDate ?? "a previous run"}. Click Generate to refresh.
          </p>
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-800/60 rounded-2xl h-28 border border-slate-700/60" />
          ))}
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && noForecasts && <EmptyForecasts onGenerate={handleGenerate} generating={generating} />}

      {/* ── KPI Cards ── */}
      {!loading && !noForecasts && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: "Current Rate", value: latestRate?.rate ? `MWK ${latestRate.rate.toFixed(2)}` : "--", icon: Zap, color: "text-blue-400" },
            { label: `${horizon}-Day Forecast`, value: forecastValue ? `MWK ${forecastValue}` : "--", change: direction && changePct ? `${direction === "up" ? "+" : ""}${changePct}%` : null, icon: direction === "up" ? TrendingUp : TrendingDown, color: direction === "up" ? "text-green-400" : "text-red-400" },
            { label: "Models Active", value: loadedModelNames?.length || 0, icon: Target, color: "text-purple-400" },
            { label: "Best Model", value: bestModel?.model_name?.toUpperCase() || "--", change: bestModel?.mape ? `MAPE: ${bestModel.mape.toFixed(1)}%` : null, icon: Shield, color: "text-emerald-400" },
          ].map((kpi, idx) => {
            const Icon = kpi.icon;
            return (
              <div key={idx} className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
                <div className="flex items-start justify-between mb-2">
                  <p className="text-slate-400 text-xs uppercase tracking-wider">{kpi.label}</p>
                  <Icon className={`w-5 h-5 ${kpi.color}`} />
                </div>
                <p className="text-2xl font-bold text-white">{kpi.value}</p>
                {kpi.change && <p className={`text-sm font-medium mt-1 ${kpi.color}`}>{kpi.change}</p>}
              </div>
            );
          })}
        </div>
      )}

      {/* ── TRUST CHART: Monthly Actual vs Forecast ── */}
      {!loading && history?.length > 30 && (
        <TrustChart history={history} forecasts={forecasts} />
      )}

      {/* ── Hero Rate Card ── */}
      {!loading && latestRate && (
        <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider">Current Exchange Rate</p>
              <p className="text-3xl font-bold text-white mt-1">MWK {latestRate.rate.toFixed(2)}</p>
              <p className="text-slate-500 text-xs mt-1">{latestRate.date} · {latestRate.source || 'Database'}</p>
            </div>
            {forecastValue && (
              <div className="text-right">
                <p className="text-sm text-slate-400">{horizon}-Day Forecast</p>
                <p className="text-2xl font-bold text-white">MWK {forecastValue}</p>
                {direction && changePct && (
                  <p className={`text-sm font-medium ${direction === "up" ? "text-green-400" : "text-red-400"}`}>
                    {direction === "up" ? "↗" : "↘"} {changePct}%
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Fan Chart ── */}
      {!loading && !noForecasts && <FanChart forecasts={forecasts} history={history} />}

      {/* ── History + Metrics ── */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">Historical Trends</h3>
            <HistoryChart history={history} loading={loading} forecasts={forecasts} />
          </div>
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              Model Accuracy
              {loadedModelNames.length > 0 && (
                <span className="ml-2 text-xs text-slate-500 normal-case font-normal">({loadedModelNames.join(", ")})</span>
              )}
            </h3>
            <ModelMetricsTable metrics={metrics} />
          </div>
        </div>
      )}

      {/* ── Disclaimer ── */}
      <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-5 flex gap-4">
        <AlertCircle className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <h3 className="font-semibold text-amber-300 mb-1">Important Disclaimer</h3>
          <p className="text-amber-200/80 text-sm">
            These forecasts are for informational purposes only. Exchange rates are influenced by many unpredictable factors.
          </p>
        </div>
      </div>
    </div>
  );
}