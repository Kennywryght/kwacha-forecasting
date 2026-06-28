import axios from "axios";
import { getApiUrl } from "../config";

const API_BASE = `${getApiUrl()}/api/v1`;

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 502) {
      console.warn("Backend temporarily unavailable (502)");
    }
    return Promise.reject(error);
  }
);

const normaliseForecast = (data) => {
  if (!data?.forecasts) return null;
  return {
    name: data.model_name,
    dates: data.forecasts.map(f => f.target_date),
    prediction: data.forecasts.map(f => f.predicted_rate),
    lower_80: data.forecasts.map(f => f.lower_bound),
    upper_80: data.forecasts.map(f => f.upper_bound),
    is_stale: data.is_stale ?? false,
    forecast_date: data.forecast_date ?? null,
  };
};

async function withRetry(fn, maxRetries = 2, delay = 2000) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const isTransient = error.response?.status === 502 || error.response?.status === 503 || error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK';
      if (isTransient && attempt < maxRetries) {
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      throw error;
    }
  }
}

export const fetchForecasts = async () => {
  try {
    const res = await withRetry(() => api.get(`/forecasts/all`));
    return res.data || {};
  } catch { return {}; }
};

export const fetchHistory = async (start, end, limit = 365) => {
  try {
    const params = { limit };
    if (start) params.start = start;
    if (end) params.end = end;
    const res = await withRetry(() => api.get(`/rates/history`, { params }));
    return res.data || [];
  } catch { return []; }
};

export const getHistory = fetchHistory;

export const getLatestRate = async () => {
  try {
    const res = await withRetry(() => api.get(`/rates/latest`));
    return res.data || null;
  } catch { return null; }
};

export const fetchModelRuns = async () => {
  try {
    const res = await withRetry(() => api.get(`/models/performance`));
    const data = res.data || {};
    return (data.models || []).map(m => ({
      ...m, r2: m.r_squared, model_name: m.model_name, rmse: m.rmse, mae: m.mae, mape: m.mape,
    }));
  } catch { return []; }
};

export const getModelMetrics = fetchModelRuns;

// ── Dedicated Horizon Endpoints ──────────────────────────────────────────
export const get1DayForecast = async () => {
  try {
    const res = await api.get('/forecasts/1-day');
    return res.data;
  } catch { return null; }
};

export const get7DayForecast = async () => {
  try {
    const res = await api.get('/forecasts/7-day');
    return res.data;
  } catch { return null; }
};

export const get30DayForecast = async () => {
  try {
    const res = await api.get('/forecasts/30-day');
    return res.data;
  } catch { return null; }
};

export const getForecastSummary = async () => {
  try {
    const res = await api.get('/forecasts/summary');
    return res.data;
  } catch { return null; }
};

export const getForecasts = {
  getLatest: async (horizon = 7) => {
    try {
      const res = await withRetry(() => api.get(`/forecasts/latest`, { params: { horizon, model: 'ensemble' } }));
      return normaliseForecast(res.data);
    } catch (error) {
      if (error?.response?.status === 404) return null;
      return null;
    }
  },
  generate: async (horizon = 7) => {
    try {
      const res = await api.post(`/forecasts/generate`, null, { params: { horizon } });
      return res.data;
    } catch (error) { throw error; }
  },
  getStatus: async (horizon = 7) => {
    try {
      const res = await api.get(`/forecasts/status`, { params: { horizon } });
      return res.data;
    } catch {
      return { is_fresh: false, status: "error", loaded_models: [] };
    }
  },
  retrain: async () => {
    try {
      const res = await api.post(`/forecasts/retrain`);
      return res.data;
    } catch (error) { throw error; }
  }
};

export const getAnomalies = async () => [];
export const getRates = getLatestRate;
export const fetchHistoryData = fetchHistory;