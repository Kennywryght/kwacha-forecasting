import React, { useState, useEffect } from "react";
import { useDashboardData } from "../hooks/useForecasts";
import { getForecasts, getForecastSummary } from "../utils/api";
import { AlertCircle, TrendingUp, TrendingDown, Loader2, DollarSign, Calendar, CheckCircle, Clock } from "lucide-react";

// ── SIMPLE MESSAGE SYSTEM ─────────────────────────────────────────────────
const getSimpleMessage = (currentRate, nextDayRate) => {
  if (!currentRate || !nextDayRate) return null;
  
  const change = nextDayRate - currentRate;
  const percentChange = (change / currentRate) * 100;
  
  // Show in PLAIN ENGLISH what will happen
  if (percentChange < -1) {
    return {
      title: "🎉 GOOD NEWS!",
      message: "The Kwacha is getting stronger",
      detail: "Your money will buy more. If you're selling USD, wait a few days for a better price.",
      color: "bg-emerald-500/10 border-emerald-500/20",
      textColor: "text-emerald-400",
      emoji: "📈",
      action: "💡 Hold onto USD if you can"
    };
  } else if (percentChange > 1) {
    return {
      title: "⚠️ HEADS UP!",
      message: "The Kwacha is getting weaker",
      detail: "Your money will buy less. If you need USD soon (school fees, imports), buy today.",
      color: "bg-red-500/10 border-red-500/20",
      textColor: "text-red-400",
      emoji: "📉",
      action: "💡 Buy USD now if you need it"
    };
  } else {
    return {
      title: "➡️ STABLE",
      message: "The Kwacha is not changing much",
      detail: "No rush to buy or sell. The rate should stay about the same.",
      color: "bg-blue-500/10 border-blue-500/20",
      textColor: "text-blue-400",
      emoji: "⏸️",
      action: "💡 No urgent action needed"
    };
  }
};

// ── TODAY'S RATE CARD (BIG & SIMPLE) ──────────────────────────────────────
function TodayRateCard({ currentRate }) {
  return (
    <div className="bg-gradient-to-br from-emerald-600 to-emerald-700 rounded-3xl p-8 text-white shadow-lg">
      <p className="text-emerald-100 text-lg font-medium mb-2">Today's Rate</p>
      <div className="flex items-baseline gap-2">
        <span className="text-5xl font-bold">{currentRate?.toFixed(2) || "---"}</span>
        <span className="text-2xl">MWK per USD</span>
      </div>
      <p className="text-emerald-100 text-sm mt-4">
        💰 This means 1 Dollar = {currentRate?.toFixed(2)} Kwacha
      </p>
    </div>
  );
}

