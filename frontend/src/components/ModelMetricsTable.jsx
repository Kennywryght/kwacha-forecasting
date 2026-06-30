import React from "react";

export default function ModelMetricsTable({
  metrics = [],
  lang = "en",
}) {

  const headers =
    lang === "ny"
      ? ["Model", "RMSE", "MAE", "MAPE %", "Status"]
      : ["Model", "RMSE", "MAE", "MAPE %", "Status"];

  // Sort by RMSE (lowest first)
  const sortedMetrics = [...metrics].sort(
    (a, b) => a.rmse - b.rmse
  );

  // Best model
  const bestModel = sortedMetrics[0];

  return (
    <div className="bg-stone-900/60 rounded-2xl p-5 border border-stone-700/60 backdrop-blur h-full">

      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-lg font-semibold text-stone-100">
            {lang === "ny"
              ? "Kuyerekeza kwa Model"
              : "Model Performance"}
          </h2>

          <p className="text-sm text-stone-400 mt-1">
            Comparison of forecasting model accuracy
          </p>
        </div>

        {bestModel && (
          <div className="bg-gold-500/20 border border-gold-500/30 px-3 py-1 rounded-full text-xs text-gold-300">
            Best: {bestModel.model_name || bestModel.name}
          </div>
        )}
      </div>

      {sortedMetrics.length === 0 ? (
        <div className="text-center text-stone-400 mt-10">
          <p className="text-sm">
            {lang === "ny"
              ? "Palibe zotsatira za model."
              : "No model metrics yet."}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-left">

            <thead>
              <tr className="border-b border-stone-600 bg-stone-700/30">

                {headers.map((header) => (
                  <th
                    key={header}
                    className="px-4 py-3 font-semibold text-stone-300"
                  >
                    {header}
                  </th>
                ))}

              </tr>
            </thead>

            <tbody className="text-stone-300">

              {sortedMetrics.map((model, idx) => {

                const isBest =
                  (model.model_name || model.name) ===
                  (bestModel.model_name || bestModel.name);

                return (
                  <tr
                    key={idx}
                    className={`transition-colors hover:bg-stone-700/30 ${
                      isBest
                        ? "bg-gold-500/10 border-l-4 border-gold-400"
                        : ""
                    }`}
                  >

                    {/* MODEL NAME */}
                    <td className="px-4 py-3 font-medium text-stone-100">
                      {model.model_name || model.name || idx}
                    </td>

                    {/* RMSE */}
                    <td className="px-4 py-3 font-mono">
                      {model.rmse?.toFixed(2)}
                    </td>

                    {/* MAE */}
                    <td className="px-4 py-3 font-mono">
                      {model.mae?.toFixed(2)}
                    </td>

                    {/* MAPE */}
                    <td className="px-4 py-3 font-mono">
                      {model.mape?.toFixed(2)}%
                    </td>

                    {/* STATUS */}
                    <td className="px-4 py-3">
                      {isBest ? (
                        <span className="bg-gold-500/20 text-gold-300 px-2 py-1 rounded-full text-xs">
                          Best Model
                        </span>
                      ) : (
                        <span className="text-stone-400 text-xs">
                          Compared
                        </span>
                      )}
                    </td>

                  </tr>
                );
              })}

            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
