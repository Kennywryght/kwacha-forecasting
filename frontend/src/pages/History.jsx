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
const Card = ({ title, value }) => <div><h3>{title}</h3><p>{value}</p></div>;
const useLanguage = () => ({ lang: "en", setLang: () => {} });
import { Calendar } from "lucide-react";

export default function History() {
  const { t } = useLanguage();
  const [start, setStart] = useState("2023-01-01");
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [timeRange, setTimeRange] = useState("1y");

  const fetch = async () => {
    setLoading(true);
    try {
      const res = await fetchHistory(start, end);
      // res = { start_date, end_date, total, latest_rate, data: [...] }
      setData(res);
    } catch (e) {
      alert("Failed to load history");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickRange = (range) => {
    setTimeRange(range);
    const today = new Date();
    let from = new Date();
    switch (range) {
      case "1m":
        from.setMonth(today.getMonth() - 1);
        break;
      case "3m":
        from.setMonth(today.getMonth() - 3);
        break;
      case "6m":
        from.setMonth(today.getMonth() - 6);
        break;
      case "1y":
        from.setFullYear(today.getFullYear() - 1);
        break;
      case "5y":
        from.setFullYear(today.getFullYear() - 5);
        break;
      case "all":
        from = new Date("2012-01-01");
        break;
      default:
        break;
    }
    setStart(from.toISOString().slice(0, 10));
    setEnd(today.toISOString().slice(0, 10));
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6 text-white">
      <h1 className="text-2xl sm:text-3xl font-bold">{t.history}</h1>

      {/* Quick select */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-4 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2 text-slate-300">
          <Calendar size={20} />
          <span className="font-medium">Time Range:</span>
        </div>
        <div className="flex gap-2">
          {["1m", "3m", "6m", "1y", "5y", "all"].map((range) => (
            <button
              key={range}
              onClick={() => handleQuickRange(range)}
              className={`px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                timeRange === range
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}
            >
              {range.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Manual date inputs */}
      <div className="flex gap-4 items-end flex-wrap">
        <div>
          <label className="text-slate-400 text-sm block mb-1">
            Start Date
          </label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600"
          />
        </div>
        <div>
          <label className="text-slate-400 text-sm block mb-1">
            End Date
          </label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="bg-slate-700 text-white px-3 py-2 rounded-lg border border-slate-600"
          />
        </div>
        <button
          onClick={fetch}
          className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm"
        >
          {loading ? t.loading : "Load"}
        </button>
      </div>

      {/* Stats */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card title="Total Records" value={data.total} />
          <Card
            title="Latest Rate"
            value={`${data.latest_rate?.toLocaleString()} MWK`}
          />
          <Card
            title="Date Range"
            value={`${data.start_date} → ${data.end_date}`}
          />
        </div>
      )}

      {/* Chart */}
      {data && (
        <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6">
          <h2 className="text-xl font-semibold mb-4">
            Exchange Rate History
          </h2>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={data.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
              />
              <YAxis
                tick={{ fill: "#94a3b8", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  borderRadius: 8,
                }}
              />
              <Area
                type="monotone"
                dataKey="rate"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.3}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Placeholder for indicators */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6 text-center text-slate-400">
        <h3 className="text-lg font-semibold mb-2 text-white">
          Macroeconomic Indicators Coming Soon
        </h3>
        <p>
          Data on inflation, foreign reserves, money supply and policy rates
          will be available via an integrated API.
        </p>
      </div>

      {/* Data Sources */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-2xl p-6">
        <h3 className="text-xl font-bold mb-4">Data Sources</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
          <div>
            <h4 className="font-semibold text-slate-300 mb-2">
              Primary Data
            </h4>
            <ul className="text-slate-400 space-y-1">
              <li>Exchange Rates: Investing.com / RBM</li>
              <li>Inflation: IMF International Financial Statistics</li>
              <li>Foreign Reserves: Reserve Bank of Malawi</li>
              <li>Money Supply: RBM Statistical Bulletin</li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold text-slate-300 mb-2">
              Model Methodology
            </h4>
            <ul className="text-slate-400 space-y-1">
              <li>Historical Period: 2012-2025</li>
              <li>Stationarity tests (ADF, KPSS)</li>
              <li>Model selection via AIC/BIC</li>
              <li>Rolling window validation</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}