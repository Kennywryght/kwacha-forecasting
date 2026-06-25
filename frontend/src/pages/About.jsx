import React from "react";
import { AlertCircle, BookOpen, BarChart3, TrendingUp, Target, Shield, Mail } from "lucide-react";

export default function About() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-12 space-y-12">
      {/* Hero */}
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-4">About KwachaCast</h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-lg">
          An AI-powered forecasting system for the Malawi Kwacha exchange rate, 
          built to help businesses and individuals make informed financial decisions.
        </p>
      </div>

      {/* Mission */}
      <div className="bg-emerald-900/20 border-l-4 border-emerald-500 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-3">
          <Target className="w-5 h-5 text-emerald-400" />
          <h2 className="text-xl font-bold text-emerald-300">Our mission</h2>
        </div>
        <p className="text-emerald-100/80 leading-relaxed">
          To provide accessible, accurate, and transparent exchange rate forecasts 
          that empower businesses, travelers, and individuals in Malawi.
        </p>
      </div>

      {/* How it works */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <BarChart3 className="w-7 h-7 text-blue-400" />
          <h2 className="text-2xl font-bold text-white">How it works</h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6 space-y-4">
          <div className="flex items-start gap-3">
            <span className="text-emerald-400 font-bold text-lg">1.</span>
            <div>
              <h3 className="font-semibold text-white">Data collection</h3>
              <p className="text-slate-400 text-sm">Historical exchange rates from 2013 to present, sourced from the Reserve Bank of Malawi and global currency APIs.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <span className="text-emerald-400 font-bold text-lg">2.</span>
            <div>
              <h3 className="font-semibold text-white">Model training</h3>
              <p className="text-slate-400 text-sm">Advanced statistical models (ARIMA & ARIMAX) learn patterns from 13+ years of data to predict future rates.</p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <span className="text-emerald-400 font-bold text-lg">3.</span>
            <div>
              <h3 className="font-semibold text-white">Forecast generation</h3>
              <p className="text-slate-400 text-sm">Daily predictions with 80% confidence intervals, updated each business day.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Accuracy */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <Shield className="w-7 h-7 text-purple-400" />
          <h2 className="text-2xl font-bold text-white">Accuracy & reliability</h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
            <div>
              <p className="text-3xl font-bold text-emerald-400">0.30%</p>
              <p className="text-slate-400 text-sm mt-1">Average error rate (MAPE)</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-blue-400">13+</p>
              <p className="text-slate-400 text-sm mt-1">Years of training data</p>
            </div>
            <div>
              <p className="text-3xl font-bold text-purple-400">80%</p>
              <p className="text-slate-400 text-sm mt-1">Confidence interval</p>
            </div>
          </div>
          <p className="text-slate-500 text-xs text-center mt-4">
            Our models achieve exceptional accuracy due to Malawi's managed exchange rate policy, 
            which keeps daily movements minimal and predictable.
          </p>
        </div>
      </section>

      {/* Disclaimer */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <AlertCircle className="w-7 h-7 text-amber-400" />
          <h2 className="text-2xl font-bold text-white">Important disclaimer</h2>
        </div>
        <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-xl p-6 space-y-3 text-amber-100/90">
          <p className="font-semibold">For informational purposes only.</p>
          <ul className="list-disc ml-5 space-y-2 text-sm">
            <li>This is not financial advice. Consult a professional for financial decisions.</li>
            <li>While our models are highly accurate, no forecast can guarantee future rates.</li>
            <li>Exchange rates are influenced by many unpredictable factors including central bank policy and global markets.</li>
          </ul>
        </div>
      </section>

      {/* Project info */}
      <section>
        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-7 h-7 text-slate-300" />
          <h2 className="text-2xl font-bold text-white">Project information</h2>
        </div>
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold text-white mb-1">Researcher</h4>
              <p className="text-slate-300">Kennedy Banda</p>
              <p className="text-slate-400 text-sm">Data Science, Mzuzu University</p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-1">Supervisor</h4>
              <p className="text-slate-300">Dr. Ruben Moyo</p>
              <p className="text-slate-400 text-sm">Faculty of ICT</p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-1">Project type</h4>
              <p className="text-slate-300">Data Science Capstone Project</p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-1">Technologies</h4>
              <p className="text-slate-300">Python, React, FastAPI, SQLite</p>
              <p className="text-slate-400 text-sm">ARIMA, ARIMAX, Prophet, Ensemble</p>
            </div>
          </div>
        </div>
      </section>

      {/* Contact */}
      <div className="bg-gradient-to-r from-blue-900/30 to-slate-800/60 border border-blue-500/20 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-2 mb-3">
          <Mail className="w-5 h-5 text-blue-400" />
          <h3 className="text-xl font-bold text-white">Questions or feedback?</h3>
        </div>
        <p className="text-slate-400 mb-4">We welcome suggestions for improvement.</p>
        <div className="space-y-1 text-slate-300 text-sm">
          <p>Email: <a href="mailto:kbanda@mzuzuuni.mw" className="text-blue-400 hover:underline">kbanda@mzuzuuni.mw</a></p>
        </div>
      </div>
    </div>
  );
}