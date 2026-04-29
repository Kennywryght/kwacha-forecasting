import React from "react";
import {
  Chart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

export const ForecastChart = ({ forecasts }) => {
  // Validate input props
  if (!forecasts || !Array.isArray(forecasts)) {
    return <div className="flex justify-center items-center h-64">No forecast data available.</div>;
  }

  // DATA TRANSFORMATION: Ensure date is sorted for the line chart
  const sortedData = [...forecasts].sort((a, b) => new Date(a.date) - new Date(b.date));

  return (
    <div className="bg-slate-800 rounded-2xl p-6 border border-slate-700">
      <h2 className="text-xl font-semibold text-slate-900">7-Day Forecast</h2>
      
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart
          margin={{ top: 20, right: 20, left: 10, bottom: 10 }}
          data={{
            date: 'date',
            rate: 'rate',
          }}
        >
          <defs>
            <linearGradient id="rateGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stop-color="#3b82f6" />
              <stop offset="95%" stop-color="#1ded8" />
            </linearGradient>
          </defs>
          
          <defs>
            <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stop-color="#3b82f6" stop-opacity="0.6" />
              <stop offset="95%" stop-color="#1ded8" stop-opacity="0.1" />
            </linearGradient>
          </defs>
          
          {/* --- THE FORECAST LINE (Area) */}
          <Area 
            type="monotone"
            dataKey="rate"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#rateGrad)"
            name="Forecast"
          />
          
          {/* THE CONFIDENCE BAND (Visual Flair) */}
          {/* Only show if data exists and we have enough points */}
          {sortedData.length > 0 && sortedData.some(item => item.rate !== null) && (
             <Area 
              type="monotone"
              dataKey="rate"
                stroke="#8884d8"
                strokeWidth={0}
                strokeDasharray="3 3 2"
                fillOpacity={0.05}
                name="Confidence"
              />
          )}

          {/* DOTS */}
          <Line
            type="monotone"
            dataKey="rate"
            stroke="#b82f6"
            strokeWidth={2}
            dot={true}
            activeDot={{ r: 8, fill: "#b82f6" }}
          />
          
          {/* TOOLTIP */}
          <Tooltip 
            contentStyle={{
              backgroundColor: "rgba(0, 0, 0, 0.8)",
              color: "#fff",
              borderRadius: "4px"
            }}
            itemSorter={(a, b) => a.date - b.date} // Tooltip sorting
            itemFormatter={(value, name) => (
              <div>
                <p className="font-bold text-gray-800">{name}</p>
                <p className="text-sm text-gray-600">{value.date}</p>
                <p className="text-lg font-mono font-semibold text-blue-600">{value.rate.toFixed(2)} MWK</p>
              </div>
            )}
          />
          
          {/* Y-AXIS */}
          <XAxis 
            dataKey="date" 
            tick={{ fill: "none" }} 
            type="category" 
            tickLine={false} 
            axisLine={false} 
            tickFormatter={(value) => {
                const d = new Date(value);
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); 
              }}
            />
          
          <YAxis 
            domain={[1690, 1800]} 
            axisLine={false}
            tickCount={5}
            tickFormatter={(value) => `MWK ${value.toFixed(0)}`} 
            labelStyle={{ color: "#94a3b8" }}
          />
          
          <CartesianGrid strokeDasharray="3 3 2" stroke="#cbd5e1" />
          
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ForecastChart;