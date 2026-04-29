import React from "react";
import { ModelMetricsTable } from "../components/ModelMetricsTable";

export default function ModelMetricsTable() {
  // Ideally, this comes from the API: GET /models/all
  // Since we are using the old hook structure, we check for falsy models
  const { models } = { models: [] }; // Placeholder for now, or connect to your hook

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-xl font-semibold text-gray-900">Model Performance</h2>
      
      {!models || !models.length > 0 ? (
        <div className="text-center text-gray-500 mt-10">
          <p className="text-sm">No model metrics yet. Train models first.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full w-full text-sm text-left">
            <thead>
              <tr className="text-left border-b bg-gray-100">
                <th className="px-4 py-2 text-left font-semibold text-gray-700">Model</th>
                <th className="px-4 py-2 text-left font-semibold text-gray-700">RMSE</th>
                <th className="px-4 py-2 text-left font-semibold text-gray-700">MAE</th>
                <th className="px-4 py-2 text-left font-semibold text-gray-700">MAPE %</th>
                <th className="px-4 py-2 text-left font-semibold text-gray-700">R²</th>
              </tr>
            </thead>
            <tbody className="bg-white">
              {models.map((model, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-900 font-medium">{model.model_name}</td>
                  <td className="px-4 text-gray-900 font-mono">{model.rmse.toFixed(2)}</td>
                  <td className="import React from "react";
import { Chart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export const HistoryChart = ({ history, loading }) => {
  // This component now uses the `useForecasts` hook for the Rate Card "Current Rate"
  // If history is missing, it shows a simple loading or empty state

  // 1. Check for empty history
  if (!history || !Array.isArray(history)) {
      return (
        <div className="text-center text-gray-400 mt-10">
          <p>No history found.</p>
        </div>
      );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border-gray-200 p-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Historical MWK/USD Rate (1 Year)</h2>
      
      <div className="h-64">
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart
            data={history}
            margin={{ top: 20, right: 20, left: 20, bottom: 10 }}
            data={{
              date: "date",
              rate: "rate",
            }}
            margin={{ left: 10, right: 30, bottom: 20 }} 
          >
            <defs>
              <linearGradient id="rateGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.6" />
                <stop offset="100%" stopColor="#1d4ed8" />
              </linearGradient>
            </defs>
            
            {/* Area Chart */}
            <Area 
              type="monotone"
              dataKey="rate"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#rateGrad)"
              name="Historical Rate"
            />
            
            <CartesianGrid strokeDasharray="3 3 2" stroke="#cbd5e1" />
            
            <XAxis 
              dataKey="date" 
              tickLine={false} 
              tickFormatter={(value) => {
                const d = new Date(value);
                return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
              }}
              axisLine={false}
            />
            
            <YAxis 
              domain={[1690, 2000]} 
              tickLine={false} 
              tickFormatter={(value) => `MWK ${value.toFixed(0)}`} 
              labelStyle={{ color: "#3b82f6" }}
            />
            
            <Tooltip 
              contentStyle={{
                backgroundColor: "rgba(0, 0,0,0.8)",
                color: "#fff",
                borderRadius: "4px"
              }}
              itemSorter={(a, b) => a.date - b.date} 
              formatter={(value, name) => (
                <div>
                  <p className="font-bold text-gray-800">{name}</p>
                  <p className="text-sm text-gray-600">{value.date}</p>
                  <p className="text-lg font-mono font-semibold text-blue-600">{value.rate.toFixed(2)} MWK</p>
                </div>
              )}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default HistoryChart;