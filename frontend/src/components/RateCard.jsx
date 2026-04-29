import { useForecasts, useForecasts } from "../hooks/useForecasts"; // Import the hook you just updated
import TrendingUp from "lucide-react";

export default function RateCard({ }) {
  // We pull data from the hook which fetches from API
  const { forecasts, loading, error } = useForecasts(7);

  // We use the "latest" forecast to determine the "Live Rate"
  const latestForecasts = forecasts.length > 0 ? forecasts[0] : null;

  return (
    <div className="bg-gradient-to-br from-blue-900 to-slate-800 rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <h3 className="text-2xl font-bold text-white">MWK/USD Exchange Rate</h3>
          
          {/* Status Badge */}
          <span className={`px-2 py-1 rounded-full font-bold text-xs uppercase tracking-tight ${
            loading ? "bg-yellow-500 animate-pulse" 
              : "bg-green-500"
          }`}>
            {loading ? "LIVE DATA PENDING" : "LIVE API CONNECTED"}
          </span>
        </div>

        {/* Rate Display */}
        <div className="mt-4">
          {!latestForecasts ? (
            <>
              <div className="text-gray-200 text-center mb-1">No live data available.</div>
            </>
          ) : (
              <>
                <p className="text-4xl font-bold text-white tracking-wider">
                  {latestForecasts.rate?.toFixed(2)} MWK
                </p>
                <p className="text-sm text-gray-300">as of {latestForecasts.target_date}</p>
              </>
          )}
        </div>

        {/* Action Button */}
        <div className="mt-6">
          <button 
            onClick={() => window.location.href = "/history"} 
            className="w-full bg-white/20 border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium rounded-lg shadow-sm"
          >
            View Full History
          </button>
        </div>
      </div>
    </div>
  );
};