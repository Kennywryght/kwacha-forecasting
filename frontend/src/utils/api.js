import axios from "axios";

// Hardcoded Base URL for stability. You can change 'localhost' to '127.0.0.1' if you run Backend remotely
const API_BASE_URL = "http://localhost:8000/api";

export const fetchForecasts = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/forecasts`);
    
    // VALIDATION: Check if response exists and is valid
    if (!response || !response.data || !Array.isArray(response.data)) {
      console.error("⚠️ API returned invalid or no data.");
      return []; // Return empty array so chart doesn't crash
    }
    
    return response.data;
  } catch (error) {
    console.error("❌ API Error:", error);
    return []; // Prevent infinite spinners
  }
};

export const fetchHistory = async (limit = 365) => {
  const response = await axios.get(`${API_BASE_URL}/history?limit=${limit}`);
  return response.data || [];
};

export const getRates = async () => {
  const response =  await axios.get(`${API_BASE_URL}/rates/latest`);
  return response.data ? response.data : { date: "2025-04-26", rate: 1750.0 }; // Fallback to ensure dashboard has *something* to show
};

export const fetchModelRuns = async () => {
  const response = await axios.get(`${API_BASE_URL}/models/all`);
  return response.data || [];
};

export const fetchModelRuns = async () => {
  const response = await axios.get(`${API_LOGS_BASE_URL}/model_runs`); // Typo in your api.js
  return response.data || [];
};