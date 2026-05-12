import React from 'react';

export default function ApiDocs() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12 space-y-8 text-white">
      <h1 className="text-3xl font-bold">API Documentation</h1>
      <p className="text-slate-400">
        Base URL: <code className="bg-slate-800 px-2 py-1 rounded text-blue-400">/api/v1</code>
      </p>

      {/* Endpoints */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 space-y-2">
          <h3 className="text-green-400 font-mono font-semibold">GET /rates/latest</h3>
          <p className="text-slate-400 text-sm">Returns latest exchange rate and daily return.</p>
          <pre className="bg-slate-950 p-3 rounded text-xs text-slate-300 overflow-x-auto">
{`{
  "rate": 1089.45,
  "date": "2025-05-11",
  "daily_return": -0.12,
  "source": "RBM"
}`}
          </pre>
        </div>

        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 space-y-2">
          <h3 className="text-green-400 font-mono font-semibold">GET /rates/history</h3>
          <p className="text-slate-400 text-sm">Historical rates between two dates.</p>
          <pre className="bg-slate-950 p-3 rounded text-xs text-slate-300 overflow-x-auto">
{`?start=2024-01-01&end=2025-01-01`}
          </pre>
        </div>

        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 space-y-2">
          <h3 className="text-green-400 font-mono font-semibold">GET /forecasts/all</h3>
          <p className="text-slate-400 text-sm">All model forecasts for current horizon.</p>
          <pre className="bg-slate-950 p-3 rounded text-xs text-slate-300 overflow-x-auto">
{`[
  { "name": "arima", "prediction": [1085,...] },
  { "name": "arimax", "prediction": [1083,...] },
  ...
]`}
          </pre>
        </div>

        <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-5 space-y-2">
          <h3 className="text-green-400 font-mono font-semibold">POST /forecasts/generate</h3>
          <p className="text-slate-400 text-sm">Triggers new forecast generation (requires training).</p>
          <pre className="bg-slate-950 p-3 rounded text-xs text-slate-300 overflow-x-auto">
{`{ "horizon": 7 }`}
          </pre>
        </div>
      </div>

      {/* Response Format */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6 space-y-4">
        <h2 className="text-xl font-bold">Response Envelope</h2>
        <pre className="bg-slate-950 p-4 rounded text-sm text-slate-300 overflow-x-auto">
{`{
  "success": true,
  "data": { ... },
  "timestamp": "2025-05-11T14:30:00Z",
  "notes": "Forecasts for informational purposes only"
}`}
        </pre>
        <p className="text-slate-400 text-sm">
          All endpoints return this structure except for <code>/forecasts/all</code> which returns an array directly.
        </p>
      </div>

      {/* Usage Example */}
      <div className="bg-slate-800/60 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-bold mb-4">JavaScript Example</h2>
        <pre className="bg-slate-950 p-4 rounded text-sm text-slate-300 overflow-x-auto">
{`fetch('http://127.0.0.1:8000/api/v1/rates/latest')
  .then(r => r.json())
  .then(data => console.log(data.data.rate))`}
        </pre>
      </div>
    </div>
  );
}