import { useState, useEffect, useCallback, useRef } from "react";
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
  return {
    name: data.model_name,
    dates: data.forecasts.map((f) => f.target_date),
    prediction: data.forecasts.map((f) => f.predicted_rate),
    lower: data.forecasts.map((f) => f.lower_bound),
    upper: data.forecasts.map((f) => f.upper_bound),
  };
};

// NEW: Fetch historical forecasts for Trust Chart
const fetchHistoricalForecasts = async () => {
  try {
    const endDate = new Date().toISOString().slice(0, 10);
    const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
      .toISOString().slice(0, 10);
    
    const API_BASE = import.meta.env.VITE_API_URL || 'https://kwachacast-api.onrender.com/api/v1';
    const url = `${API_BASE}/forecasts/historical?start_date=${startDate}&end_date=${endDate}&model=ensemble&horizon=7`;
    
    const res = await fetch(url);
    const data = await res.json();
    return data;
  } catch {
    return { forecast_dates: {} };
  }
};

export function useDashboardData(horizon = 7) {
  const [latestRate, setLatestRate] = useState(null);
  const [forecasts, setForecasts] = useState(null);
  const [allForecasts, setAllForecasts] = useState([]);
  const [history, setHistory] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [forecast30d, setForecast30d] = useState(null);
  const [isStale, setIsStale] = useState(false);
  const [forecastDate, setForecastDate] = useState(null);
  const [noForecasts, setNoForecasts] = useState(false);
  const [loadedModelNames, setLoadedModelNames] = useState([]);
  const [generationStatus, setGenerationStatus] = useState("idle");
  const [generationProgress, setGenerationProgress] = useState(0);
  const [historicalForecasts, setHistoricalForecasts] = useState(null); // NEW

  const isStaleRef = useRef(false);
  const pollingRef = useRef(null);
  const isMountedRef = useRef(true);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const processForecastData = useCallback((forecastAllData, loadedNames, statusData) => {
    const wantedModels = loadedNames.length > 0 ? loadedNames : ["arima", "prophet", "ensemble"];
    const modelsList = [];
    let ensembleData = null;

    if (forecastAllData && typeof forecastAllData === "object") {
      if (forecastAllData.status === "generating") {
        return { ensembleData: null, modelsList: [], noForecasts: true, isGenerating: true };
      }

      const modelsObj = forecastAllData.models || forecastAllData;
      
      if (Object.keys(modelsObj).length > 0) {
        Object.entries(modelsObj).forEach(([key, model]) => {
          if (!model?.forecasts) return;
          const norm = normaliseModelForecast(model);
          if (!norm) return;

          if (key === "ensemble") {
            ensembleData = {
              dates: norm.dates,
              prediction: norm.prediction,
              lower_80: norm.lower,
              upper_80: norm.upper,
            };
          } else if (wantedModels.includes(key)) {
            modelsList.push({
              name: model.model_name,
              prediction: norm.prediction,
              dates: norm.dates,
            });
          }
        });

        if (!ensembleData && modelsList.length > 0) {
          const fb = modelsList[0];
          ensembleData = {
            dates: fb.dates,
            prediction: fb.prediction,
            lower_80: [],
            upper_80: [],
          };
        }
      }
    }

    return {
      ensembleData,
      modelsList,
      noForecasts: !ensembleData && modelsList.length === 0,
      isGenerating: false,
    };
  }, []);

  const fetchAll = useCallback(async (skipGenerationCheck = false) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);

      const statusData = await getForecasts.getStatus(horizon);
      
      if (!isMountedRef.current) return;

      const loadedNames = statusData?.loaded_models ?? [];
      setLoadedModelNames(loadedNames);

      if (statusData?.status === "generating") {
        setGenerationStatus("generating");
        setGenerationProgress(statusData.generation_elapsed_seconds || 0);
        
        if (pollingRef.current) clearTimeout(pollingRef.current);
        pollingRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            fetchAll(true);
          }
        }, 2000);
        
        setLoading(false);
        return;
      }

      if (!statusData?.is_fresh && !skipGenerationCheck) {
        setGenerationStatus("starting_generation");
        
        try {
          const genResponse = await getForecasts.generate(horizon);
          
          if (genResponse?.status === "already_generating") {
            setGenerationStatus("generating");
            if (pollingRef.current) clearTimeout(pollingRef.current);
            pollingRef.current = setTimeout(() => {
              if (isMountedRef.current) fetchAll(true);
            }, 2000);
            setLoading(false);
            return;
          } else if (genResponse?.status === "already_fresh") {
            setGenerationStatus("ready");
          } else if (genResponse?.status === "generating") {
            setGenerationStatus("generating");
            if (pollingRef.current) clearTimeout(pollingRef.current);
            pollingRef.current = setTimeout(() => {
              if (isMountedRef.current) fetchAll(true);
            }, 2000);
            setLoading(false);
            return;
          }
        } catch (err) {
          console.error("Failed to trigger generation:", err);
        }
      } else {
        setGenerationStatus("ready");
      }

      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }

      const endDate = new Date().toISOString().slice(0, 10);
      const startDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
        .toISOString().slice(0, 10);

      const [
        latestRateData,
        forecastAllData,
        historyData,
        metricsData,
        forecast30dData,
        historicalData, // NEW
      ] = await Promise.all([
        getLatestRate().catch(() => null),
        fetchForecasts().catch(() => ({})),
        getHistory(startDate, endDate).catch(() => []),
        getModelMetrics().catch(() => []),
        getForecasts.getLatest(30).catch(() => null),
        fetchHistoricalForecasts().catch(() => ({ forecast_dates: {} })), // NEW
      ]);

      if (!isMountedRef.current) return;

      setLatestRate(latestRateData);
      setAnomalies([]);
      setForecast30d(forecast30dData);
      setHistoricalForecasts(historicalData); // NEW

      const filteredMetrics = Array.isArray(metricsData) 
        ? metricsData.filter(m => loadedNames.length === 0 || loadedNames.includes(m.model_name))
        : [];
      setMetrics(filteredMetrics);

      const isFresh = statusData?.is_fresh ?? false;
      setIsStale(!isFresh);
      isStaleRef.current = !isFresh;
      setForecastDate(statusData?.forecast_date ?? null);

      const { ensembleData, modelsList, noForecasts } = processForecastData(
        forecastAllData,
        loadedNames,
        statusData
      );

      setForecasts(ensembleData);
      setAllForecasts(modelsList);
      setNoForecasts(noForecasts);

      let historyArray = [];
      if (Array.isArray(historyData)) {
        historyArray = historyData;
      } else if (historyData?.data) {
        historyArray = historyData.data;
      } else if (historyData?.rates) {
        historyArray = historyData.rates;
      }
      setHistory(historyArray);

    } catch (err) {
      if (err.name !== 'AbortError' && err.name !== 'CanceledError') {
        console.error("Dashboard fetch error:", err);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [horizon, processForecastData]);

  useEffect(() => {
    if (isMountedRef.current) {
      fetchAll();
    }
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [fetchAll]);

  const generateForecasts = useCallback(async (h) => {
    try {
      setGenerationStatus("starting_generation");
      const response = await getForecasts.generate(h || horizon);
      
      if (response?.status === "generating" || response?.status === "already_generating") {
        setGenerationStatus("generating");
        if (pollingRef.current) clearTimeout(pollingRef.current);
        pollingRef.current = setTimeout(() => {
          if (isMountedRef.current) fetchAll(true);
        }, 2000);
      } else if (response?.status === "already_fresh") {
        await fetchAll(true);
      }
    } catch (err) {
      console.error("Failed to generate forecasts:", err);
      setGenerationStatus("error");
    }
  }, [horizon, fetchAll]);

  return {
    latestRate,
    forecasts,
    allForecasts,
    history,
    metrics,
    anomalies,
    loading,
    forecast30d,
    isStale,
    isStaleRef,
    forecastDate,
    noForecasts,
    loadedModelNames,
    generationStatus,
    generationProgress,
    historicalForecasts, // NEW
    refetch: fetchAll,
    generateForecasts,
  };
}