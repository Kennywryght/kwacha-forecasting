import { useState, useEffect } from "react";
import {
  fetchForecasts,
  getLatestRate,
  getHistory,
  getModelMetrics,
  getAnomalies,
  getForecasts
} from "../utils/api";

// ------- Legacy hook (unchanged) -------
export const useForecasts = (horizon = 7) => {
  const [forecasts, setForecasts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        console.log("📡 Fetching Live Forecasts from API...");
        const rawData = await fetchForecasts();

        if (!rawData || !Array.isArray(rawData)) {
          if (!cancelled) setForecasts([]);
          return;
        }
        const formatted = rawData.map((item) => ({
          date: item.target_date,
          rate: parseFloat(item.predicted_rate),
        }));
        if (!cancelled) setForecasts(formatted);
      } catch (err) {
        console.error("❌ Error in useForecasts:", err);
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => { cancelled = true; };
  }, [horizon]);

  return { forecasts, loading, error };
};

// ------- Normalisation helper -------
const normaliseModelForecast = (data) => {
  if (!data?.forecasts) return null;
  const dates = data.forecasts.map(f => f.target_date);
  const prediction = data.forecasts.map(f => f.predicted_rate);
  return {
    name: data.model_name,
    dates,
    prediction,
    lower: data.forecasts.map(f => f.lower_bound),
    upper: data.forecasts.map(f => f.upper_bound),
  };
};

// ------- Main Dashboard Hook -------
export function useDashboardData(horizon) {
  const [latestRate, setLatestRate] = useState(null);
  const [forecasts, setForecasts] = useState(null);       // ensemble normalised
  const [allForecasts, setAllForecasts] = useState([]);   // array of { name, prediction[] }
  const [history, setHistory] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function fetchAll() {
      setLoading(true);
      try {
        const [
          latestRateData,
          forecastAllData,      // the object from /forecasts/all
          historyData,
          metricsData,
          anomaliesData
        ] = await Promise.all([
          getLatestRate(),
          fetchForecasts(),      // returns { arima: {...}, arimax: {...}, ensemble: {...} }
          getHistory(90),
          getModelMetrics(),     // already filtered and mapped
          getAnomalies()
        ]);

        if (cancelled) return;

        // Latest rate
        setLatestRate(latestRateData);

        // Process forecast models – keep only ARIMA, ARIMAX, Ensemble
        const wantedModels = ['arima', 'arimax', 'ensemble'];
        const modelsList = [];
        let ensembleData = null;

        if (forecastAllData && typeof forecastAllData === 'object') {
          Object.entries(forecastAllData).forEach(([key, model]) => {
            if (wantedModels.includes(key) && model?.forecasts) {
              const norm = normaliseModelForecast(model);
              if (key === 'ensemble') {
                ensembleData = {
                  dates: norm.dates,
                  prediction: norm.prediction,
                  lower_80: norm.lower,
                  upper_80: norm.upper
                };
              } else {
                modelsList.push({
                  name: model.model_name,
                  prediction: norm.prediction,
                  dates: norm.dates
                });
              }
            }
          });

          // If no ensemble, fallback to first available model
          if (!ensembleData && modelsList.length > 0) {
            const fallback = modelsList[0];
            ensembleData = {
              dates: fallback.dates,
              prediction: fallback.prediction,
              lower_80: [],
              upper_80: []
            };
          }
        }

        setForecasts(ensembleData);
        setAllForecasts(modelsList);

        // ---------- HISTORY FIX ----------
        // The API returns an object with a "data" key containing the array of rates
        let historyArray = [];
        if (Array.isArray(historyData)) {
          historyArray = historyData;
        } else if (historyData && typeof historyData === 'object' && historyData.data) {
          historyArray = historyData.data;
        }
        console.log('History array extracted:', historyArray.length, 'points');
        setHistory(historyArray);

        setMetrics(metricsData);
        setAnomalies(anomaliesData || []);

      } catch (err) {
        console.error('Dashboard fetch error:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchAll();
    return () => { cancelled = true; };
  }, [horizon]);

  return { latestRate, forecasts, allForecasts, history, metrics, anomalies, loading };
}