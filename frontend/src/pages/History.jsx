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
} from "recharts";
import { Calendar, TrendingUp, Database, Clock } from "lucide-react";

function StatCard({ title, value, icon: Icon }) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 backdrop-blur">
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className="w-4 h-4 text-emerald-400" />}
        <p className="text-xs text-slate-400 uppercase tracking-wider">{title}</p>
      </div>
      <p className="text-xl font-bold text-white">{value}</p>
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

  // Auto-fetch on mount
  React.useEffect(() => {
    fetch();
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6 text-white">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold">Exchange rate history</h1>
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
              {range === "all" ? "All" : range.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Manual date inputs */}
      <div className="flex gap-3 items-end flex-wrap">
        <div>
          <label className="text-slate-400 text-xs block mb-1">Start date</label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600"
          />
        </div>
        <div>
          <label className="text-slate-400 text-xs block mb-1">End date</label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="bg-slate-700 text-white text-sm px-3 py-2 rounded-lg border border-slate-600"
          />
        </div>
        <button
          onClick={fetch}
          disabled={loading}
          className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          {loading ? "Loading..." : "Load"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="bg-slate-800/60 rounded-2xl h-64 border border-slate-700/60 animate-pulse flex items-center justify-center">
          <p className="text-slate-400">Loading data...</p>
        </div>
      )}

      {/* Stats */}
      {data && !loading && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard title="Total records" value={data.total?.toLocaleString()} icon={Database} />
          <StatCard title="Latest rate" value={`MWK ${data.latest_rate?.toLocaleString()}`} icon={TrendingUp} />
          <StatCard title="Date range" value={`${data.start_date} → ${data.end_date}`} icon={Clock} />
        </div>
      )}

      {/* Chart */}
      {data && !loading && data.data?.length > 0 && (
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">
            Exchange rate chart
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={data.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" tick={{ fill: "#94a3b8", fontSize: 11 }} interval={Math.floor(data.data.length / 10)} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 11 }} domain={['auto', 'auto']} tickFormatter={(v) => v.toFixed(0)} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1e293b", borderRadius: 8, border: 'none', color: '#e2e8f0', fontSize: 12 }}
                formatter={(v) => [`MWK ${Number(v).toFixed(2)}`, 'Rate']}
              />
              <Area type="monotone" dataKey="rate" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Data info */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-5 backdrop-blur">
        <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-3">About this data</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <p className="text-slate-400">
              <span className="text-slate-300 font-medium">Source:</span> Reserve Bank of Malawi, Investing.com
            </p>
            <p className="text-slate-400">
              <span className="text-slate-300 font-medium">Period:</span> 2013 – Present
            </p>
            <p className="text-slate-400">
              <span className="text-slate-300 font-medium">Updates:</span> Daily (business days)
            </p>
          </div>
          <div className="space-y-2">
            <p className="text-slate-400">
              <span className="text-slate-300 font-medium">Methodology:</span> Official interbank rates
            </p>
            <p className="text-slate-400">
              <span className="text-slate-300 font-medium">Models:</span> ARIMA & ARIMAX ensemble
            </p>
            <p className="text-slate-400">
              <span className="text-slate-300 font-medium">Accuracy:</span> ~0.30% MAPE
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}