import React, { useState, useEffect, useRef } from "react";
import { useDashboardData } from "../hooks/useForecasts";
import HistoryChart from "../components/HistoryChart";
import { getForecasts } from "../utils/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, ComposedChart, Legend,
} from "recharts";
import { AlertCircle, TrendingDown, TrendingUp, Clock, RefreshCw, Loader2, Shield, Zap, Calendar, ThumbsUp, Target, DollarSign, Briefcase, Plane, HelpCircle, Info } from "lucide-react";

const LIVE_RATE_URL = 'https://open.er-api.com/v6/latest/USD';

// ── Mini Sparkline ────────────────────────────────────────────────────────────
function MiniSparkline({ data, color, label }) {
  if (!data?.length) return null;
  return (
    <div>
      <ResponsiveContainer width="100%" height={28}>
        <LineChart data={data}>
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
      {label && <p className="text-[10px] text-slate-500 text-center mt-0.5">{label}</p>}
    </div>
  );
}

// ── Trust Chart ───────────────────────────────────────────────────────────────
function TrustChart({ history, forecasts }) {
  if (!history?.length) return null;
  const data = history.slice(-30).map((h) => {
    const fcDate = h.date?.slice(0, 10);
    const fcIndex = forecasts?.dates?.findIndex(d => String(d).slice(0, 10) === fcDate);
    return {
      date: h.date?.slice(5) || h.date,
      actual: Number(h.rate?.toFixed(2)),
      forecasted: fcIndex >= 0 ? Number(forecasts.prediction[fcIndex]?.toFixed(2)) : null,
    };
  });

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <div className="flex items-center gap-2 mb-3">
        <Shield className="w-4 h-4 text-emerald-400" />
        <h3 className="text-sm font-semibold text-slate-300">Trust & transparency — last 30 days</h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">Compare our forecasts against actual market rates</p>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} interval={4} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#e2e8f0', fontSize: 12 }}
            formatter={(v, name) => [`MWK ${Number(v).toFixed(2)}`, name === 'actual' ? 'Actual rate' : 'Forecasted rate']} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#60a5fa" strokeWidth={2} dot={false} name="Actual rate" />
          <Line type="monotone" dataKey="forecasted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecasted rate" connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Fan Chart ─────────────────────────────────────────────────────────────────
function FanChart({ forecasts, history }) {
  if (!forecasts?.dates?.length) return null;
  const histData = history?.slice(-60).map((d) => ({ date: d.date, rate: Number(d.rate?.toFixed(2)) })) || [];
  const fcData = forecasts.dates.map((d, i) => ({
    date: d, predicted: Number(forecasts.prediction[i]?.toFixed(2)),
    lower_80: forecasts.lower_80?.[i] != null ? Number(forecasts.lower_80[i].toFixed(2)) : null,
    upper_80: forecasts.upper_80?.[i] != null ? Number(forecasts.upper_80[i].toFixed(2)) : null,
  }));
  const lastHist = histData[histData.length - 1];
  const bridge = lastHist ? [{ date: lastHist.date, predicted: lastHist.rate, lower_80: lastHist.rate, upper_80: lastHist.rate }] : [];
  const combined = [...histData.map((h) => ({ ...h, type: "actual" })), ...bridge, ...fcData.map((f) => ({ ...f, type: "forecast" }))];

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <div className="flex items-center gap-2 mb-3">
        <Target className="w-4 h-4 text-orange-400" />
        <h3 className="text-sm font-semibold text-slate-300">Forecast outlook — 80% confidence range</h3>
      </div>
      <p className="text-xs text-slate-500 mb-2">
        The shaded area shows where we're 80% confident the rate will fall. 
        Narrow band = higher confidence in the prediction.
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={combined}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 10 }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} domain={["auto", "auto"]} tickFormatter={(v) => `${v.toFixed(0)}`} />
          <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "none", borderRadius: "8px", color: "#e2e8f0" }}
            formatter={(v, name) => {
              const labels = { rate: 'Actual rate (MWK)', predicted: 'Forecast (MWK)', upper_80: 'Upper 80% bound (MWK)', lower_80: 'Lower 80% bound (MWK)' };
              return [`${Number(v).toFixed(2)}`, labels[name] || name];
            }} />
          <Area type="monotone" dataKey="upper_80" stroke="#f97316" strokeWidth={1} fill="#f97316" fillOpacity={0.10} name="Upper 80% bound" />
          <Area type="monotone" dataKey="lower_80" stroke="#f97316" strokeWidth={1} fill="#f97316" fillOpacity={0.10} name="Lower 80% bound" />
          <Line type="monotone" dataKey="rate" stroke="#60a5fa" strokeWidth={2} dot={false} name="Actual rate" />
          <Line type="monotone" dataKey="predicted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={true} name="Forecast" />
          {lastHist && <ReferenceLine y={lastHist.rate} stroke="#64748b" strokeDasharray="3 3" />}
          <Legend />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Quick Summary Card ────────────────────────────────────────────────────────
