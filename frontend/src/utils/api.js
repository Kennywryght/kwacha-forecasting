import axios from "axios";

const API_BASE = "/api/v1";

// ---------- Helper to normalise forecast object ----------
const normaliseForecast = (data) => {
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

// ---------- Fetch all forecasts (used by dashboard hook) ----------
export const fetchForecasts = async () => {
  try {
    const res = await axios.get(`${API_BASE}/forecasts/all`);
    return res.data || {};
  } catch (error) {
    console.error("❌ fetchForecasts error:", error);
    return {};
  }
};

// ---------- Rate History ----------
export const fetchHistory = async (start, end, limit = 365) => {
  const params = {};
  if (start) params.start = start;
  if (end) params.end = end;
  params.limit = limit;
  const res = await axios.get(`${API_BASE}/rates/history`, { params });
  return res.data || [];
};
export const getHistory = fetchHistory;

// ---------- Latest Rate ----------
export const getLatestRate = async () => {
  const res = await axios.get(`${API_BASE}/rates/latest`);
  return res.data || { date: new Date().toISOString().slice(0, 10), rate: 1750.0 };
};

// ---------- Model Performance ----------
export const fetchModelRuns = async () => {
  const res = await axios.get(`${API_BASE}/models/performance`);
  const data = res.data || {};
  const allModels = data.models || [];
  const wanted = ['arima', 'arimax', 'ensemble'];
  const filtered = allModels.filter(m => wanted.includes(m.model_name));
  return filtered.map(m => ({
    ...m,
    r2: m.r_squared,
    model_name: m.model_name,
    rmse: m.rmse,
    mae: m.mae,
    mape: m.mape
  }));
};
export const getModels = fetchModelRuns;
export const getModelMetrics = fetchModelRuns;

// ---------- Pipeline Status ----------
export const getPipeline = async () => {
  const res = await axios.get(`${API_BASE}/pipeline/status`);
  return res.data || { status: "unknown" };
};

// ---------- Forecast Generation & Latest (single model) ----------
export const getForecasts = {
  getLatest: async (horizon = 7) => {
    const res = await axios.get(`${API_BASE}/forecasts/latest`, {
      params: { horizon, model: 'ensemble' }
    });
    return normaliseForecast(res.data);
  },
  generate: async (horizon = 7) => {
    const res = await axios.post(`${API_BASE}/forecasts/generate`, null, {
      params: { horizon }
    });
    return res.data;
  }
};

// ---------- Anomalies (placeholder) ----------
export const getAnomalies = async () => {
  return [];
};

// Aliases
export const getRates = getLatestRate;
export const fetchHistoryData = fetchHistory;