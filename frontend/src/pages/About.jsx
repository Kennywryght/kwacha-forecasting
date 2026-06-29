import React from "react";
import { Target, BarChart3, Shield, Brain, Layers, LineChart } from "lucide-react";

export default function About() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12 space-y-10">
      {/* Hero */}
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-4">About KwachaCast</h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-lg">
          An AI-powered exchange rate forecasting system for the Malawi Kwacha, 
          built to help businesses and individuals make informed financial decisions.
        </p>
      </div>

      {/* Problem & Solution */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <Brain className="w-6 h-6 text-purple-400" />
          <h2 className="text-2xl font-bold text-white">Problem & solution</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-red-900/10 border border-red-500/20 rounded-xl p-5">
            <h3 className="text-red-400 font-semibold mb-2 text-sm uppercase tracking-wider">The problem</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Businesses and individuals in Malawi lack access to reliable exchange rate forecasts, 
              making it difficult to plan imports, budget for school fees, or time currency conversions effectively.
            </p>
          </div>
          <div className="bg-emerald-900/10 border border-emerald-500/20 rounded-xl p-5">
            <h3 className="text-emerald-400 font-semibold mb-2 text-sm uppercase tracking-wider">Our solution</h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              A machine learning system that analyzes 13+ years of exchange rate data with multiple forecasting models 
              to provide daily predictions with 0.30% average error (MAPE).
            </p>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <BarChart3 className="w-6 h-6 text-blue-400" />
          <h2 className="text-2xl font-bold text-white">How it works</h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6 space-y-4">
          {[
            { step: "1", title: "Data collection", desc: "Historical MWK/USD rates (2013–present) from the Reserve Bank of Malawi, supplemented with live currency API data and macroeconomic indicators (inflation, interest rates, money supply)." },
            { step: "2", title: "Feature engineering", desc: "42 features created including lagged values, rolling statistics, momentum indicators, cyclical temporal encodings, and macroeconomic differentials." },
            { step: "3", title: "Model training", desc: "Five forecasting models trained: ARIMA, ARIMAX, Prophet, XGBoost, and LightGBM. Hyperparameters tuned using RandomizedSearchCV with time-based cross-validation." },
            { step: "4", title: "Ensemble prediction", desc: "Models combined using weighted averaging based on RMSE performance. Confidence intervals show prediction uncertainty (95% range)." },
            { step: "5", title: "Daily updates", desc: "Forecasts regenerated each business day. System supports fast refit for incremental updates and full retraining for periodic optimization." },
          ].map((item) => (
            <div key={item.step} className="flex items-start gap-3">
              <span className="bg-emerald-600 text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                {item.step}
              </span>
              <div>
                <h3 className="font-semibold text-white text-sm">{item.title}</h3>
                <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Models & Technology */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <Layers className="w-6 h-6 text-amber-400" />
          <h2 className="text-2xl font-bold text-white">Models & technology</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
            <h3 className="text-white font-semibold text-sm mb-3">Forecasting models</h3>
            <div className="space-y-2 text-xs">
              {[
                { name: "ARIMA", desc: "Statistical baseline with auto-order selection via AIC" },
                { name: "ARIMAX", desc: "ARIMA enhanced with exogenous economic indicators" },
                { name: "Prophet", desc: "Decomposition-based model with changepoint detection" },
                { name: "XGBoost", desc: "Gradient boosting with 42 engineered features" },
                { name: "LightGBM", desc: "High-performance gradient boosting framework" },
                { name: "Ensemble", desc: "Weighted combination of all models by RMSE" },
              ].map((m) => (
                <div key={m.name} className="flex items-start gap-2">
                  <span className="text-emerald-400 font-mono text-xs min-w-[80px]">{m.name}</span>
                  <span className="text-slate-400">{m.desc}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5">
            <h3 className="text-white font-semibold text-sm mb-3">Technology stack</h3>
            <div className="space-y-2 text-xs">
              {[
                { cat: "Backend", tech: "Python, FastAPI, SQLAlchemy" },
                { cat: "ML/AI", tech: "Statsmodels, Scikit-learn, XGBoost, LightGBM, Prophet" },
                { cat: "Frontend", tech: "React, Tailwind CSS, Recharts" },
                { cat: "Database", tech: "SQLite (dev), PostgreSQL (prod)" },
                { cat: "Deployment", tech: "Render (backend), Vercel (frontend)" },
                { cat: "Training", tech: "Google Colab with GPU acceleration" },
              ].map((t) => (
                <div key={t.cat} className="flex items-start gap-2">
                  <span className="text-blue-400 font-mono text-xs min-w-[90px]">{t.cat}</span>
                  <span className="text-slate-400">{t.tech}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Model Performance */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <Shield className="w-6 h-6 text-emerald-400" />
          <h2 className="text-2xl font-bold text-white">Model performance</h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            {[
              { value: "0.30%", label: "MAPE", desc: "Mean Absolute Percentage Error" },
              { value: "4.88", label: "RMSE", desc: "Root Mean Square Error (MWK)" },
              { value: "0.991", label: "R²", desc: "Coefficient of determination" },
              { value: "78%", label: "Directional", desc: "Correct direction prediction" },
            ].map((m) => (
              <div key={m.label} className="bg-slate-700/40 rounded-lg p-3">
                <p className="text-2xl font-bold text-emerald-400">{m.value}</p>
                <p className="text-white text-xs font-medium mt-1">{m.label}</p>
                <p className="text-slate-500 text-xs mt-0.5">{m.desc}</p>
              </div>
            ))}
          </div>
          <p className="text-slate-500 text-xs text-center mt-4">
            Evaluated on a 15% held-out test set (time-based split). 
            MAPE of 0.30% means average prediction error of ~5 MWK when the rate is 1,735 MWK/USD.
          </p>
        </div>
      </section>

      {/* Key Features */}
      <section>
        <div className="flex items-center gap-3 mb-5">
          <LineChart className="w-6 h-6 text-purple-400" />
          <h2 className="text-2xl font-bold text-white">Key features</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { title: "Multiple horizons", desc: "1-day, 7-day, and 30-day forecasts to support short and medium-term planning." },
            { title: "Confidence intervals", desc: "95% prediction intervals showing forecast uncertainty at each horizon." },
            { title: "Actionable insights", desc: "Plain-language guidance on what rate movements mean for different users." },
            { title: "Historical analysis", desc: "Interactive charts from 2013–present with volatility and trend analysis." },
            { title: "Model transparency", desc: "Accuracy metrics and past forecast comparisons publicly available." },
            { title: "Offline access", desc: "Installable as a PWA for quick access without app stores." },
          ].map((f) => (
            <div key={f.title} className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-4">
              <h3 className="text-white font-semibold text-sm mb-1">{f.title}</h3>
              <p className="text-slate-400 text-xs leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Limitations */}
      <div className="bg-amber-900/10 border border-amber-500/20 rounded-xl p-6">
        <h3 className="text-amber-400 font-semibold text-sm mb-3 uppercase tracking-wider">Limitations & disclaimer</h3>
        <ul className="space-y-2 text-amber-100/80 text-sm">
          <li className="flex items-start gap-2">
            <span className="text-amber-400 shrink-0">•</span>
            Forecasts are for informational purposes only — not financial advice.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-amber-400 shrink-0">•</span>
            Accuracy depends on Malawi's managed exchange rate policy; structural changes (devaluations) may temporarily reduce accuracy.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-amber-400 shrink-0">•</span>
            Exogenous variable forecasts (inflation, interest rates) assume current conditions persist.
          </li>
          <li className="flex items-start gap-2">
            <span className="text-amber-400 shrink-0">•</span>
            Past accuracy does not guarantee future performance.
          </li>
        </ul>
      </div>
    </div>
  );
}