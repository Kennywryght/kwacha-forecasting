import { useState, useEffect } from "react";
import {
  fetchForecasts,
  getLatestRate,
  getHistory,
  getModelMetrics,
  getAnomalies,
  getForecasts,
} from "../utils/api";

const normaliseModelForecast = (data) => {
  if (!data?.forecasts) return null;
  const dates = data.forecasts.map((f) => f.target_date);
  const prediction = data.forecasts.map((f) => f.predicted_rate);
  return {
    name: data.model_name,
    dates,
    prediction,
    lower: data.forecasts.map((f) => f.lower_bound),
    upper: data.forecasts.map((f) => f.upper_bound),
  };
};

export function useDashboardData(horizon) {
  const [latestRate, setLatestRate] = useState(null);
  const [forecasts, setForecasts] = useState(null);
  const [allForecasts, setAllForecasts] = useState([]);
  const [history, setHistory] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [forecast30d, setForecast30d] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function fetchAll() {
      setLoading(true);
      try {
        // Calculate date range for last 90 days
        const endDate = new Date().toISOString().slice(0, 10);
        const startDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
          .toISOString()
          .slice(0, 10);

        const [
          latestRateData,
          forecastAllData,
          historyData,
          metricsData,
          anomaliesData,
          forecast30dData,
        ] = await Promise.all([
          getLatestRate(),
          fetchForecasts(),
          getHistory(startDate, endDate),   // ← corrected
          getModelMetrics(),
          getAnomalies(),
          getForecasts.getLatest(30),
        ]);

        if (cancelled) return;

        setLatestRate(latestRateData);
        setMetrics(metricsData);
        setAnomalies(anomaliesData || []);
        setForecast30d(forecast30dData);

        const wantedModels = ["arima", "arimax", "ensemble"];
        const modelsList = [];
        let ensembleData = null;

        if (forecastAllData && typeof forecastAllData === "object") {
          Object.entries(forecastAllData).forEach(([key, model]) => {
            if (wantedModels.includes(key) && model?.forecasts) {
              const norm = normaliseModelForecast(model);
              if (key === "ensemble") {
                ensembleData = {
                  dates: norm.dates,
                  prediction: norm.prediction,
                  lower_80: norm.lower,
                  upper_80: norm.upper,
                };
              } else {
                modelsList.push({
                  name: model.model_name,
                  prediction: norm.prediction,
                  dates: norm.dates,
                });
              }
            }
          });

          if (!ensembleData && modelsList.length > 0) {
            const fallback = modelsList[0];
            ensembleData = {
              dates: fallback.dates,
              prediction: fallback.prediction,
              lower_80: [],
              upper_80: [],
            };
          }
        }

        setForecasts(ensembleData);
        setAllForecasts(modelsList);

        // History extraction (backend returns an object with a "data" array)
        let historyArray = [];
        if (Array.isArray(historyData)) {
          historyArray = historyData;
        } else if (historyData?.data) {
          historyArray = historyData.data;
        }
        setHistory(historyArray);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchAll();
    return () => { cancelled = true; };
  }, [horizon]);

  return {
    latestRate,
    forecasts,
    allForecasts,
    history,
    metrics,
    anomalies,
    loading,
    forecast30d,
  };
}