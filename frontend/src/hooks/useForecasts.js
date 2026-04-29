import { useState, useEffect } from "react";
import { fetchForecasts } from "../utils/api"; // Import from utils/api.js

export const useForecasts = (horizon = 7) => {
  const [forecasts, setForecasts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        console.log("📡 Fetching Live Forecasts from API...");
        const rawData = await fetchForecasts();
        
        // VALIDATION: Check raw data
        if (!rawData || !Array.isArray(rawData)) {
            console.warn("⚠️ API returned invalid format (expected Array).");
          setForecasts([]); // Use empty list
          return;
        }

        if (rawData.length === 0) {
          console.warn("⚠️ API returned empty array.");
          setForecasts([]);
          return;
        }

        console.log(`📊 Raw API Data (Sample):`, rawData[0]);

        // MAPPING: Map DB response to Chart Format
        const formattedData = rawData.map((item) => ({
          date: item.target_date, // Must match YYYY-MM-DD string from Backend
          rate: parseFloat(item.predicted_rate),
        }));

        console.log("✅ Formatted Chart Data:", formattedData);
        setForecasts(formattedData);

      } catch (err) {
        console.error("❌ Error in useForecasts:", err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

  //  load when hook is called (Dashboard mount, refresh)
  fetchData();
  }, [horizon, fetchData]);

  return { forecasts, loading, error };
};