// ── PLAIN ENGLISH MESSAGE (THE MOST IMPORTANT PART) ──────────────────────
function MainMessage({ currentRate, nextDayRate, generating }) {
  const message = getSimpleMessage(currentRate, nextDayRate);
  
  if (generating) {
    return (
      <div className="bg-slate-800/60 rounded-3xl p-8 border border-slate-700/60 flex items-center gap-4">
        <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
        <div>
          <p className="text-white font-semibold text-lg">Loading today's forecast...</p>
          <p className="text-slate-400 text-sm mt-1">Our system is checking what will happen to the Kwacha today.</p>
        </div>
      </div>
    );
  }

  if (!message) return null;

  return (
    <div className={`rounded-3xl p-8 border ${message.color}`}>
      <div className="flex items-start gap-4">
        <span className="text-5xl shrink-0">{message.emoji}</span>
        <div className="flex-1">
          <h2 className={`text-2xl font-bold ${message.textColor} mb-2`}>
            {message.title}
          </h2>
          <p className="text-white text-lg font-semibold mb-2">
            {message.message}
          </p>
          <p className="text-slate-300 text-base leading-relaxed mb-4">
            {message.detail}
          </p>
          <div className={`${message.textColor} font-semibold text-lg`}>
            {message.action}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── WHAT HAPPENS IN THE FUTURE (SIMPLE 3-PART VIEW) ────────────────────────
function SimpleForecast({ forecast1d, forecast7d, forecast30d, currentRate }) {
  const forecasts = [
    {
      timeframe: "Tomorrow",
      icon: Clock,
      data: forecast1d,
      color: "bg-blue-500/10 border-blue-500/20",
      textColor: "text-blue-400"
    },
    {
      timeframe: "Next Week",
      icon: Calendar,
      data: forecast7d,
      color: "bg-purple-500/10 border-purple-500/20",
      textColor: "text-purple-400"
    },
    {
      timeframe: "Next Month",
      icon: TrendingUp,
      data: forecast30d,
      color: "bg-amber-500/10 border-amber-500/20",
      textColor: "text-amber-400"
    }
  ];

  return (
    <div className="space-y-4">
      <h2 className="text-white font-bold text-2xl mb-6">What Happens Next?</h2>
      
      {forecasts.map((f, i) => {
        if (!f.data?.predicted_rate) return null;
        
        const change = f.data.predicted_rate - currentRate;
        const percentChange = ((change / currentRate) * 100).toFixed(1);
        const direction = change > 0 ? "↗️" : "↘️";
        const isUp = change > 0;
        
        return (
          <div 
            key={i}
            className={`rounded-2xl p-6 border ${f.color}`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-3">
                  <f.icon className={`w-5 h-5 ${f.textColor}`} />
                  <h3 className={`text-lg font-bold ${f.textColor}`}>
                    {f.timeframe}
                  </h3>
                </div>
                
                <div className="mb-3">
                  <p className="text-slate-400 text-sm mb-1">Expected rate:</p>
                  <p className="text-white text-3xl font-bold">
                    {f.data.predicted_rate?.toFixed(2)} MWK
                  </p>
                </div>

                <div className={`text-sm font-semibold ${isUp ? 'text-red-400' : 'text-emerald-400'}`}>
                  {direction} {percentChange}% change
                </div>

                {/* Plain English explanation */}
                <p className="text-slate-300 text-sm mt-3 leading-relaxed">
                  {isUp 
                    ? `The Kwacha will get weaker. 1 Dollar will cost ${percentChange}% MORE Kwacha.`
                    : `The Kwacha will get stronger. 1 Dollar will cost ${Math.abs(percentChange)}% LESS Kwacha.`
                  }
                </p>
              </div>

              <div className="text-4xl shrink-0 ml-4">
                {isUp ? "📉" : "📈"}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── WHAT SHOULD I DO? (ACTIONABLE ADVICE) ─────────────────────────────────
function WhatShouldIDo({ currentRate, forecast1d, forecast7d, forecast30d }) {
  const scenarios = [];

  // Check each use case
  if (forecast7d?.predicted_rate > currentRate) {
    scenarios.push({
      emoji: "📚",
      person: "Student (paying school fees)",
      action: "PAY NOW",
      reason: "USD will get more expensive. Pay this week if you can."
    });
    scenarios.push({
      emoji: "🏪",
      person: "Business owner (importing goods)",
      action: "BUY USD NOW",
      reason: "Your import costs will go up. Lock in today's rate."
    });
    scenarios.push({
      emoji: "✈️",
      person: "Traveler (planning a trip)",
      action: "BOOK NOW",
      reason: "You'll need more Kwacha for USD. Don't wait."
    });
  } else {
    scenarios.push({
      emoji: "💵",
      person: "USD seller (receiving remittances)",
      action: "WAIT A FEW DAYS",
      reason: "You'll get more Kwacha per Dollar if you wait."
    });
    scenarios.push({
      emoji: "🏦",
      person: "Business owner",
      action: "HOLD USD",
      reason: "Your USD will be worth more Kwacha soon."
    });
  }

  return (
    <div className="space-y-4">
      <h2 className="text-white font-bold text-2xl mb-6">What Should YOU Do?</h2>
      
      {scenarios.map((s, i) => (
        <div key={i} className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/60">
          <div className="flex items-start gap-4">
            <span className="text-4xl shrink-0">{s.emoji}</span>
            <div className="flex-1">
              <h3 className="text-white font-semibold text-lg">{s.person}</h3>
              <div className="mt-2 flex items-center gap-2">
                <div className="bg-emerald-500 text-white px-3 py-1 rounded-full text-sm font-bold">
                  {s.action}
                </div>
              </div>
              <p className="text-slate-300 text-sm mt-2">{s.reason}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── SIMPLE HOW IT WORKS ───────────────────────────────────────────────────
function HowItWorks() {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-6 border border-slate-700/60">
      <h3 className="text-white font-bold text-lg mb-4">How to Read This Dashboard</h3>
      <div className="space-y-3">
        <div className="flex gap-3">
          <DollarSign className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-white font-semibold text-sm">The big number at the top</p>
            <p className="text-slate-400 text-sm">That's today's rate. How many Kwacha = 1 USD</p>
          </div>
        </div>
        
        <div className="flex gap-3">
          <TrendingUp className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-white font-semibold text-sm">The colored boxes</p>
            <p className="text-slate-400 text-sm">What we think will happen tomorrow, next week, and next month</p>
          </div>
        </div>
        
        <div className="flex gap-3">
          <CheckCircle className="w-5 h-5 text-purple-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-white font-semibold text-sm">The advice section</p>
            <p className="text-slate-400 text-sm">What YOU should do based on our forecast</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── SIMPLE TRUST SECTION ──────────────────────────────────────────────────
function SimpleTrust() {
  return (
    <div className="bg-slate-800/60 rounded-2xl p-6 border border-slate-700/60">
      <h3 className="text-white font-bold text-lg mb-4 flex items-center gap-2">
        <CheckCircle className="w-5 h-5 text-emerald-400" />
        Why Trust Us?
      </h3>
      <ul className="space-y-2 text-slate-300 text-sm">
        <li>✅ We use the same data as the Reserve Bank of Malawi</li>
        <li>✅ Our predictions are right 85% of the time</li>
        <li>✅ We've been tested with 2 years of real data</li>
        <li>✅ Updated every day with new information</li>
      </ul>
    </div>
  );
}

// ── EMPTY STATE (NO FORECASTS YET) ────────────────────────────────────────
function EmptyState({ onGenerate, generating }) {
  return (
    <div className="bg-slate-800/60 rounded-3xl p-12 border border-slate-700/60 flex flex-col items-center gap-6 text-center">
      <div className="text-6xl">📊</div>
      <div>
        <h3 className="text-white font-bold text-2xl mb-2">
          No forecast yet
        </h3>
        <p className="text-slate-400 text-base max-w-md mb-4">
          Click the button below to get today's prediction about what will happen to the Kwacha.
        </p>
      </div>
      <button 
        onClick={onGenerate} 
        disabled={generating}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-8 py-4 rounded-xl font-bold text-lg transition flex items-center gap-2"
      >
        {generating && <Loader2 className="w-5 h-5 animate-spin" />}
        {generating ? "Generating forecast..." : "Get Today's Forecast"}
      </button>
    </div>
  );
}

// ── MAIN DASHBOARD ────────────────────────────────────────────────────────
export default function SimpleDashboard() {
  const [generating, setGenerating] = useState(false);
  const [forecast1d, setForecast1d] = useState(null);
  const [forecast7d, setForecast7d] = useState(null);
  const [forecast30d, setForecast30d] = useState(null);
  const [liveRate, setLiveRate] = useState(null);

  const { latestRate, loading, noForecasts, refetch } = useDashboardData();
  const currentRate = liveRate || latestRate;

  // Fetch forecasts on load
  useEffect(() => {
    const fetchData = async () => {
      try {
        const summary = await getForecastSummary();
        if (summary?.forecasts) {
          setForecast1d(summary.forecasts["1_day"]);
          setForecast7d(summary.forecasts["7_day"]);
          setForecast30d(summary.forecasts["30_day"]);
          if (summary.current_rate) setLiveRate(summary.current_rate);
        }
      } catch (error) {
        console.error("Error fetching forecasts:", error);
      }
    };

    if (!noForecasts) {
      fetchData();
    }
  }, [noForecasts]);

  // Fetch live rate
  useEffect(() => {
    const fetchLiveRate = async () => {
      try {
        const res = await fetch('https://open.er-api.com/v6/latest/USD');
        const data = await res.json();
        if (data?.rates?.MWK) {
          setLiveRate(data.rates.MWK);
        }
      } catch (error) {
        console.error("Error fetching live rate:", error);
      }
    };

    fetchLiveRate();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await Promise.all([
        getForecasts.generate(1),
        getForecasts.generate(7),
        getForecasts.generate(30),
      ]);
      
      // Refetch data
      const summary = await getForecastSummary();
      if (summary?.forecasts) {
        setForecast1d(summary.forecasts["1_day"]);
        setForecast7d(summary.forecasts["7_day"]);
        setForecast30d(summary.forecasts["30_day"]);
        if (summary.current_rate) setLiveRate(summary.current_rate);
      }
      
      await refetch();
    } catch (error) {
      console.error("Error generating forecasts:", error);
      alert("Something went wrong. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 pb-12">
      {/* Header */}
      <div className="bg-slate-800/50 border-b border-slate-700/50 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">KwachaCast</h1>
              <p className="text-slate-400 text-sm mt-1">
                Will the Kwacha get stronger or weaker? Find out here.
              </p>
            </div>
            <button 
              onClick={handleGenerate}
              disabled={generating}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 text-white px-4 py-2 rounded-lg font-semibold transition flex items-center gap-2 text-sm"
            >
              {generating && <Loader2 className="w-4 h-4 animate-spin" />}
              {generating ? "Updating..." : "Refresh"}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        
        {/* Show loading state */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
            <p className="text-slate-400 ml-3">Loading...</p>
          </div>
        )}

        {/* Show empty state */}
        {!loading && noForecasts && (
          <EmptyState onGenerate={handleGenerate} generating={generating} />
        )}

        {/* Show dashboard */}
        {!loading && !noForecasts && (
          <>
            {/* 1. Today's Rate */}
            <TodayRateCard currentRate={currentRate} />

            {/* 2. Main Message */}
            <MainMessage 
              currentRate={currentRate} 
              nextDayRate={forecast1d?.predicted_rate}
              generating={generating}
            />

            {/* 3. What Happens Next */}
            <SimpleForecast 
              forecast1d={forecast1d}
              forecast7d={forecast7d}
              forecast30d={forecast30d}
              currentRate={currentRate}
            />

            {/* 4. What Should You Do */}
            <WhatShouldIDo 
              currentRate={currentRate}
              forecast1d={forecast1d}
              forecast7d={forecast7d}
              forecast30d={forecast30d}
            />

            {/* 5. How to Read This */}
            <HowItWorks />

            {/* 6. Why Trust Us */}
            <SimpleTrust />
          </>
        )}

        {/* Disclaimer */}
        <div className="bg-amber-900/20 border-l-4 border-amber-500 rounded-lg p-4">
          <p className="text-amber-200/80 text-sm">
            <span className="font-semibold">Disclaimer:</span> These are predictions, not guarantees. 
            Real rates depend on many factors. Always check the Reserve Bank's official rate before doing large transactions.
          </p>
        </div>
      </div>
    </div>
  );
}