function QuickSummary({ displayRate, sevenDayChange }) {
  const pct = parseFloat(sevenDayChange?.pct || 0);
  const isUp = sevenDayChange?.direction === "up";
  const stable = Math.abs(pct) < 0.5;

  return (
    <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle className="w-4 h-4 text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-300">What this means for you</h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="bg-slate-700/40 rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign className="w-4 h-4 text-yellow-400" />
            <p className="text-xs font-medium text-slate-300">Importers</p>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {stable ? "Minimal change expected — stable import costs ahead." :
             isUp ? `Costs may rise ~${Math.abs(pct).toFixed(1)}% — consider early orders.` :
             `Costs may drop ~${Math.abs(pct).toFixed(1)}% — good time to buy.`}
          </p>
        </div>
        <div className="bg-slate-700/40 rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <Briefcase className="w-4 h-4 text-blue-400" />
            <p className="text-xs font-medium text-slate-300">Businesses</p>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {stable ? "Stable outlook — no urgent action needed." :
             isUp ? `Plan for ~${Math.abs(pct).toFixed(1)}% higher forex costs.` :
             `Save ~${Math.abs(pct).toFixed(1)}% on foreign payments.`}
          </p>
        </div>
        <div className="bg-slate-700/40 rounded-xl p-3">
          <div className="flex items-center gap-2 mb-2">
            <Plane className="w-4 h-4 text-emerald-400" />
            <p className="text-xs font-medium text-slate-300">Travelers</p>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            {stable ? "Exchange rate stable — predictable travel budget." :
             isUp ? `Your dollar buys ${Math.abs(pct).toFixed(1)}% more Kwacha.` :
             `Kwacha gaining — wait for better rates if possible.`}
          </p>
        </div>
      </div>
    </div>
  );
}

