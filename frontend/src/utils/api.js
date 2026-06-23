import axios from "axios";
import { getApiUrl } from "../config";

const API_BASE = `${getApiUrl()}/api/v1`;

// ── Axios instance with retry logic ────────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000, // 10 second timeout
});

// Response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 502) {
      console.warn("⚠️ Backend temporarily unavailable (502) - will retry");
    }
    return Promise.reject(error);
  }
);

const normaliseForecast = (data) => {
  if (!data?.forecasts) return null;
  return {
    name:          data.model_name,
    dates:         data.forecasts.map(f => f.target_date),
    prediction:    data.forecasts.map(f => f.predicted_rate),
    lower_80:      data.forecasts.map(f => f.lower_bound),
    upper_80:      data.forecasts.map(f => f.upper_bound),
    is_stale:      data.is_stale ?? false,
    forecast_date: data.forecast_date ?? null,
  };
};

// ── Retry wrapper for transient failures ───────────────────────────────────
async function withRetry(fn, maxRetries = 3, delay = 2000) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      const isTransient = 
        error.response?.status === 502 || 
        error.response?.status === 503 ||
        error.code === 'ECONNABORTED' ||
        error.code === 'ERR_NETWORK';
      
      if (isTransient && attempt < maxRetries) {
        console.warn(`Retry ${attempt}/${maxRetries} after ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      throw error;
    }
  }
}

// ── API Functions ──────────────────────────────────────────────────────────

export const fetchForecasts = async () => {
  try {
    const res = await withRetry(() => 
      api.get(`/forecasts/all`)
    );
    return res.data || {};
  } catch (error) {
    console.error("❌ fetchForecasts error:", error);
    return {};
  }
};

export const fetchHistory = async (start, end, limit = 365) => {
  try {
    const params = {};
    if (start) params.start = start;
    if (end)   params.end   = end;
    params.limit = limit;
    const res = await withRetry(() => 
      api.get(`/rates/history`, { params })
    );
    return res.data || [];
  } catch (error) {
    console.error("❌ fetchHistory error:", error);
    return [];
  }
};

export const getHistory = fetchHistory;

export const getLatestRate = async () => {
  try {
    const res = await withRetry(() => 
      api.get(`/rates/latest`)
    );
    return res.data || null;
  } catch (error) {
    console.error("❌ getLatestRate error:", error);
    return null;
  }
};

export const fetchModelRuns = async () => {
  try {
    const res = await withRetry(() => 
      api.get(`/models/performance`)
    );
    const data = res.data || {};
    const allModels = data.models || [];
    return allModels.map(m => ({
      ...m,
      r2:         m.r_squared,
      model_name: m.model_name,
      rmse:       m.rmse,
      mae:        m.mae,
      mape:       m.mape,
    }));
  } catch (error) {
    console.error("❌ fetchModelRuns error:", error);
    return [];
  }
};

export const getModels       = fetchModelRuns;
export const getModelMetrics = fetchModelRuns;

export const getPipeline = async () => {
  try {
    const res = await withRetry(() => 
      api.get(`/pipeline/status`)
    );
    return res.data || { status: "unknown" };
  } catch (error) {
    console.error("❌ getPipeline error:", error);
    return { status: "unknown" };
  }
};

// ── Forecast-specific API ──────────────────────────────────────────────────

export const getForecasts = {
  getLatest: async (horizon = 7) => {
    try {
      const res = await withRetry(() => 
        api.get(`/forecasts/latest`, {
          params: { horizon, model: 'ensemble' },
        })
      );
      return normaliseForecast(res.data);
    } catch (error) {
      if (error?.response?.status === 404) return null;
      console.error("❌ getLatest error:", error);
      return null;
    }
  },
  
  generate: async (horizon = 7) => {
    try {
      const res = await api.post(`/forecasts/generate`, null, {
        params: { horizon },
      });
      return res.data;
    } catch (error) {
      console.error("❌ generate error:", error);
      throw error;
    }
  },
  
  getStatus: async (horizon = 7) => {
    try {
      const res = await api.get(`/forecasts/status`, {
        params: { horizon },
      });
      return res.data;
    } catch (error) {
      if (error.response?.status !== 502) {
        console.error("❌ getStatus error:", error);
      }
      return { 
        is_fresh: false, 
        status: "error",
        loaded_models: [],
        message: "Status check failed" 
      };
    }
  },

  retrain: async () => {
    try {
      const res = await api.post(`/forecasts/retrain`);
      return res.data;
    } catch (error) {
      console.error("❌ retrain error:", error);
      throw error;
    }
  }
};

export const getAnomalies = async () => [];

export const getRates         = getLatestRate;
export const fetchHistoryData = fetchHistory;