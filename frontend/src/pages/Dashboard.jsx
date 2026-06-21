import React, { useState, useEffect, useRef } from "react";
import { useDashboardData } from "../hooks/useForecasts";
import HistoryChart from "../components/HistoryChart";
import ModelMetricsTable from "../components/ModelMetricsTable";
import { getForecasts } from "../utils/api";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, ComposedChart, Legend,
} from "recharts";
import { AlertCircle, TrendingDown, TrendingUp, Clock, RefreshCw, Loader2 } from "lucide-react";

// ── Model Consensus ────────────────────────────────────────────────────────────
function ModelConsensus({ models, latestRate, horizon }) {
  if (!models || !latestRate || models.length === 0) return null;
  const directions = models.map((m) => {
    const lastPred = m.prediction?.[Math.min(horizon - 1, m.prediction.length - 1)] ?? 0;
    return lastPred > latestRate ? "up" : "down";
  });
  const upCount   = directions.filter((d) => d === "up").length;
  const downCount = directions.length - upCount;
  const consensus = upCount > downCount ? "Kukwera (Appreciation)" : "Kutsika (Depreciation)";

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
        Model Consensus
      </h3>
      <div className="flex items-center justify-between">
        <div className="flex gap-2 items-center">
          <span className="text-green-400 text-xl font-bold">{upCount}</span>
          <span className="text-slate-400 text-sm">Up</span>
          <span className="text-red-400 text-xl font-bold ml-3">{downCount}</span>
          <span className="text-slate-400 text-sm">Down</span>
        </div>
        <div className="text-right">
          <p className="text-white font-bold text-lg">{consensus}</p>
          <p className="text-slate-400 text-xs">{models.length} models reporting</p>
        </div>
      </div>
    </div>
  );
}

// ── Fan Chart ──────────────────────────────────────────────────────────────────
function FanChart({ forecasts, history }) {
  if (!forecasts?.dates?.length) return null;
  const histData = history?.slice(-60).map((d) => ({ date: d.date, rate: d.rate })) || [];
  const fcData   = forecasts.dates.map((d, i) => ({
    date:      d,
    predicted: forecasts.prediction[i],
    lower_80:  forecasts.lower_80?.[i] ?? null,
    upper_80:  forecasts.upper_80?.[i] ?? null,
  }));
  const lastHist = histData[histData.length - 1];
  const bridge   = lastHist
    ? [{ date: lastHist.date, predicted: lastHist.rate, lower_80: lastHist.rate, upper_80: lastHist.rate }]
    : [];
  const combined = [
    ...histData.map((h) => ({ ...h, type: "actual" })),
    ...bridge,
    ...fcData.map((f) => ({ ...f, type: "forecast" })),
  ];

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
        Forecast Fan (80% Confidence)
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={combined}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} />
          <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} domain={["auto", "auto"]} />
          <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "none", borderRadius: "8px", color: "#e2e8f0" }} />
          <Area type="monotone" dataKey="upper_80" stroke="none" fill="#f97316" fillOpacity={0.15} />
          <Area type="monotone" dataKey="lower_80" stroke="none" fill="#f97316" fillOpacity={0.15} />
          <Line type="monotone" dataKey="rate"      stroke="#60a5fa" strokeWidth={2} dot={false} name="Actual" />
          <Line type="monotone" dataKey="predicted" stroke="#fbbf24" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Forecast" />
          {lastHist && <ReferenceLine y={lastHist.rate} stroke="#64748b" strokeDasharray="3 3" />}
          <Legend />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Model Interpretation ───────────────────────────────────────────────────────
function ModelInterpretation({ forecasts, language, horizon, latestRate }) {
  if (!forecasts?.prediction?.length || !latestRate) return null;
  const futureValue = forecasts.prediction[forecasts.prediction.length - 1];
  const diff        = futureValue - latestRate;
  const direction   = diff > 0 ? "weaken" : "strengthen";
  const pct         = Math.abs((diff / latestRate) * 100).toFixed(2) + "%";
  const dirText     = language === "ny"
    ? (direction === "weaken" ? "kutsika" : "kukwera")
    : direction;
  const summary = language === "ny"
    ? `M'tsogolo mwa masiku ${horizon}, Kwacha iku${dirText} ndi ${pct}.`
    : `The ${horizon}-day outlook suggests the Kwacha will ${direction} by ${pct}.`;
  const details = language === "ny"
    ? "Zochokera ku gulu la ma model a ARIMA, ARIMAX ndi Ensemble."
    : "Based on ensemble of ARIMA, ARIMAX, and Ensemble models.";

  return (
    <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
      <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
        Outlook Summary
      </h3>
      <p className="text-white font-medium">{summary}</p>
      <p className="text-slate-400 text-sm mt-1">{details}</p>
    </div>
  );
}