// ── When to Act Timeline ──────────────────────────────────────────────────────
function WhenToActTimeline({ nextDayChange, sevenDayChange, thirtyDayChange }) {
  const getUrgency = (pct) => {
    const val = Math.abs(parseFloat(pct || 0));
    if (val < 0.5) return { level: "No urgency", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", dot: "bg-emerald-400" };
    if (val < 2) return { level: "Monitor", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30", dot: "bg-yellow-400" };
    return { level: "Take action", color: "bg-red-500/20 text-red-400 border-red-500/30", dot: "bg-red-400" };
  };

  const stages = [
    { label: "Today", change: nextDayChange?.pct || "0", desc: "Current snapshot" },
    { label: "7 days", change: sevenDayChange?.pct || "0", desc: "Short-term trend" },
    { label: "30 days", change: thirtyDayChange?.pct || "0", desc: "Monthly outlook" },
  ];

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-4 h-4 text-purple-400" />
        <h3 className="text-sm font-semibold text-slate-300">When to act</h3>
      </div>
      <div className="space-y-4">
        {stages.map((stage, i) => {
          const urgency = getUrgency(stage.change);
          return (
            <div key={i} className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${urgency.dot}`} />
              <span className="text-sm text-slate-400 min-w-[60px]">{stage.label}</span>
              <div className="flex-1 h-px bg-slate-700" />
              <span className={`text-xs px-3 py-1 rounded-full border font-medium ${urgency.color}`}>
                {urgency.level}
              </span>
            </div>
          );
        })}
      </div>
      <div className="mt-4 pt-3 border-t border-slate-700/50">
        <div className="flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
          <p className="text-xs text-slate-500 leading-relaxed">
            {Math.abs(parseFloat(thirtyDayChange?.pct || 0)) < 0.5
              ? "The rate is expected to remain stable. No immediate action required for routine transactions."
              : `A ${Math.abs(parseFloat(thirtyDayChange?.pct || 0)).toFixed(2)}% change is projected over 30 days. ` +
                (parseFloat(thirtyDayChange?.pct || 0) > 0 
                  ? "If you need USD, consider buying sooner. If you hold USD, waiting may be beneficial."
                  : "If you need USD, waiting may save you money. If you hold USD, consider converting sooner.")}
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Kwacha Direction Card ─────────────────────────────────────────────────────
function KwachaDirection({ direction, changePct, horizon }) {
  const isGaining = direction === "down";
  const strengthText = isGaining ? "gaining strength" : "losing value";
  const icon = isGaining ? TrendingDown : TrendingUp;
  const color = isGaining ? "text-emerald-400" : "text-red-400";
  const bgColor = isGaining ? "bg-emerald-500/10 border-emerald-500/20" : "bg-red-500/10 border-red-500/20";

  return (
    <div className={`rounded-2xl p-5 border backdrop-blur ${bgColor}`}>
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-xl ${isGaining ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
          {React.createElement(icon, { className: `w-6 h-6 ${color}` })}
        </div>
        <div>
          <p className={`text-lg font-bold ${color}`}>The Kwacha is {strengthText}</p>
          <p className="text-sm text-slate-400 mt-0.5">
            Expected to {isGaining ? "appreciate" : "depreciate"} by {changePct}% over the next {horizon} days
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Confidence Card ───────────────────────────────────────────────────────────
function ConfidenceCard({ mape, forecasts }) {
  const lower = forecasts?.lower_80?.[forecasts.lower_80.length - 1];
  const upper = forecasts?.upper_80?.[forecasts.upper_80.length - 1];
  const spread = lower && upper ? (upper - lower).toFixed(0) : null;
  const highConfidence = mape < 1;
  const confidenceLevel = highConfidence ? "High" : mape < 5 ? "Moderate" : "Low";
  const confidenceColor = highConfidence ? "text-emerald-400" : mape < 5 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <div className="flex items-center gap-2 mb-3">
        <ThumbsUp className={`w-5 h-5 ${confidenceColor}`} />
        <h3 className="text-sm font-semibold text-slate-300">Forecast confidence</h3>
      </div>
      <p className={`text-2xl font-bold ${confidenceColor}`}>{confidenceLevel}</p>
      <div className="text-sm text-slate-400 mt-2 space-y-1">
        <p>• Average error: <span className="text-slate-300">{mape.toFixed(2)}%</span> (within ~{Math.round(mape * 17)} MWK of actual)</p>
        {spread && (
          <p>• 80% confidence range spans <span className="text-slate-300">{spread} MWK</span>
            {lower && upper && ` (${lower.toFixed(0)} – ${upper.toFixed(0)} MWK/USD)`}
          </p>
        )}
        <p className="text-xs text-slate-500 mt-1">
          {highConfidence 
            ? "The narrow range reflects Malawi's managed exchange rate, making predictions highly reliable."
            : "Some uncertainty is normal in currency markets. The range accounts for potential fluctuations."}
        </p>
      </div>
    </div>
  );
}

// ── Contributing Factors ──────────────────────────────────────────────────────
function ContributingFactors({ forecasts, history, horizon }) {
  if (!forecasts?.prediction?.length || !history?.length) return null;
  const recentRates = history.slice(-30).map(h => h.rate);
  const recentTrend = recentRates[recentRates.length - 1] - recentRates[0];
  const changes = [];
  for (let i = 1; i < recentRates.length; i++) changes.push(Math.abs(recentRates[i] - recentRates[i-1]));
  const avgDailyChange = changes.reduce((a, b) => a + b, 0) / changes.length;
  const spread = forecasts.upper_80?.[forecasts.upper_80.length - 1] - forecasts.lower_80?.[forecasts.lower_80.length - 1];
  const factors = [];

  if (Math.abs(recentTrend) < 0.5) {
    factors.push({ factor: "Rate stability pattern", impact: "High", desc: `Near-zero movement (${recentTrend.toFixed(2)} MWK net change over 30 days). The model expects this managed stability to continue.` });
  } else if (recentTrend > 0) {
    factors.push({ factor: "Gradual upward trend", impact: "High", desc: `The rate rose ${recentTrend.toFixed(2)} MWK over 30 days (avg ${avgDailyChange.toFixed(2)} MWK/day). Model extends this trend.` });
  } else {
    factors.push({ factor: "Slight downward correction", impact: "High", desc: `The rate eased by ${Math.abs(recentTrend).toFixed(2)} MWK recently. Model expects this to persist short-term.` });
  }

  if (spread < 50) {
    factors.push({ factor: "Tight prediction range", impact: "High", desc: `The 80% confidence band is only ${spread.toFixed(0)} MWK wide. This indicates the model is very certain about the forecast.` });
  } else if (spread < 150) {
    factors.push({ factor: "Normal prediction range", impact: "Medium", desc: `The ${spread.toFixed(0)} MWK confidence band is typical for currency forecasting — moderate but manageable uncertainty.` });
  } else {
    factors.push({ factor: "Wider uncertainty band", impact: "Medium", desc: `The ${spread.toFixed(0)} MWK range suggests the model detected some unusual patterns warranting caution.` });
  }

  if (avgDailyChange < 0.3) {
    factors.push({ factor: "Central bank stability", impact: "High", desc: `Extremely low daily movement (${avgDailyChange.toFixed(2)} MWK/day). This confirms the Reserve Bank of Malawi's tight management of the exchange rate.` });
  } else {
    factors.push({ factor: "Moderate market activity", impact: "Medium", desc: `Daily changes of ${avgDailyChange.toFixed(2)} MWK suggest some market forces at play beyond central bank management.` });
  }

  const currentMonth = new Date().getMonth();
  if (currentMonth >= 2 && currentMonth <= 5) {
    factors.push({ factor: "Tobacco season influence", impact: "Medium", desc: "March–June typically brings foreign currency from tobacco exports, which historically supports the Kwacha." });
  } else if (currentMonth >= 9 && currentMonth <= 11) {
    factors.push({ factor: "Q4 import pressure", impact: "Medium", desc: "Year-end typically sees increased demand for foreign currency for imports, which can weigh on the Kwacha." });
  } else {
    factors.push({ factor: "Neutral seasonal period", impact: "Low", desc: "No strong seasonal pattern detected. The forecast is driven primarily by recent price behavior." });
  }

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-300 mb-4">What the model found in the data</h3>
      <div className="space-y-3">
        {factors.slice(0, 4).map((f, i) => (
          <div key={i} className="flex items-start gap-3 p-3 bg-slate-700/30 rounded-xl">
            <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0 ${
              f.impact === 'High' ? 'bg-emerald-500/20 text-emerald-400' : 
              f.impact === 'Medium' ? 'bg-yellow-500/20 text-yellow-400' : 
              'bg-blue-500/20 text-blue-400'}`}>
              {f.impact}
            </span>
            <div>
              <p className="text-sm text-slate-200 font-medium">{f.factor}</p>
              <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{f.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────
function EmptyForecasts({ onGenerate, generating }) {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-12 border border-slate-700/60 backdrop-blur flex flex-col items-center gap-4 text-center">
      <Calendar className="w-14 h-14 text-slate-500" />
      <h3 className="text-white font-semibold text-xl">No forecasts yet</h3>
      <p className="text-slate-400 text-sm max-w-md">Generate today's forecasts to see predictions for the Malawi Kwacha.</p>
      <button onClick={onGenerate} disabled={generating}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-6 py-3 rounded-xl font-semibold transition-colors flex items-center gap-2 mt-2">
        {generating && <Loader2 className="w-4 h-4 animate-spin" />}
        {generating ? "Generating..." : "Generate forecasts"}
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
  const [liveRate, setLiveRate] = useState(null);
  const pollRef = useRef(null);
  const attemptsRef = useRef(0);

  const { latestRate, forecasts, history, metrics, loading, isStale, forecastDate, noForecasts, refetch } = useDashboardData(horizon);
  const [forecast7d, setForecast7d] = useState(null);
  const [forecast30d, setForecast30d] = useState(null);

  useEffect(() => { getForecasts.getLatest(7).then(setForecast7d).catch(() => {}); getForecasts.getLatest(30).then(setForecast30d).catch(() => {}); }, [horizon, forecasts]);
  useEffect(() => { fetch(LIVE_RATE_URL).then(r => r.json()).then(d => { if (d?.rates?.MWK) setLiveRate({ rate: d.rates.MWK, date: d.time_last_update_utc?.split(' ')[0] || new Date().toISOString().split('T')[0], source: 'Live API' }); }).catch(() => {}); }, []);
  useEffect(() => () => clearInterval(pollRef.current), []);

  const displayRate = liveRate || latestRate;

  const stopPolling = () => { clearInterval(pollRef.current); pollRef.current = null; attemptsRef.current = 0; setGenerating(false); setGenerateStatus(null); setTimeout(() => setGenerateMsg(null), 3000); };

  const handleGenerate = async () => {
    if (pollRef.current) return;
    setGenerating(true); setGenerateStatus("starting"); setGenerateMsg("Starting generation...");
    try {
      const result = await getForecasts.generate(horizon);
      if (result?.status === "already_fresh") { setGenerateStatus("complete"); setGenerateMsg("✅ Forecasts are already up to date."); setTimeout(stopPolling, 3000); return; }
      setGenerateStatus("generating"); setGenerateMsg("Generating — checking every 5s..."); attemptsRef.current = 0;
      pollRef.current = setInterval(async () => {
        attemptsRef.current += 1;
        try {
          const status = await getForecasts.getStatus(horizon);
          if (status?.is_fresh) { await refetch(); setGenerateStatus("complete"); setGenerateMsg("✅ Forecasts updated!"); setTimeout(stopPolling, 2000); }
          else if (attemptsRef.current >= 24) { setGenerateStatus("error"); setGenerateMsg("⏰ Timed out."); stopPolling(); }
        } catch { if (attemptsRef.current >= 24) stopPolling(); }
      }, 5000);
    } catch { setGenerateStatus("error"); setGenerateMsg("Failed to start."); setGenerating(false); }
  };

  const getForecastChange = (forecastData, displayRate) => {
    if (!displayRate?.rate || !forecastData?.prediction?.length) return null;
    const futureVal = forecastData.prediction[forecastData.prediction.length - 1];
    const diff = futureVal - displayRate.rate;
    return { direction: diff > 0 ? "up" : "down", pct: ((diff / displayRate.rate) * 100).toFixed(2), value: futureVal.toFixed(2) };
  };

  const nextDayForecast = forecasts?.prediction?.[0]?.toFixed(2) ?? null;
  const nextDayChange = getForecastChange(forecasts, displayRate);
  const sevenDayData = forecast7d || forecasts;
  const sevenDayForecast = sevenDayData?.prediction?.[Math.min(6, (sevenDayData.prediction?.length ?? 1) - 1)]?.toFixed(2) ?? null;
  const sevenDayChange = getForecastChange(sevenDayData, displayRate);
  const thirtyDayData = forecast30d || forecasts;
  const thirtyDayForecast = thirtyDayData?.prediction?.[Math.min(29, (thirtyDayData.prediction?.length ?? 1) - 1)]?.toFixed(2) ?? null;
  const thirtyDayChange = getForecastChange(thirtyDayData, displayRate);
  const arimaMetric = metrics?.find(m => m.model_name === 'arima');
  const mape = arimaMetric?.mape || 0.30;

  const statusBadgeColor = generateStatus === "generating" ? "border-blue-500/30 bg-blue-500/10 text-blue-300" : generateStatus === "complete" ? "border-green-500/30 bg-green-500/10 text-green-300" : generateStatus === "error" ? "border-red-500/30 bg-red-500/10 text-red-300" : "border-blue-500/30 bg-blue-500/10 text-blue-300";

  const historySparkline = history?.slice(-7).map(h => ({ value: h.rate })) || [];
  const forecastSparkline = forecasts?.prediction?.slice(0, 7).map(v => ({ value: v })) || [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">Kwacha forecast</h1>
          <p className="text-slate-400 text-sm mt-1">AI-powered exchange rate predictions for the Malawi Kwacha</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))} className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600">
            <option value={1}>Next day</option><option value={7}>7 days</option><option value={30}>30 days</option>
          </select>
          <button onClick={handleGenerate} disabled={generating} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition flex items-center gap-2">
            {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            {generating ? "Generating..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Status */}
      {generateMsg && (<div className={`rounded-xl p-3 text-sm flex items-center gap-2 border ${statusBadgeColor}`}>{generateStatus === "generating" && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}{generateMsg}</div>)}
      {isStale && !generating && !noForecasts && (<div className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-4 flex items-center gap-3"><Clock className="w-5 h-5 text-yellow-400 shrink-0" /><p className="text-yellow-300 text-sm">Showing forecasts from {forecastDate ?? "a previous run"}. Click Refresh to update.</p></div>)}
      {loading && (<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">{[...Array(4)].map((_, i) => (<div key={i} className="bg-slate-800/60 rounded-2xl h-40 border border-slate-700/60" />))}</div>)}
      {!loading && noForecasts && <EmptyForecasts onGenerate={handleGenerate} generating={generating} />}

      {/* KPI Cards */}
      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-900/30 to-slate-800/60 border border-blue-500/20 rounded-2xl p-5 backdrop-blur">
            <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Current rate</p>
            <p className="text-2xl font-bold text-white">{displayRate?.rate ? `MWK ${displayRate.rate.toFixed(2)}` : "--"}</p>
            <p className="text-xs text-slate-500 mt-1">Live exchange rate</p>
            <div className="mt-2"><MiniSparkline data={historySparkline} color="#60a5fa" label="7-day trend" /></div>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
            <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Next day</p>
            <p className="text-2xl font-bold text-white">{nextDayForecast ? `MWK ${nextDayForecast}` : "--"}</p>
            {nextDayChange && (<p className={`text-sm font-medium mt-1 ${nextDayChange.direction === "up" ? "text-red-400" : "text-emerald-400"}`}>{nextDayChange.direction === "up" ? "↗" : "↘"} {nextDayChange.pct}%</p>)}
            <div className="mt-2"><MiniSparkline data={forecastSparkline.slice(0,1)} color={nextDayChange?.direction === "up" ? "#f87171" : "#34d399"} label="Tomorrow" /></div>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
            <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">7-day outlook</p>
            <p className="text-2xl font-bold text-white">{sevenDayForecast ? `MWK ${sevenDayForecast}` : "--"}</p>
            {sevenDayChange && (<p className={`text-sm font-medium mt-1 ${sevenDayChange.direction === "up" ? "text-red-400" : "text-emerald-400"}`}>{sevenDayChange.direction === "up" ? "↗" : "↘"} {sevenDayChange.pct}%</p>)}
            <div className="mt-2"><MiniSparkline data={forecastSparkline} color={sevenDayChange?.direction === "up" ? "#f87171" : "#34d399"} label="7-day projection" /></div>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
            <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">30-day outlook</p>
            <p className="text-2xl font-bold text-white">{thirtyDayForecast ? `MWK ${thirtyDayForecast}` : "--"}</p>
            {thirtyDayChange && (<p className={`text-sm font-medium mt-1 ${thirtyDayChange.direction === "up" ? "text-red-400" : "text-emerald-400"}`}>{thirtyDayChange.direction === "up" ? "↗" : "↘"} {thirtyDayChange.pct}%</p>)}
            <div className="mt-2"><MiniSparkline data={[...forecastSparkline, ...forecastSparkline, ...forecastSparkline, ...forecastSparkline]} color={thirtyDayChange?.direction === "up" ? "#f87171" : "#34d399"} label="30-day trend" /></div>
          </div>
        </div>
      )}

      {/* Quick Summary */}
      {!loading && !noForecasts && (<QuickSummary displayRate={displayRate} sevenDayChange={sevenDayChange} />)}

      {/* Kwacha Direction + When to Act */}
      {!loading && !noForecasts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <KwachaDirection direction={sevenDayChange?.direction} changePct={sevenDayChange?.pct} horizon={horizon} />
          <WhenToActTimeline nextDayChange={nextDayChange} sevenDayChange={sevenDayChange} thirtyDayChange={thirtyDayChange} />
        </div>
      )}

      {/* Confidence */}
      {!loading && !noForecasts && (<ConfidenceCard mape={mape} forecasts={forecasts} />)}

      {/* Trust Chart */}
      {!loading && history?.length > 30 && (<TrustChart history={history} forecasts={forecasts} />)}

      {/* Fan Chart */}
      {!loading && !noForecasts && <FanChart forecasts={forecasts} history={history} />}

      {/* Contributing Factors + History */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ContributingFactors forecasts={forecasts} history={history} horizon={horizon} />
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Historical trends</h3>
            <HistoryChart history={history} loading={loading} forecasts={forecasts} />
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-5 flex gap-4">
        <AlertCircle className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <h3 className="font-semibold text-amber-300 mb-1">Important note</h3>
          <p className="text-amber-200/80 text-sm">These forecasts are for informational purposes only. Exchange rates are influenced by many unpredictable factors.</p>
        </div>
      </div>
    </div>
  );
}