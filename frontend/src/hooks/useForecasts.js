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

  // Refs to prevent stale closures and race conditions
  const isStaleRef = useRef(false);
  const pollingRef = useRef(null);
  const isMountedRef = useRef(true);
  const abortControllerRef = useRef(null);

  // Cleanup on unmount
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
      // Handle case where backend returns { status: "generating", ... }
      if (forecastAllData.status === "generating") {
        return { ensembleData: null, modelsList: [], noForecasts: true, isGenerating: true };
      }

      // Handle nested models object
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

        // Fallback: if no ensemble, use first model
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
    // Cancel any pending requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      setLoading(true);

      // Step 1: Always check status first (fast, lightweight)
      const statusData = await getForecasts.getStatus(horizon);
      
      if (!isMountedRef.current) return;

      const loadedNames = statusData?.loaded_models ?? [];
      setLoadedModelNames(loadedNames);

      // Step 2: Handle different states
      if (statusData?.status === "generating") {
        setGenerationStatus("generating");
        setGenerationProgress(statusData.generation_elapsed_seconds || 0);
        
        // Poll every 2 seconds until generation completes
        if (pollingRef.current) clearTimeout(pollingRef.current);
        pollingRef.current = setTimeout(() => {
          if (isMountedRef.current) {
            fetchAll(true);
          }
        }, 2000);
        
        setLoading(false);
        return;
      }

      // Step 3: If not fresh and no generation in progress, trigger generation
      if (!statusData?.is_fresh && !skipGenerationCheck) {
        setGenerationStatus("starting_generation");
        
        try {
          const genResponse = await getForecasts.generate(horizon);
          
          if (genResponse?.status === "already_generating") {
            // Another client is generating, start polling
            setGenerationStatus("generating");
            if (pollingRef.current) clearTimeout(pollingRef.current);
            pollingRef.current = setTimeout(() => {
              if (isMountedRef.current) fetchAll(true);
            }, 2000);
            setLoading(false);
            return;
          } else if (genResponse?.status === "already_fresh") {
            // Already fresh, proceed to fetch data
            setGenerationStatus("ready");
          } else if (genResponse?.status === "generating") {
            // Generation started, poll for completion
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
          // Continue anyway - might have stale data to show
        }
      } else {
        setGenerationStatus("ready");
      }

      // Clear polling if we're proceeding to fetch
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }

      // Step 4: Fetch all data in parallel (but only if ready)
      const endDate = new Date().toISOString().slice(0, 10);
      const startDate = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
        .toISOString().slice(0, 10);

      const [
        latestRateData,
        forecastAllData,
        historyData,
        metricsData,
        forecast30dData,
      ] = await Promise.all([
        getLatestRate().catch(err => {
          console.warn("Failed to fetch latest rate:", err);
          return null;
        }),
        fetchForecasts().catch(err => {
          console.warn("Failed to fetch forecasts:", err);
          return {};
        }),
        getHistory(startDate, endDate).catch(err => {
          console.warn("Failed to fetch history:", err);
          return [];
        }),
        getModelMetrics().catch(err => {
          console.warn("Failed to fetch metrics:", err);
          return [];
        }),
        getForecasts.getLatest(30).catch(err => {
          console.warn("Failed to fetch 30d forecast:", err);
          return null;
        }),
      ]);

      if (!isMountedRef.current) return;

      // Process results
      setLatestRate(latestRateData);
      setAnomalies([]);
      setForecast30d(forecast30dData);

      // Filter metrics to only loaded models
      const filteredMetrics = Array.isArray(metricsData) 
        ? metricsData.filter(m => loadedNames.length === 0 || loadedNames.includes(m.model_name))
        : [];
      setMetrics(filteredMetrics);

      // Stale check
      const isFresh = statusData?.is_fresh ?? false;
      setIsStale(!isFresh);
      isStaleRef.current = !isFresh;
      setForecastDate(statusData?.forecast_date ?? null);

      // Process forecast data
      const { ensembleData, modelsList, noForecasts } = processForecastData(
        forecastAllData,
        loadedNames,
        statusData
      );

      setForecasts(ensembleData);
      setAllForecasts(modelsList);
      setNoForecasts(noForecasts);

      // Process history data
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

  // Initial fetch on mount or horizon change
  useEffect(() => {
    if (isMountedRef.current) {
      fetchAll();
    }
    
    // Cleanup polling on dependency change
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [fetchAll]);

  // Manual generation trigger
  const generateForecasts = useCallback(async (h) => {
    try {
      setGenerationStatus("starting_generation");
      const response = await getForecasts.generate(h || horizon);
      
      if (response?.status === "generating" || response?.status === "already_generating") {
        setGenerationStatus("generating");
        // Start polling
        if (pollingRef.current) clearTimeout(pollingRef.current);
        pollingRef.current = setTimeout(() => {
          if (isMountedRef.current) fetchAll(true);
        }, 2000);
      } else if (response?.status === "already_fresh") {
        // Just fetch the data
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
    refetch: fetchAll,
    generateForecasts,
  };
}