// ── Empty State ────────────────────────────────────────────────────────────────
function EmptyForecasts({ onGenerate, generating, t }) {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-10 border border-slate-700/60 backdrop-blur flex flex-col items-center gap-4 text-center">
      <RefreshCw className="w-12 h-12 text-slate-500" />
      <h3 className="text-white font-semibold text-lg">{t("No Forecasts Yet", "Palibe Zolosera")}</h3>
      <p className="text-slate-400 text-sm max-w-sm">
        {t(
          "No forecast data found. Click below to generate today's forecasts.",
          "Palibe zolosera mu database. Dinani batani pansipa."
        )}
      </p>
      <button
        onClick={onGenerate}
        disabled={generating}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white px-6 py-2.5 rounded-lg font-medium transition-colors flex items-center gap-2"
      >
        {generating && <Loader2 className="w-4 h-4 animate-spin" />}
        {generating ? t("Generating...", "Tikupanga...") : t("Generate Forecasts", "Pangani Ma Forecast")}
      </button>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [horizon, setHorizon]                 = useState(7);
  const [generating, setGenerating]           = useState(false);
  const [lang, setLang]                       = useState("en");
  const [showModelDetail, setShowModelDetail] = useState(false);
  const [generateMsg, setGenerateMsg]         = useState(null);
  const [generateStatus, setGenerateStatus]   = useState(null); // 'starting' | 'generating' | 'complete' | 'error'
  const pollRef                               = useRef(null);
  const attemptsRef                           = useRef(0);

  const {
    latestRate, forecasts, allForecasts, history,
    metrics, anomalies, loading, forecast30d,
    isStale, forecastDate, noForecasts,
    loadedModelNames, refetch,
  } = useDashboardData(horizon);

  useEffect(() => () => clearInterval(pollRef.current), []);

  const t = (en, ny) => (lang === "ny" ? ny : en);

  const stopPolling = () => {
    clearInterval(pollRef.current);
    pollRef.current     = null;
    attemptsRef.current = 0;
    setGenerating(false);
    setGenerateStatus(null);
    // Keep success message for a moment
    setTimeout(() => setGenerateMsg(null), 3000);
  };

  const handleGenerate = async () => {
    if (pollRef.current) return;

    setGenerating(true);
    setGenerateStatus("starting");
    setGenerateMsg(t("Starting generation...", "Tikuyamba..."));

    try {
      const result = await getForecasts.generate(horizon);

      if (result?.status === "already_fresh") {
        setGenerateStatus("complete");
        setGenerateMsg(t("✅ Forecasts are already up to date.", "✅ Zolosera ndi zatsopano kale."));
        setTimeout(stopPolling, 3000);
        return;
      }

      if (result?.status === "already_generating") {
        setGenerateMsg(t("Generation already in progress...", "Kupanga kuli mkati..."));
        // Still start polling to catch when it completes
      }

      setGenerateStatus("generating");
      setGenerateMsg(t("Generating in background — checking every 5s...", "Tikupanga — tikuyang'anira..."));
      attemptsRef.current = 0;

      pollRef.current = setInterval(async () => {
        attemptsRef.current += 1;

        try {
          const status = await getForecasts.getStatus(horizon);

          // Handle different status responses
          if (status?.status === "generating") {
            // Still generating - update message with progress
            setGenerateMsg(t(
              `Generating... (${attemptsRef.current * 5}s)`,
              `Tikupanga... (${attemptsRef.current * 5}s)`
            ));
            return;
          }

          if (status?.is_fresh) {
            await refetch();
            setGenerateStatus("complete");
            setGenerateMsg(t("✅ Forecasts updated!", "✅ Zolosera zasinthidwa!"));
            setTimeout(stopPolling, 2000);
            return;
          }

          if (status?.status === "error") {
            setGenerateStatus("error");
            setGenerateMsg(t(
              "⚠️ Generation encountered an error. Please try again.",
              "⚠️ Kupanga kwalephera. Yesaninso."
            ));
            stopPolling();
            return;
          }

          if (attemptsRef.current >= 24) {
            setGenerateStatus("error");
            setGenerateMsg(t(
              "⏰ Generation timed out. Please refresh and try again.",
              "⏰ Kupanga kwachedwa. Yesaninso."
            ));
            stopPolling();
          }
        } catch (pollError) {
          // Silently handle polling errors - don't stop polling
          if (attemptsRef.current >= 24) {
            setGenerateStatus("error");
            setGenerateMsg(t(
              "❌ Unable to check status. Server may be unavailable.",
              "❌ Sikuti titha kuyang'ana. Server ikhala pansi."
            ));
            stopPolling();
          }
        }
      }, 5000);

    } catch (e) {
      console.error("Generate error:", e);
      setGenerateStatus("error");
      setGenerateMsg(t(
        "Failed to start generation. Is the backend running?",
        "Zalephera kuyambitsa. Kodi backend ikugwira?"
      ));
      setGenerating(false);
    }
  };

  // ── Derived values ─────────────────────────────────────────────────────────
  let direction = null;
  let changePct = null;
  if (latestRate?.rate && forecasts?.prediction?.length) {
    const future = forecasts.prediction[forecasts.prediction.length - 1];
    const diff   = future - latestRate.rate;
    direction    = diff > 0 ? "up" : "down";
    changePct    = ((diff / latestRate.rate) * 100).toFixed(2);
  }

  const sevenDayForecast  = forecasts?.prediction?.[Math.min(6,  (forecasts.prediction?.length  ?? 1) - 1)]?.toFixed(2) ?? null;
  const thirtyDayForecast = forecast30d?.prediction?.[Math.min(29, (forecast30d.prediction?.length ?? 1) - 1)]?.toFixed(2) ?? null;
  const avgMape           = metrics.length > 0
    ? (metrics.reduce((s, m) => s + (m.mape || 0), 0) / metrics.length).toFixed(2) + "%"
    : null;
  const bestModel         = metrics.length > 0
    ? metrics.reduce((best, m) => (!best || (m.mape ?? 999) < (best.mape ?? 999)) ? m : best, null)
    : null;
  const modelConfidence   = bestModel?.r_squared != null
    ? (bestModel.r_squared * 100).toFixed(1) + "%"
    : null;

  const kpis = [
    {
      label:  t("7-Day Forecast", "Zolosera za Masiku 7"),
      value:  sevenDayForecast ? `MWK ${sevenDayForecast}` : "--",
      change: direction && changePct ? `${direction === "up" ? "+" : ""}${changePct}%` : null,
      icon:   direction === "up" ? TrendingUp : TrendingDown,
      color:  direction === "up" ? "text-green-400" : direction === "down" ? "text-red-400" : "text-slate-400",
    },
    {
      label:  t("30-Day Forecast", "Zolosera za Masiku 30"),
      value:  thirtyDayForecast ? `MWK ${thirtyDayForecast}` : "--",
      change: null,
      icon:   TrendingUp,
      color:  "text-blue-400",
    },
    {
      label:  t("Best Model R²", "R² ya Model Yabwino"),
      value:  modelConfidence ?? "--",
      change: bestModel ? bestModel.model_name.toUpperCase() : null,
      icon:   TrendingUp,
      color:  "text-blue-400",
    },
    {
      label:  t("Avg. Model MAPE", "MAPE ya Mamodel Onse"),
      value:  avgMape ?? "--",
      change: null,
      icon:   TrendingDown,
      color:  "text-green-400",
    },
  ];

  // ── Determine status badge color ──────────────────────────────────────────
  const statusBadgeColor = 
    generateStatus === "generating" ? "border-blue-500/30 bg-blue-500/10 text-blue-300" :
    generateStatus === "complete"   ? "border-green-500/30 bg-green-500/10 text-green-300" :
    generateStatus === "error"      ? "border-red-500/30 bg-red-500/10 text-red-300" :
    "border-blue-500/30 bg-blue-500/10 text-blue-300";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">
            {t("Kwacha Forecast Command", "Dashibodi ya Mwawi wa Kwacha")}
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            {t("Real-time ensemble forecasts · MWK/USD", "Zolosera zogwirizana · ARIMA · ARIMAX · ENSEMBLE")}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => setLang((l) => (l === "en" ? "ny" : "en"))}
            className="px-3 py-1.5 rounded-lg bg-slate-700 text-white text-xs font-medium hover:bg-slate-600 transition"
          >
            {lang === "en" ? "Chichewa" : "English"}
          </button>
          <select
            value={horizon}
            onChange={(e) => setHorizon(Number(e.target.value))}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600"
          >
            <option value={1}>{t("Next Day", "Tsiku Limodzi")}</option>
            <option value={7}>{t("7 Days", "Masiku 7")}</option>
            <option value={30}>{t("30 Days", "Masiku 30")}</option>
          </select>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-slate-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition-colors flex items-center gap-2"
          >
            {generating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <RefreshCw className="w-3.5 h-3.5" />
            )}
            {generating
              ? t("Generating...", "Tikupanga...")
              : t("Generate Forecasts", "Pangani Ma Forecast")}
          </button>
        </div>
      </div>

      {/* ── Generation status message ── */}
      {generateMsg && (
        <div className={`rounded-xl p-3 text-sm flex items-center gap-2 border ${statusBadgeColor}`}>
          {generateStatus === "generating" && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
          {generateStatus === "complete" && <span className="text-green-400">✅</span>}
          {generateStatus === "error" && <span className="text-red-400">⚠️</span>}
          {generateMsg}
        </div>
      )}

      {/* ── Stale data banner ── */}
      {isStale && !generating && !noForecasts && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-2xl p-4 flex items-center gap-3">
          <Clock className="w-5 h-5 text-yellow-400 shrink-0" />
          <p className="text-yellow-300 text-sm flex-1">
            {t(
              `Showing forecasts from ${forecastDate ?? "a previous run"}. Click "Generate Forecasts" to refresh.`,
              `Mukuwonetsa zolosera zakale (${forecastDate ?? "tsiku lapita"}). Dinani "Pangani Ma Forecast".`
            )}
          </p>
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-800/60 rounded-2xl h-28 border border-slate-700/60" />
          ))}
        </div>
      )}

      {/* ── Empty state ── */}
      {!loading && noForecasts && (
        <EmptyForecasts onGenerate={handleGenerate} generating={generating} t={t} />
      )}

      {/* ── KPI Cards ── */}
      {!loading && !noForecasts && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((kpi, idx) => {
            const Icon = kpi.icon;
            return (
              <div key={idx} className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="text-slate-400 text-xs uppercase tracking-wider">{kpi.label}</p>
                    <p className="text-2xl font-bold text-white mt-1">{kpi.value}</p>
                  </div>
                  <Icon className={`w-7 h-7 ${kpi.color}`} />
                </div>
                {kpi.change && (
                  <p className={`text-sm font-semibold ${kpi.color}`}>{kpi.change}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Rest of dashboard unchanged ── */}
      {/* ... (keep the same Hero Rate Card, FanChart, Sparkline, Consensus, etc.) ... */}

      {/* ── Hero Rate Card ── */}
      {!loading && latestRate && (
        <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/40 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <p className="text-slate-400 text-xs uppercase tracking-wider">
                {t("Current Rate", "Mtengo Wapano")}
              </p>
              <p className="text-3xl font-bold text-white mt-1">
                MWK {latestRate.rate.toFixed(2)}
              </p>
              <p className="text-slate-500 text-xs mt-1">
                {latestRate.date}
                {latestRate.stale && (
                  <span className="ml-2 text-yellow-400">(stale — live fetch failed)</span>
                )}
              </p>
            </div>
            {forecasts?.prediction?.length > 0 && (
              <div className="text-right">
                <p className="text-sm text-slate-400">
                  {t("Forecast", "Zolosera")} ({horizon}d)
                </p>
                <p className="text-2xl font-bold text-white">
                  MWK {forecasts.prediction[forecasts.prediction.length - 1]?.toFixed(2)}
                </p>
                {direction && changePct && (
                  <p className={`text-sm font-medium ${direction === "up" ? "text-green-400" : "text-red-400"}`}>
                    {direction === "up" ? "↗" : "↘"} {changePct}%
                  </p>
                )}
              </div>
            )}
            {allForecasts.length > 0 && (
              <button
                onClick={() => setShowModelDetail(!showModelDetail)}
                className="text-blue-400 text-xs hover:underline self-start sm:self-center"
              >
                {showModelDetail
                  ? t("Hide models", "Bisa ma model")
                  : t("Show individual models", "Wonetsa ma model")}
              </button>
            )}
          </div>

          {showModelDetail && allForecasts.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4 pt-4 border-t border-slate-700/50">
              {allForecasts.map((model, idx) => {
                const lastPred = model.prediction?.[model.prediction.length - 1];
                const up       = lastPred != null && latestRate?.rate != null && lastPred > latestRate.rate;
                return (
                  <div key={idx} className="bg-slate-700/40 p-3 rounded-xl border border-slate-600/50">
                    <p className="text-slate-400 text-xs uppercase">{model.name}</p>
                    <p className="text-white font-bold mt-1">
                      {lastPred != null ? `MWK ${lastPred.toFixed(2)}` : "--"}
                    </p>
                    {lastPred != null && (
                      <p className={`text-xs mt-0.5 ${up ? "text-green-400" : "text-red-400"}`}>
                        {up ? "↗ Up" : "↘ Down"}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── Fan Chart ── */}
      {!loading && !noForecasts && (
        <FanChart forecasts={forecasts} history={history} />
      )}

      {/* ── Sparkline ── */}
      {!loading && forecasts?.dates?.length > 0 && (
        <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-2">
            {t("Forecast Sparkline", "Chithunzi cha Zolosera")}
          </h3>
          <div className="flex gap-2 text-xs text-slate-400 mb-3">
            {[7, 14, 30].map((h) => (
              <span
                key={h}
                onClick={() => setHorizon(h)}
                className={`cursor-pointer px-2 py-1 rounded transition ${
                  horizon === h ? "bg-slate-600 text-white" : "hover:bg-slate-700"
                }`}
              >
                {h}d
              </span>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={100}>
            <LineChart
              data={forecasts.dates.map((d, i) => ({
                date:       d,
                prediction: forecasts.prediction[i],
              }))}
            >
              <Line type="monotone" dataKey="prediction" stroke="#fbbf24" strokeWidth={2} dot={false} />
              <XAxis dataKey="date" hide />
              <YAxis domain={["auto", "auto"]} hide />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", border: "none", borderRadius: "6px", color: "#e2e8f0", fontSize: 12 }}
                formatter={(v) => [`MWK ${Number(v).toFixed(2)}`, "Forecast"]}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Consensus + Interpretation ── */}
      {!loading && !noForecasts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ModelConsensus
            models={allForecasts}
            latestRate={latestRate?.rate}
            horizon={horizon}
          />
          <ModelInterpretation
            forecasts={forecasts}
            language={lang}
            horizon={horizon}
            latestRate={latestRate?.rate}
          />
        </div>
      )}

      {/* ── History + Metrics ── */}
      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              {t("Historical Rate & Forecast", "Mbiri Yakale")}
            </h3>
            <HistoryChart history={history} loading={loading} forecasts={forecasts} />
          </div>
          <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60 backdrop-blur">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">
              {t("Model Accuracy", "Kuyerekeza kwa Model")}
              {loadedModelNames.length > 0 && (
                <span className="ml-2 text-xs text-slate-500 normal-case font-normal">
                  ({loadedModelNames.join(", ")})
                </span>
              )}
            </h3>
            <ModelMetricsTable metrics={metrics} lang={lang} />
          </div>
        </div>
      )}

      {/* ── Disclaimer ── */}
      <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-5 flex gap-4">
        <AlertCircle className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <h3 className="font-semibold text-amber-300 mb-1">
            {t("Important Disclaimer", "Chenjezo Lofunika")}
          </h3>
          <p className="text-amber-200/80 text-sm">
            {t(
              "These forecasts are for informational purposes only and should not be considered financial advice. Exchange rate movements are influenced by many unpredictable factors.",
              "Zolosera izi ndi zongofuna kudziwitsa basi osati uphungu wa ndalama. Kusintha kwa mtengo wa ndalama kumadalira zinthu zambiri zosayembekezereka."
            )}
          </p>
        </div>
      </div>

    </div>
  );
}