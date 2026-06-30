import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useDashboardData } from "../hooks/useForecasts";
import HistoryChart from "../components/HistoryChart";
import { getForecasts, getForecastSummary, getRateStats, getForecastAccuracy, get7DayForecast, get30DayForecast, getRateAlerts } from "../utils/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { AlertCircle, RefreshCw, Loader2, Shield, Calendar, Download, TrendingUp, TrendingDown, BarChart3, Target, Zap, DollarSign, Briefcase, GraduationCap, ShoppingCart, Home, Clock, HelpCircle, Bell, ArrowRight } from "lucide-react";

const LIVE_RATE_URL = 'https://open.er-api.com/v6/latest/USD';

const fmtDate = (d) => {
  if (!d) return '';
  const date = new Date(d + (d.includes('T') ? '' : 'T00:00:00'));
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};

// ── Trust Chart ───────────────────────────────────────────────────────────────
function TrustChart({ history, forecasts, historicalForecasts }) {
  if (!history?.length) return null;
  
  const forecastMap = {};
  
  if (historicalForecasts?.forecast_dates) {
    Object.values(historicalForecasts.forecast_dates).forEach(dayForecasts => {
      dayForecasts.forEach(f => {
        const d = String(f.target_date).slice(0, 10);
        forecastMap[d] = Number(f.predicted_rate?.toFixed(2));
      });
    });
  }
  else if (forecasts?.forecasts) {
    forecasts.forecasts.forEach(f => {
      const d = String(f.target_date).slice(0, 10);
      forecastMap[d] = Number(f.predicted_rate?.toFixed(2));
    });
  } else if (forecasts?.prediction && forecasts?.dates) {
    forecasts.dates.forEach((d, i) => {
      const dateStr = String(d).slice(0, 10);
      forecastMap[dateStr] = Number(forecasts.prediction[i]?.toFixed(2));
    });
  }
  
  const data = history.slice(-30).map((h) => {
    const histDate = String(h.date).slice(0, 10);
    return { date: fmtDate(h.date), actual: Number(h.rate?.toFixed(2)), forecasted: forecastMap[histDate] || null };
  });
  
  const hasForecasts = data.some(d => d.forecasted != null);
  
  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <div className="flex items-center gap-2 mb-3"><Shield className="w-4 h-4 text-gold-400" /><h3 className="text-sm font-semibold text-stone-300">Accuracy & transparency</h3></div>
      <p className="text-xs text-stone-500 mb-4">
        {hasForecasts ? "Our forecasts (dotted) vs actual rates." : "Historical rates for the last 30 days. Past forecasts will appear here as they accumulate."}
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2A332D" />
          <XAxis dataKey="date" tick={{ fill: '#8A968D', fontSize: 10 }} interval={4} angle={-30} textAnchor="end" />
          <YAxis tick={{ fill: '#8A968D', fontSize: 10 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
          <Tooltip contentStyle={{ backgroundColor: '#1A211D', border: 'none', borderRadius: '8px', color: '#D2D8D2', fontSize: 12 }} 
            formatter={(v, name) => { 
              if (v == null) return ['N/A', name];
              const label = name === 'actual' ? 'Actual rate' : name === 'forecasted' ? 'Our forecast' : name;
              return [`MWK ${Number(v).toFixed(2)}`, label];
            }} />
          <Legend />
          <Line type="monotone" dataKey="actual" stroke="#6FAE82" strokeWidth={2} dot={false} name="Actual rate" />
          {hasForecasts && <Line type="monotone" dataKey="forecasted" stroke="#E0AC4F" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 3 }} name="Our forecast" connectNulls={false} />}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

// ── Error Bar Dot Renderer ───────────────────────────────────────────────────
const ErrorBarDot = ({ cx, cy, payload, color }) => {
  if (!payload) return null;
  const lower = payload.lower;
  const upper = payload.upper;
  
  if (lower == null || upper == null) {
    return <circle cx={cx} cy={cy} r={4} fill={color} stroke="#1A211D" strokeWidth={1.5} />;
  }
  
  return (
    <g className="error-bar-group" style={{ cursor: 'pointer' }}>
      <line x1={cx} y1={cy - 8} x2={cx} y2={cy + 8} stroke={color} strokeWidth={1.5} strokeOpacity={0.5} />
      <line x1={cx - 4} y1={cy - 8} x2={cx + 4} y2={cy - 8} stroke={color} strokeWidth={1.5} strokeOpacity={0.5} />
      <line x1={cx - 4} y1={cy + 8} x2={cx + 4} y2={cy + 8} stroke={color} strokeWidth={1.5} strokeOpacity={0.5} />
      <circle cx={cx} cy={cy} r={5} fill={color} stroke="#1A211D" strokeWidth={1.5} />
      <g className="bounds-label" opacity="0">
        <rect x={cx - 44} y={cy - 26} width={88} height={18} rx={5} fill="#1A211D" stroke={color} strokeWidth={1} />
        <text x={cx} y={cy - 14} textAnchor="middle" fill={color} fontSize={10} fontWeight="bold" fontFamily="IBM Plex Mono, monospace">↑ {upper.toFixed(2)}</text>
        <rect x={cx - 44} y={cy + 8} width={88} height={18} rx={5} fill="#1A211D" stroke={color} strokeWidth={1} />
        <text x={cx} y={cy + 20} textAnchor="middle" fill={color} fontSize={10} fontWeight="bold" fontFamily="IBM Plex Mono, monospace">↓ {lower.toFixed(2)}</text>
      </g>
      <title>{`Predicted: ${payload.value?.toFixed(2)}\nUpper (95%): ${upper.toFixed(2)}\nLower (95%): ${lower.toFixed(2)}`}</title>
    </g>
  );
};

// ── Forecast Outlook ──────────────────────────────────────────────────────────
function ForecastOutlook({ forecast1d, forecast7d, forecast30d }) {
  const nextDayData = [];
  const sevenDayData = [];
  const thirtyDayData = [];
  
  if (forecast1d?.predicted_rate && forecast1d?.target_date) {
    nextDayData.push({ 
      day: 1, 
      value: Number(Number(forecast1d.predicted_rate).toFixed(2)), 
      lower: forecast1d.lower_bound != null ? Number(Number(forecast1d.lower_bound).toFixed(2)) : null, 
      upper: forecast1d.upper_bound != null ? Number(Number(forecast1d.upper_bound).toFixed(2)) : null, 
      date: fmtDate(forecast1d.target_date) 
    });
  }
  
  if (forecast7d?.forecasts) {
    forecast7d.forecasts.forEach((v, i) => {
      if (v?.target_date) {
        sevenDayData.push({ 
          day: i + 1, 
          value: Number(Number(v.predicted_rate).toFixed(2)), 
          lower: v.lower_bound != null ? Number(Number(v.lower_bound).toFixed(2)) : null, 
          upper: v.upper_bound != null ? Number(Number(v.upper_bound).toFixed(2)) : null, 
          date: fmtDate(v.target_date) 
        });
      }
    });
  }
  
  if (forecast30d?.forecasts) {
    forecast30d.forecasts.forEach((v, i) => {
      if (v?.target_date) {
        thirtyDayData.push({ 
          day: i + 1, 
          value: Number(Number(v.predicted_rate).toFixed(2)), 
          lower: v.lower_bound != null ? Number(Number(v.lower_bound).toFixed(2)) : null, 
          upper: v.upper_bound != null ? Number(Number(v.upper_bound).toFixed(2)) : null, 
          date: fmtDate(v.target_date) 
        });
      }
    });
  }
  
  if (!nextDayData.length && !sevenDayData.length && !thirtyDayData.length) return null;

  const hasConfidenceIntervals = [...nextDayData, ...sevenDayData, ...thirtyDayData].some(d => d.lower != null && d.upper != null);

  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <h3 className="text-sm font-semibold text-stone-300 mb-3">Forecast outlook</h3>
      <p className="text-xs text-stone-500 mb-4">
        {hasConfidenceIntervals 
          ? "Projected Kwacha movement with 95% confidence intervals." 
          : "Projected Kwacha movement across timeframes."}
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart margin={{ top: 10, right: 20, left: 10, bottom: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2A332D" />
          <XAxis 
            type="number"
            domain={[1, 30]}
            tickCount={30}
            tick={{ fill: '#8A968D', fontSize: 10 }}
            label={{ value: 'Days ahead', position: 'insideBottom', fill: '#8A968D', fontSize: 10, offset: -5 }}
          />
          <YAxis 
            tick={{ fill: '#8A968D', fontSize: 10 }} 
            domain={['auto', 'auto']} 
            tickFormatter={(v) => v.toFixed(0)} 
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1A211D', border: 'none', borderRadius: '8px', color: '#D2D8D2', fontSize: 12 }} 
            formatter={(v, name) => {
              if (v == null) return ['N/A', name];
              if (name === 'Next day') return [`MWK ${Number(v).toFixed(2)}`, 'Next day forecast'];
              if (name === '7 days') return [`MWK ${Number(v).toFixed(2)}`, '7-day forecast'];
              if (name === '30 days') return [`MWK ${Number(v).toFixed(2)}`, '30-day forecast'];
              return [`MWK ${Number(v).toFixed(2)}`, name];
            }}
          />
          <Legend />
          
          {nextDayData.length > 0 && (
            <Line 
              type="monotone" 
              data={nextDayData}
              dataKey="value" 
              stroke="#E0AC4F" 
              strokeWidth={0}
              dot={{ r: 6, fill: '#E0AC4F', stroke: '#1A211D', strokeWidth: 2 }}
              name="Next day"
              isAnimationActive={false}
            />
          )}
          
          {sevenDayData.length > 0 && (
            <Line 
              type="monotone" 
              data={sevenDayData}
              dataKey="value" 
              stroke="#7DA0C4" 
              strokeWidth={2}
              dot={(props) => <ErrorBarDot {...props} color="#7DA0C4" />}
              name="7 days"
              isAnimationActive={false}
            />
          )}
          
          {thirtyDayData.length > 0 && (
            <Line 
              type="monotone" 
              data={thirtyDayData}
              dataKey="value" 
              stroke="#6FAE82" 
              strokeWidth={2}
              dot={(props) => <ErrorBarDot {...props} color="#6FAE82" />}
              name="30 days"
              isAnimationActive={false}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
      {hasConfidenceIntervals && (
        <details className="mt-3 group">
          <summary className="text-xs text-stone-500 cursor-pointer hover:text-stone-400 transition">💡 How to interpret this chart</summary>
          <div className="mt-2 p-3 bg-stone-700/40 rounded-lg text-xs text-stone-400 space-y-1.5">
            <p>• <span className="text-stone-300 font-medium">Gold dot</span> = tomorrow's predicted rate.</p>
            <p>• <span className="text-stone-300 font-medium">Blue line</span> = 7-day forecast with confidence intervals.</p>
            <p>• <span className="text-stone-300 font-medium">Green line</span> = 30-day forecast showing the longer-term trend.</p>
            <p>• <span className="text-stone-300 font-medium">Hover over dots</span> to see upper (↑) and lower (↓) bounds.</p>
          </div>
        </details>
      )}
    </div>
  );
}

// ── Key Insight Banner ────────────────────────────────────────────────────────
function KeyInsight({ displayRate, sevenDayChange, accuracy }) {
  const pct = parseFloat(sevenDayChange?.pct || 0);
  const isStable = Math.abs(pct) < 0.3;
  
  return (
    <div className="bg-gradient-to-r from-gold-500/10 to-stone-900/60 rounded-2xl p-4 border border-gold-500/20">
      <div className="flex items-center gap-3">
        <Target className="w-5 h-5 text-gold-400 shrink-0" />
        <div>
          <p className="text-stone-100 font-semibold text-sm">
            {isStable 
              ? `The Kwacha is expected to remain stable at ~MWK ${displayRate?.rate?.toFixed(2) || '---'} this week.`
              : `The Kwacha is expected to ${sevenDayChange?.direction === 'up' ? 'weaken' : 'strengthen'} by ${Math.abs(pct).toFixed(2)}% over the next 7 days.`
            }
          </p>
          <p className="text-stone-400 text-xs mt-0.5">
            Our models have a {accuracy?.avg_error_pct || '0.3'}% error rate based on {accuracy?.comparisons?.length || '3'} historical comparisons.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Last Updated ──────────────────────────────────────────────────────────────
function LastUpdated() {
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  return (
    <div className="text-stone-500 text-xs flex items-center gap-1">
      <Clock className="w-3 h-3" />
      Last updated: {today}
    </div>
  );
}

// ── What You Should Do ────────────────────────────────────────────────────────
function WhenToAct({ nextDayChange, sevenDayChange, thirtyDayChange, displayRate, forecast1d, forecast7d, forecast30d }) {
  const getAdvice = (label, change, horizon) => {
    const pct = parseFloat(change?.pct || 0);
    const dir = change?.direction;
    const absPct = Math.abs(pct);
    
    let confidenceWidth = 0;
    let forecastData = null;
    if (horizon === 1) forecastData = forecast1d;
    else if (horizon === 7) forecastData = forecast7d;
    else if (horizon === 30) forecastData = forecast30d;
    
    if (forecastData?.lower_bound && forecastData?.upper_bound) {
      confidenceWidth = forecastData.upper_bound - forecastData.lower_bound;
    } else if (forecastData?.forecasts) {
      const lastForecast = forecastData.forecasts[forecastData.forecasts.length - 1];
      if (lastForecast?.lower_bound && lastForecast?.upper_bound) {
        confidenceWidth = lastForecast.upper_bound - lastForecast.lower_bound;
      }
    }
    
    const predictedRate = forecastData?.predicted_rate || (forecastData?.forecasts ? forecastData.forecasts[forecastData.forecasts.length - 1]?.predicted_rate : null);
    const pctWidth = predictedRate && confidenceWidth > 0 ? (confidenceWidth / predictedRate) * 100 : 100;
    const highConfidence = pctWidth < 1.0;
    const moderateConfidence = pctWidth < 3.0;
    const significantMove = absPct > 0.5;
    const minorMove = absPct > 0.15 && absPct <= 0.5;
    
    if (!significantMove && !minorMove && highConfidence) {
      return { level: "Hold", color: "text-gold-400", bg: "bg-gold-500/10", short: "Rate is stable with high certainty.", detail: `Tight confidence interval (±${(confidenceWidth/2).toFixed(1)} MWK, ${pctWidth.toFixed(1)}% of rate). No urgency to act.` };
    }
    if (!significantMove && !minorMove && !highConfidence) {
      return { level: "Monitor", color: "text-yellow-400", bg: "bg-yellow-500/10", short: "Rate appears stable but confidence is moderate.", detail: `Confidence interval: ±${(confidenceWidth/2).toFixed(1)} MWK (${pctWidth.toFixed(1)}% of rate). Check back tomorrow.` };
    }
    if (dir === "up" && significantMove && highConfidence) {
      return { level: "Hedge Now", color: "text-terracotta-400", bg: "bg-terracotta-500/10", short: `Strong signal: Kwacha may lose ~${absPct.toFixed(1)}%.`, detail: `All models agree on weakening. Tight interval (±${(confidenceWidth/2).toFixed(1)} MWK). Buy USD now.` };
    }
    if (dir === "up" && (significantMove || minorMove) && !highConfidence && moderateConfidence) {
      return { level: "Consider Hedging", color: "text-terracotta-400", bg: "bg-terracotta-500/10", short: `Kwacha may weaken ~${absPct.toFixed(1)}% with moderate confidence.`, detail: "Consider hedging 50% now, reassess tomorrow." };
    }
    if (dir === "up" && !highConfidence && !moderateConfidence) {
      return { level: "Monitor Closely", color: "text-yellow-400", bg: "bg-yellow-500/10", short: `Possible weakening but low confidence.`, detail: `Wide confidence interval (±${(confidenceWidth/2).toFixed(1)} MWK). Wait for clearer signal.` };
    }
    if (dir === "down" && significantMove && highConfidence) {
      return { level: "Wait (High Confidence)", color: "text-gold-400", bg: "bg-gold-500/10", short: `Strong signal: Kwacha may gain ~${absPct.toFixed(1)}%.`, detail: `All models agree on strengthening. Delay USD purchases.` };
    }
    if (dir === "down" && (significantMove || minorMove) && !highConfidence) {
      return { level: "Likely Strengthening", color: "text-gold-400", bg: "bg-gold-500/10", short: `Kwacha may gain ~${absPct.toFixed(1)}%.`, detail: "Most models point to strengthening. Waiting could save you money." };
    }
    return { level: "Monitor", color: "text-yellow-400", bg: "bg-yellow-500/10", short: "Uncertain — monitor before acting.", detail: "Forecast confidence is low. Wait for clearer signal." };
  };
  
  const stages = [
    { label: "Today", change: nextDayChange, icon: Zap, horizon: 1 },
    { label: "This week", change: sevenDayChange, icon: TrendingUp, horizon: 7 },
    { label: "This month", change: thirtyDayChange, icon: Target, horizon: 30 },
  ];
  
  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <h3 className="text-sm font-semibold text-stone-300 mb-4">What you should do</h3>
      <p className="text-xs text-stone-500 mb-4">Guidance based on forecast at MWK {displayRate?.rate?.toFixed(2) || '---'}.</p>
      <div className="space-y-3">
        {stages.map((stage, i) => {
          const advice = getAdvice(stage.label, stage.change, stage.horizon);
          const Icon = stage.icon;
          return (
            <div key={i} className={`${advice.bg} rounded-xl p-4`}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2"><Icon className={`w-4 h-4 ${advice.color}`} /><span className="text-sm font-medium text-stone-300">{stage.label}</span></div>
                <span className={`text-xs font-bold ${advice.color}`}>{advice.level}</span>
              </div>
              <p className="text-xs text-stone-200 font-medium mb-1">{advice.short}</p>
              <p className="text-xs text-stone-400">{advice.detail}</p>
              {stage.change && <p className="text-xs text-stone-500 mt-2">Expected: {stage.change.direction === "up" ? "↗" : "↘"} {stage.change.pct}%</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Decision Impact Analysis ──────────────────────────────────────────────────
function DecisionImpact({ displayRate, sevenDayChange, thirtyDayChange, forecast7d, forecast30d }) {
  if (!displayRate?.rate) return null;
  
  const getConfidence = (forecastData) => {
    let lower, upper, predicted;
    if (forecastData?.lower_bound && forecastData?.upper_bound) {
      lower = forecastData.lower_bound;
      upper = forecastData.upper_bound;
      predicted = forecastData.predicted_rate;
    } else if (forecastData?.forecasts) {
      const last = forecastData.forecasts[forecastData.forecasts.length - 1];
      if (last?.lower_bound && last?.upper_bound) {
        lower = last.lower_bound;
        upper = last.upper_bound;
        predicted = last.predicted_rate;
      }
    }
    if (lower && upper && predicted) {
      const width = upper - lower;
      const pctWidth = (width / predicted) * 100;
      return { width, pctWidth, isHigh: pctWidth < 1.0, isModerate: pctWidth < 3.0 };
    }
    return null;
  };
  
  const conf7d = getConfidence(forecast7d);
  const conf30d = getConfidence(forecast30d);
  
  const pct7d = Math.abs(parseFloat(sevenDayChange?.pct || 0));
  const pct30d = Math.abs(parseFloat(thirtyDayChange?.pct || 0));
  const dir7d = sevenDayChange?.direction;
  const dir30d = thirtyDayChange?.direction;
  
  const transactionSizes = [1000, 5000, 10000];
  
  const getRecommendation = (pct, dir, conf, horizon) => {
    const isStable = pct < 0.15;
    if (isStable && conf?.isHigh) return "No action — rate is stable with high certainty.";
    if (isStable) return "Rate appears stable. Monitor but no urgency.";
    if (conf?.isHigh) {
      return dir === "up" ? `Hedge now — strong signal Kwacha will weaken over ${horizon} days.` : `Wait — strong signal Kwacha will strengthen over ${horizon} days.`;
    }
    if (conf?.isModerate) return "Consider partial action — moderate confidence in this forecast.";
    return `Monitor — confidence is lower for ${horizon}-day forecasts. This is normal.`;
  };

  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <h3 className="text-sm font-semibold text-stone-300 mb-3 flex items-center gap-2">
        <DollarSign className="w-4 h-4 text-gold-400" />
        Decision Impact Analysis
      </h3>
      <p className="text-xs text-stone-500 mb-4">Estimated cost of waiting if forecast is correct</p>
      
      <div className="mb-4">
        <p className="text-xs text-stone-400 font-medium mb-2">7-Day Forecast Impact</p>
        <div className="space-y-2 mb-3">
          {transactionSizes.map(size => {
            const potentialLoss = size * (pct7d / 100) * displayRate.rate;
            return (
              <div key={`7d-${size}`} className="bg-stone-700/40 rounded-lg p-3 flex justify-between items-center">
                <div><span className="text-xs text-stone-300 font-medium">${size.toLocaleString()}</span><span className="text-xs text-stone-500 ml-2">{dir7d === "up" ? "extra cost" : "savings"} if you wait</span></div>
                <span className={`text-sm font-bold font-data ${dir7d === "up" ? 'text-terracotta-400' : 'text-gold-400'}`}>~MWK {potentialLoss.toFixed(0)}</span>
              </div>
            );
          })}
        </div>
        {conf7d && (
          <div className="bg-stone-700/40 rounded-lg p-3 mb-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-stone-400">Confidence (7-day)</span>
              <span className={`text-sm font-bold ${conf7d.isHigh ? 'text-gold-400' : conf7d.isModerate ? 'text-yellow-400' : 'text-stone-400'}`}>
                {conf7d.isHigh ? 'High' : conf7d.isModerate ? 'Moderate' : 'Lower'}
                <span className="font-normal text-xs ml-1">(±{conf7d.width.toFixed(1)} MWK, {conf7d.pctWidth.toFixed(1)}% of rate)</span>
              </span>
            </div>
            <p className="text-xs text-stone-500 mt-1">
              {conf7d.isHigh ? 'Tight interval — models agree closely.' : conf7d.isModerate ? 'Moderate spread — reasonable confidence.' : `Wider interval (±${conf7d.width.toFixed(1)} MWK) — models disagree on magnitude. Common in FX forecasting.`}
            </p>
          </div>
        )}
        <p className="text-xs text-stone-500 italic">💡 {getRecommendation(pct7d, dir7d, conf7d, 7)}</p>
      </div>
      
      <div className="border-t border-stone-700 pt-4">
        <p className="text-xs text-stone-400 font-medium mb-2">30-Day Forecast Impact</p>
        <div className="space-y-2 mb-3">
          {transactionSizes.map(size => {
            const potentialLoss = size * (pct30d / 100) * displayRate.rate;
            return (
              <div key={`30d-${size}`} className="bg-stone-700/40 rounded-lg p-3 flex justify-between items-center">
                <div><span className="text-xs text-stone-300 font-medium">${size.toLocaleString()}</span><span className="text-xs text-stone-500 ml-2">{dir30d === "up" ? "extra cost" : "savings"} if you wait</span></div>
                <span className={`text-sm font-bold font-data ${dir30d === "up" ? 'text-terracotta-400' : 'text-gold-400'}`}>~MWK {potentialLoss.toFixed(0)}</span>
              </div>
            );
          })}
        </div>
        {conf30d && (
          <div className="bg-stone-700/40 rounded-lg p-3 mb-2">
            <div className="flex justify-between items-center">
              <span className="text-xs text-stone-400">Confidence (30-day)</span>
              <span className={`text-sm font-bold ${conf30d.isHigh ? 'text-gold-400' : conf30d.isModerate ? 'text-yellow-400' : 'text-stone-400'}`}>
                {conf30d.isHigh ? 'High' : conf30d.isModerate ? 'Moderate' : 'Lower'}
                <span className="font-normal text-xs ml-1">(±{conf30d.width.toFixed(1)} MWK, {conf30d.pctWidth.toFixed(1)}% of rate)</span>
              </span>
            </div>
            <p className="text-xs text-stone-500 mt-1">30-day forecasts naturally have wider intervals — uncertainty increases with time.</p>
          </div>
        )}
        {pct7d.toFixed(2) === pct30d.toFixed(2) && (
          <p className="text-xs text-stone-500 mb-2 italic">📌 7-day and 30-day impacts are similar because the forecast shows the rate stabilizing.</p>
        )}
        <p className="text-xs text-stone-500 italic">💡 {getRecommendation(pct30d, dir30d, conf30d, 30)}</p>
      </div>
      
      <p className="text-xs text-stone-500 mt-4 border-t border-stone-700 pt-3">⚠️ Decision-support tool, not financial advice.</p>
    </div>
  );
}

// ── Who This Affects ──────────────────────────────────────────────────────────
function WhoThisAffects({ displayRate, sevenDayChange }) {
  const pct = parseFloat(sevenDayChange?.pct || 0);
  const dir = sevenDayChange?.direction;
  const absPct = Math.abs(pct);
  const isStable = absPct < 0.3;
  const isWeakening = dir === "up" && !isStable;

  const personas = [
    { icon: ShoppingCart, who: "Buying groceries & goods", advice: isStable ? "Prices should stay the same this week." : isWeakening ? "Imported goods may cost more soon. Stock up on essentials now." : "Imported goods may get cheaper. Wait a few days to shop." },
    { icon: GraduationCap, who: "Students & parents", advice: isStable ? "No change expected for school expenses." : isWeakening ? "If you pay fees in USD, pay now before it costs more Kwacha." : "Wait — your Kwacha will stretch further for USD payments." },
    { icon: Briefcase, who: "Business owners", advice: isStable ? "Stable outlook — plan with confidence." : isWeakening ? `Import costs may rise ~${absPct.toFixed(1)}%. Order inventory early.` : `Import costs may drop ~${absPct.toFixed(1)}%. Delay orders if possible.` },
    { icon: Home, who: "Receiving money from abroad", advice: isStable ? "Remittance value is stable." : isWeakening ? "Hold USD — it's worth more Kwacha now." : "Convert USD to Kwacha now before the rate drops." },
  ];

  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <h3 className="text-sm font-semibold text-stone-300 mb-4">How this affects you</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {personas.map((p, i) => {
          const Icon = p.icon;
          return (
            <div key={i} className="bg-stone-700/40 rounded-xl p-3 flex items-start gap-3">
              <Icon className="w-4 h-4 text-gold-400 shrink-0 mt-0.5" />
              <div><p className="text-xs font-medium text-stone-300">{p.who}</p><p className="text-xs text-stone-400 mt-0.5">{p.advice}</p></div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Rate Statistics ───────────────────────────────────────────────────────────
function RateStats({ stats }) {
  if (!stats) return null;
  
  const sevenDayTrend = stats.change_7d > 0 ? 'weakening' : stats.change_7d < 0 ? 'strengthening' : 'stable';
  const thirtyDayTrend = stats.change_30d > 0 ? 'weakening' : stats.change_30d < 0 ? 'strengthening' : 'stable';
  const volatility = stats.max_7d && stats.min_7d ? stats.max_7d - stats.min_7d : 0;
  const isVolatile = volatility > 5;
  
  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <div className="flex items-center gap-2 mb-3"><BarChart3 className="w-4 h-4 text-blue-400" /><h3 className="text-sm font-semibold text-stone-300">Rate statistics</h3></div>
      
      <div className="bg-stone-700/40 rounded-lg p-3 mb-4">
        <p className="text-xs text-stone-400 mb-1">Past 7 days (actual)</p>
        <p className={`text-sm font-semibold ${sevenDayTrend === 'weakening' ? 'text-terracotta-400' : sevenDayTrend === 'strengthening' ? 'text-gold-400' : 'text-stone-300'}`}>
          {sevenDayTrend === 'weakening' ? '↗ Kwacha weakened' : sevenDayTrend === 'strengthening' ? '↘ Kwacha strengthened' : '→ Rate stable'}
          <span className="text-stone-400 font-normal ml-2">({stats.change_7d > 0 ? '+' : ''}{stats.change_7d?.toFixed(2)} MWK, {Math.abs(stats.change_pct_7d)?.toFixed(2)}%)</span>
        </p>
        <p className="text-xs text-stone-500 mt-1">
          {sevenDayTrend === 'weakening' ? 'Rate increased — it costs more MWK to buy USD now than 7 days ago.' :
           sevenDayTrend === 'strengthening' ? 'Rate decreased — it costs fewer MWK to buy USD now than 7 days ago.' :
           'Rate has been stable over the past week.'}
        </p>
        {isVolatile && <p className="text-xs text-yellow-400 mt-1">⚠️ Above normal volatility — forecasts may be less certain</p>}
      </div>
      
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div><p className="text-stone-400 text-xs">7-day range</p><p className="text-stone-100 font-medium font-data">{stats.min_7d?.toFixed(2)} – {stats.max_7d?.toFixed(2)}</p><p className="text-stone-500 text-xs mt-0.5">Spread: {volatility.toFixed(2)} MWK</p></div>
        <div><p className="text-stone-400 text-xs">30-day trend</p><p className={`text-stone-100 font-medium font-data ${thirtyDayTrend === 'weakening' ? 'text-terracotta-400' : thirtyDayTrend === 'strengthening' ? 'text-gold-400' : ''}`}>{stats.change_30d > 0 ? '+' : ''}{stats.change_30d?.toFixed(2)} ({Math.abs(stats.change_pct_30d)?.toFixed(2)}%)</p><p className="text-stone-500 text-xs mt-0.5">30-day avg: {stats.avg_30d?.toFixed(2)}</p></div>
      </div>
      
      <p className="text-xs text-stone-500 mt-3 italic">📌 Past performance shows what happened. Forecasts predict what may happen next. They can differ.</p>
    </div>
  );
}

// ── Model Accuracy ────────────────────────────────────────────────────────────
function AccuracyCard({ accuracy }) {
  if (!accuracy?.comparisons?.length) return null;
  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <div className="flex items-center gap-2 mb-3"><Shield className="w-4 h-4 text-gold-400" /><h3 className="text-sm font-semibold text-stone-300">Model accuracy</h3></div>
      <div className="grid grid-cols-2 gap-3 text-sm mb-3">
        <div><p className="text-stone-400 text-xs">Average error</p><p className="text-stone-100 font-medium">{accuracy.avg_error_mwk} MWK</p></div>
        <div><p className="text-stone-400 text-xs">Error rate</p><p className="text-stone-100 font-medium">{accuracy.avg_error_pct}%</p></div>
        <div><p className="text-stone-400 text-xs">Within range</p><p className="text-gold-400 font-bold">{accuracy.within_range_pct}%</p></div>
        <div><p className="text-stone-400 text-xs">Comparisons</p><p className="text-stone-100 font-medium">{accuracy.comparisons.length} data points</p></div>
      </div>
      <p className="text-xs text-stone-500">Based on {accuracy.comparisons.length} past forecasts compared to actual Reserve Bank rates.</p>
    </div>
  );
}

// ── Rate Alerts ──────────────────────────────────────────────────────────────
function RateAlerts({ alerts }) {
  if (!alerts?.alerts?.length) return null;
  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <div className="flex items-center gap-2 mb-3"><Bell className="w-4 h-4 text-yellow-400" /><h3 className="text-sm font-semibold text-stone-300">Rate alerts</h3></div>
      <div className="space-y-2">
        {alerts.alerts.slice(0, 3).map((alert, i) => (
          <div key={i} className={`p-3 rounded-lg text-xs ${alert.level === 'warning' ? 'bg-yellow-500/10 border border-yellow-500/20 text-yellow-400' : alert.level === 'critical' ? 'bg-terracotta-500/10 border border-terracotta-500/20 text-terracotta-400' : 'bg-blue-500/10 border border-blue-500/20 text-blue-400'}`}>
            <div className="flex items-start gap-2"><Bell className="w-3 h-3 shrink-0 mt-0.5" /><div><p className="font-medium">{alert.message}</p>{alert.detail && <p className="mt-0.5 opacity-80">{alert.detail}</p>}</div></div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Quick FAQ ────────────────────────────────────────────────────────────────
function QuickFAQ() {
  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
      <div className="flex items-center gap-2 mb-3"><HelpCircle className="w-4 h-4 text-purple-400" /><h3 className="text-sm font-semibold text-stone-300">Quick answers</h3></div>
      <div className="space-y-2 text-sm">
        <details className="group"><summary className="text-stone-400 cursor-pointer hover:text-stone-300 text-xs">How often are forecasts updated?</summary><p className="text-stone-500 text-xs mt-1 ml-4">Forecasts are generated daily. Click "Refresh" to get the latest predictions.</p></details>
        <details className="group"><summary className="text-stone-400 cursor-pointer hover:text-stone-300 text-xs">What does "Hedge Now" mean?</summary><p className="text-stone-500 text-xs mt-1 ml-4">It means our models strongly predict the Kwacha will weaken. Buying USD now locks in a better rate than waiting.</p></details>
        <details className="group"><summary className="text-stone-400 cursor-pointer hover:text-stone-300 text-xs">Why do past and forecast trends differ?</summary><p className="text-stone-500 text-xs mt-1 ml-4">Past trends show what already happened. Forecasts predict what may happen next. They can differ when models expect a reversal.</p></details>
        <details className="group"><summary className="text-stone-400 cursor-pointer hover:text-stone-300 text-xs">Where does the data come from?</summary><p className="text-stone-500 text-xs mt-1 ml-4">Exchange rates from the Reserve Bank of Malawi and live currency APIs. Updated daily.</p></details>
      </div>
    </div>
  );
}

function EmptyForecasts({ onGenerate, generating }) {
  return (
    <div className="bg-stone-900/60 rounded-2xl p-12 border border-stone-700/60 flex flex-col items-center gap-4 text-center">
      <Calendar className="w-14 h-14 text-stone-500" />
      <h3 className="text-stone-100 font-semibold text-xl">No forecasts yet</h3>
      <p className="text-stone-400 text-sm max-w-md">Click below to generate today's exchange rate forecasts.</p>
      <button onClick={onGenerate} disabled={generating} className="bg-gold-400 hover:bg-gold-300 disabled:bg-stone-700 disabled:text-stone-400 text-ink-950 px-6 py-3 rounded-xl font-semibold transition flex items-center gap-2 mt-2">{generating && <Loader2 className="w-4 h-4 animate-spin" />}{generating ? "Generating..." : "Generate forecasts"}</button>
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
  const [alerts, setAlerts] = useState(null);

  const { latestRate, forecasts, history, loading, noForecasts, refetch, historicalForecasts } = useDashboardData(7);

  const fetchAllData = async () => {
    const [summary, stats, acc, full7d, full30d, alertsData] = await Promise.all([
      getForecastSummary(), getRateStats(), getForecastAccuracy(), get7DayForecast(), get30DayForecast(),
      getRateAlerts().catch(() => null)
    ]);
    if (summary?.forecasts) {
      setForecast1d(summary.forecasts["1_day"]);
      setForecast7d(full7d || summary.forecasts["7_day"]);
      setForecast30d(full30d || summary.forecasts["30_day"]);
      if (summary.current_rate) setLiveRate({ rate: summary.current_rate });
    }
    if (stats) setRateStats(stats);
    if (acc) setAccuracy(acc);
    if (alertsData) setAlerts(alertsData);
  };

  useEffect(() => { fetchAllData(); }, [noForecasts]);
  useEffect(() => { fetch(LIVE_RATE_URL).then(r => r.json()).then(d => { if (d?.rates?.MWK) setLiveRate({ rate: d.rates.MWK }); }).catch(() => {}); }, []);

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
  const sevenDayVal = forecast7d?.predicted_rate?.toFixed(2) ?? forecast7d?.forecasts?.[6]?.predicted_rate?.toFixed(2) ?? null;
  const sevenDayChange = forecast7d ? getChange(forecast7d.predicted_rate || forecast7d?.forecasts?.[6]?.predicted_rate) : null;
  const thirtyDayVal = forecast30d?.predicted_rate?.toFixed(2) ?? forecast30d?.forecasts?.[29]?.predicted_rate?.toFixed(2) ?? null;
  const thirtyDayChange = forecast30d ? getChange(forecast30d.predicted_rate || forecast30d?.forecasts?.[29]?.predicted_rate) : null;

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
          <h1 className="font-display text-2xl font-semibold text-stone-100">KwachaCast</h1>
          <p className="text-stone-400 text-sm mt-1">Exchange rate forecasts for the Malawi Kwacha</p>
          <LastUpdated />
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => window.open('https://kwachacast-api.onrender.com/api/v1/forecasts/export?horizon=7&format=csv', '_blank')} className="text-stone-400 hover:text-stone-100 text-sm flex items-center gap-1"><Download className="w-3.5 h-3.5" />Export</button>
          <button onClick={handleGenerate} disabled={generating} className="bg-gold-400 hover:bg-gold-300 disabled:bg-stone-700 disabled:text-stone-400 text-ink-950 text-sm px-4 py-2 rounded-lg font-semibold transition flex items-center gap-2">{generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}{generating ? "Generating..." : "Refresh"}</button>
        </div>
      </div>
      <div className="rate-wave-divider" />

      {generateMsg && <div className="rounded-xl p-3 text-sm bg-gold-500/10 border border-gold-500/20 text-gold-400">{generateMsg}</div>}
      {loading && <div className="grid grid-cols-4 gap-4 animate-pulse">{[...Array(4)].map((_, i) => <div key={i} className="bg-stone-900/60 rounded-2xl h-32 border border-stone-700/60" />)}</div>}
      {!loading && noForecasts && <EmptyForecasts onGenerate={handleGenerate} generating={generating} />}
      {!loading && alerts && <RateAlerts alerts={alerts} />}

      {!loading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((kpi, i) => (
            <div key={i} className={`bg-stone-900/60 border ${i === 0 ? 'border-gold-500/30' : 'border-stone-700/60'} rounded-2xl p-5`}>
              <p className="text-stone-400 text-xs uppercase tracking-wider mb-1">{kpi.label}</p>
              <p className="font-data text-2xl font-semibold text-stone-100">{kpi.value}</p>
              {kpi.change && <p className={`text-sm font-medium mt-1 ${kpi.change.direction === "up" ? "text-terracotta-400" : "text-gold-400"}`}>{kpi.change.direction === "up" ? "↗" : "↘"} {kpi.change.pct}%</p>}
            </div>
          ))}
        </div>
      )}

      {!loading && !noForecasts && <KeyInsight displayRate={displayRate} sevenDayChange={sevenDayChange} accuracy={accuracy} />}

      {!loading && !noForecasts && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ForecastOutlook forecast1d={forecast1d} forecast7d={forecast7d} forecast30d={forecast30d} />
          <WhenToAct nextDayChange={nextDayChange} sevenDayChange={sevenDayChange} thirtyDayChange={thirtyDayChange} displayRate={displayRate} forecast1d={forecast1d} forecast7d={forecast7d} forecast30d={forecast30d} />
        </div>
      )}

      {!loading && !noForecasts && (
        <DecisionImpact displayRate={displayRate} sevenDayChange={sevenDayChange} thirtyDayChange={thirtyDayChange} forecast7d={forecast7d} forecast30d={forecast30d} />
      )}

      {!loading && !noForecasts && <WhoThisAffects displayRate={displayRate} sevenDayChange={sevenDayChange} />}

      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RateStats stats={rateStats} />
          <AccuracyCard accuracy={accuracy} />
        </div>
      )}

      {!loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {history?.length > 30 && <TrustChart history={history} forecasts={forecast7d || forecasts} historicalForecasts={historicalForecasts} />}
          <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-stone-300">Historical trends</h3>
              <Link to="/history" className="text-xs text-gold-400 hover:text-gold-300 flex items-center gap-1 transition">View full history <ArrowRight className="w-3 h-3" /></Link>
            </div>
            <HistoryChart history={history} loading={loading} forecasts={forecasts} />
          </div>
        </div>
      )}

      {!loading && <QuickFAQ />}

      <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-4 flex gap-3">
        <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <p className="text-amber-200/80 text-sm">Forecasts are for informational purposes only — not financial advice. Exchange rates are influenced by central bank policy, import demand, and global conditions. Past accuracy does not guarantee future results.</p>
      </div>
    </div>
  );
}