import React, { useState } from "react";
import { fetchHistory } from "../utils/api";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ComposedChart,
  Line,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import { Calendar, TrendingUp, Database, Clock, Activity, ArrowUp, ArrowDown, BarChart3, Info } from "lucide-react";

function StatCard({ title, value, icon: Icon, subtitle }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 backdrop-blur">
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className="w-4 h-4 text-emerald-400" />}
        <p className="text-xs text-slate-400 uppercase tracking-wider">{title}</p>
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
      {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

export default function History() {
  const [start, setStart] = useState("2023-01-01");
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState("1y");
  const [error, setError] = useState(null);
  const [showVolatility, setShowVolatility] = useState(false);

  const fetch = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchHistory(start, end);
      setData(res);
    } catch (e) {
      setError("Failed to load history. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickRange = (range) => {
    setTimeRange(range);
    const today = new Date();
    let from = new Date();
    switch (range) {
      case "1m": from.setMonth(today.getMonth() - 1); break;
      case "3m": from.setMonth(today.getMonth() - 3); break;
      case "6m": from.setMonth(today.getMonth() - 6); break;
      case "1y": from.setFullYear(today.getFullYear() - 1); break;
      case "5y": from.setFullYear(today.getFullYear() - 5); break;
      case "all": from = new Date("2012-01-01"); break;
      default: break;
    }
    setStart(from.toISOString().slice(0, 10));
    setEnd(today.toISOString().slice(0, 10));
  };

  React.useEffect(() => { fetch(); }, []);

  // Calculate statistics from the data
  const calculateStats = (rateData) => {
    if (!rateData || rateData.length === 0) return null;
    
    const rates = rateData.map(d => d.rate);
    const dates = rateData.map(d => d.date);
    
    const avg = rates.reduce((a, b) => a + b, 0) / rates.length;
    const min = Math.min(...rates);
    const max = Math.max(...rates);
    const latest = rates[rates.length - 1];
    const oldest = rates[0];
    const change = latest - oldest;
    const changePct = ((change / oldest) * 100);
    
    // Calculate volatility (standard deviation)
    const variance = rates.reduce((sum, r) => sum + Math.pow(r - avg, 2), 0) / rates.length;
    const stdDev = Math.sqrt(variance);
    
    // Calculate daily changes
    const dailyChanges = [];
    for (let i = 1; i < rates.length; i++) {
      dailyChanges.push(rates[i] - rates[i-1]);
    }
    const avgDailyChange = dailyChanges.reduce((a, b) => a + b, 0) / dailyChanges.length;
    const maxDailyIncrease = Math.max(...dailyChanges);
    const maxDailyDecrease = Math.min(...dailyChanges);
    
    return {
      avg: avg.toFixed(2),
      min: min.toFixed(2),
      max: max.toFixed(2),
      latest: latest.toFixed(2),
      oldest: oldest.toFixed(2),
      change: change.toFixed(2),
      changePct: changePct.toFixed(2),
      stdDev: stdDev.toFixed(2),
      avgDailyChange: avgDailyChange.toFixed(4),
      maxDailyIncrease: maxDailyIncrease.toFixed(2),
      maxDailyDecrease: maxDailyDecrease.toFixed(2),
      startDate: dates[0],
      endDate: dates[dates.length - 1],
    };
  };

  // Prepare volatility data
  const prepareVolatilityData = (rateData) => {
    if (!rateData || rateData.length < 2) return [];
    
    const volatilityData = [];
    for (let i = 1; i < rateData.length; i++) {
      const change = rateData[i].rate - rateData[i-1].rate;
      volatilityData.push({
        date: rateData[i].date,
        change: Number(change.toFixed(2)),
        absChange: Math.abs(Number(change.toFixed(2))),
      });
    }
    return volatilityData;
  };

  const stats = data?.data ? calculateStats(data.data) : null;
  const volatilityData = data?.data ? prepareVolatilityData(data.data) : null;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white">Exchange rate history</h1>
        <p className="text-slate-400 text-sm mt-1">Historical MWK/USD rates from 2013 to present</p>
      </div>

      {/* Quick select */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 flex items-center gap-4 flex-wrap backdrop-blur">
        <div className="flex items-center gap-2 text-slate-300">
          <Calendar size={18} />
          <span className="font-medium text-sm">Time range:</span>
        </div>
        <div className="flex gap-2 flex-wrap">
          {["1m", "3m", "6m", "1y", "5y", "all"].map((range) => (
            <button
              key={range}
              onClick={() => handleQuickRange(range)}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors ${
                timeRange === range
                  ? "bg-emerald-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              {range === "all" ? "All time" : range.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Manual date inputs */}
      <div className="flex gap-3 items-end flex-wrap">
        <div>
          <label className="text-slate-400 text-xs block mb-1">Start date</label>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600" />
        </div>
        <div>
          <label className="text-slate-400 text-xs block mb-1">End date</label>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600" />
        </div>
        <button onClick={fetch} disabled={loading}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
          {loading ? "Loading..." : "Load"}
        </button>
        {stats && (
          <button 
            onClick={() => setShowVolatility(!showVolatility)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              showVolatility 
                ? "bg-purple-600 hover:bg-purple-500 text-white" 
                : "bg-slate-700 hover:bg-slate-600 text-slate-300"
            }`}
          >
            <Activity className="w-4 h-4" />
            {showVolatility ? "Hide volatility" : "Show volatility"}
          </button>
        )}
      </div>

      {error && (<div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">{error}</div>)}

      {loading && (
        <div className="bg-slate-800/60 rounded-2xl h-64 border border-slate-700/60 animate-pulse flex items-center justify-center">
          <p className="text-slate-400">Loading data...</p>
        </div>
      )}

      {/* Stats Cards */}
      {data && !loading && stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatCard title="Total records" value={data.total?.toLocaleString()} icon={Database} />
          <StatCard title="Latest rate" value={`MWK ${stats.latest}`} icon={TrendingUp} 
            subtitle={`Since ${stats.startDate}`} />
          <StatCard title="Period change" value={`${stats.change > 0 ? '+' : ''}${stats.change}`} 
            icon={stats.change >= 0 ? ArrowUp : ArrowDown}
            subtitle={`${stats.changePct > 0 ? '+' : ''}${stats.changePct}%`} />
          <StatCard title="Average rate" value={`MWK ${stats.avg}`} icon={BarChart3} />
          <StatCard title="Volatility (σ)" value={`${stats.stdDev} MWK`} icon={Activity}
            subtitle={`Range: ${stats.min} – ${stats.max}`} />
        </div>
      )}

      {/* Main Chart */}
      {data && !loading && data.data?.length > 0 && (
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Rate chart</h3>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-blue-500 rounded-sm"></div>
                <span>MWK/USD Rate</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-0.5 bg-emerald-400 w-6"></div>
                <span>Average: {stats.avg}</span>
              </div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <ComposedChart data={data.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="date" 
                tick={{ fill: "#94a3b8", fontSize: 11 }} 
                interval={Math.floor(data.data.length / 10)} 
              />
              <YAxis 
                tick={{ fill: "#94a3b8", fontSize: 11 }} 
                domain={['auto', 'auto']} 
                tickFormatter={(v) => v.toFixed(0)} 
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "#1e293b", 
                  borderRadius: 8, 
                  border: '1px solid #475569', 
                  color: '#e2e8f0', 
                  fontSize: 12 
                }}
                formatter={(v, name) => {
                  if (name === 'rate') return [`MWK ${Number(v).toFixed(2)}`, 'Exchange rate'];
                  if (name === 'average') return [`MWK ${Number(v).toFixed(2)}`, 'Period average'];
                  return [v, name];
                }} 
              />
              <Area 
                type="monotone" 
                dataKey="rate" 
                stroke="#3b82f6" 
                fill="#3b82f6" 
                fillOpacity={0.3} 
                name="rate"
              />
              <ReferenceLine 
                y={Number(stats.avg)} 
                stroke="#34d399" 
                strokeDasharray="5 5" 
                strokeWidth={1}
                label={{ value: `Avg: ${stats.avg}`, fill: '#34d399', fontSize: 11, position: 'right' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Volatility Chart - FIXED */}
      {data && !loading && volatilityData && showVolatility && (
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Daily volatility</h3>
            <div className="flex items-center gap-4 text-xs text-slate-400">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-400 rounded-sm"></div>
                <span>Rate weakening (↗)</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-emerald-400 rounded-sm"></div>
                <span>Rate strengthening (↘)</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-slate-500 rounded-sm"></div>
                <span>No change</span>
              </div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={volatilityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="date" 
                tick={{ fill: "#94a3b8", fontSize: 10 }} 
                interval={Math.floor(volatilityData.length / 8)} 
              />
              <YAxis 
                tick={{ fill: "#94a3b8", fontSize: 10 }} 
                tickFormatter={(v) => v.toFixed(1)}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: "#1e293b", 
                  borderRadius: 8, 
                  border: '1px solid #475569', 
                  color: '#e2e8f0', 
                  fontSize: 12 
                }}
                formatter={(v, name) => {
                  const val = Number(v);
                  if (name === 'absChange') return [`${val.toFixed(2)} MWK`, 'Absolute change'];
                  return [v, name];
                }}
                labelFormatter={(label) => {
                  const entry = volatilityData.find(d => d.date === label);
                  if (!entry) return label;
                  const direction = entry.change > 0 ? '↗ Weakening' : entry.change < 0 ? '↘ Strengthening' : '→ No change';
                  return `${label} — ${direction}`;
                }}
              />
              <Bar 
                dataKey="change" 
                radius={[2, 2, 0, 0]}
              >
                {volatilityData.map((entry, index) => {
                  let color;
                  if (entry.change > 0) {
                    color = '#ef4444'; // Red for weakening
                  } else if (entry.change < 0) {
                    color = '#34d399'; // Green for strengthening
                  } else {
                    color = '#64748b'; // Gray for no change
                  }
                  return <Cell key={`cell-${index}`} fill={color} fillOpacity={0.7} />;
                })}
              </Bar>
              <ReferenceLine y={0} stroke="#475569" />
            </BarChart>
          </ResponsiveContainer>
          
          {/* Volatility Summary */}
          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
              <div className="bg-slate-700/40 rounded-lg p-3">
                <p className="text-slate-400 text-xs">Avg daily change</p>
                <p className={`text-sm font-semibold ${Number(stats.avgDailyChange) > 0 ? 'text-red-400' : Number(stats.avgDailyChange) < 0 ? 'text-emerald-400' : 'text-slate-300'}`}>
                  {Number(stats.avgDailyChange) > 0 ? '+' : ''}{stats.avgDailyChange} MWK
                </p>
              </div>
              <div className="bg-slate-700/40 rounded-lg p-3">
                <p className="text-slate-400 text-xs">Max daily increase</p>
                <p className="text-sm font-semibold text-red-400">+{stats.maxDailyIncrease} MWK</p>
              </div>
              <div className="bg-slate-700/40 rounded-lg p-3">
                <p className="text-slate-400 text-xs">Max daily decrease</p>
                <p className="text-sm font-semibold text-emerald-400">{stats.maxDailyDecrease} MWK</p>
              </div>
              <div className="bg-slate-700/40 rounded-lg p-3">
                <p className="text-slate-400 text-xs">Overall change</p>
                <p className={`text-sm font-semibold ${Number(stats.change) > 0 ? 'text-red-400' : Number(stats.change) < 0 ? 'text-emerald-400' : 'text-slate-300'}`}>
                  {Number(stats.change) > 0 ? '+' : ''}{stats.change} MWK ({Number(stats.changePct) > 0 ? '+' : ''}{stats.changePct}%)
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Rate Distribution Summary */}
      {data && !loading && stats && (
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
            <Info className="w-4 h-4 text-blue-400" />
            Rate summary
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-sm">
            <div className="bg-slate-700/40 rounded-lg p-3">
              <p className="text-slate-400 text-xs">Highest rate</p>
              <p className="text-white font-semibold">MWK {stats.max}</p>
            </div>
            <div className="bg-slate-700/40 rounded-lg p-3">
              <p className="text-slate-400 text-xs">Lowest rate</p>
              <p className="text-white font-semibold">MWK {stats.min}</p>
            </div>
            <div className="bg-slate-700/40 rounded-lg p-3">
              <p className="text-slate-400 text-xs">Starting rate</p>
              <p className="text-white font-semibold">MWK {stats.oldest}</p>
            </div>
            <div className="bg-slate-700/40 rounded-lg p-3">
              <p className="text-slate-400 text-xs">Ending rate</p>
              <p className="text-white font-semibold">MWK {stats.latest}</p>
            </div>
            <div className="bg-slate-700/40 rounded-lg p-3">
              <p className="text-slate-400 text-xs">Total change</p>
              <p className={`font-semibold ${Number(stats.change) > 0 ? 'text-red-400' : Number(stats.change) < 0 ? 'text-emerald-400' : 'text-slate-300'}`}>
                {Number(stats.change) > 0 ? '+' : ''}{stats.change} MWK
              </p>
            </div>
            <div className="bg-slate-700/40 rounded-lg p-3">
              <p className="text-slate-400 text-xs">% Change</p>
              <p className={`font-semibold ${Number(stats.changePct) > 0 ? 'text-red-400' : Number(stats.changePct) < 0 ? 'text-emerald-400' : 'text-slate-300'}`}>
                {Number(stats.changePct) > 0 ? '+' : ''}{stats.changePct}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* About this data */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">About this data</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-slate-400"><span className="text-slate-300 font-medium">Source:</span> Reserve Bank of Malawi</p>
          </div>
          <div>
            <p className="text-slate-400"><span className="text-slate-300 font-medium">Period:</span> 2013 – Present</p>
          </div>
          <div>
            <p className="text-slate-400"><span className="text-slate-300 font-medium">Updates:</span> Daily (business days)</p>
          </div>
        </div>
      </div>
    </div>
  );
}