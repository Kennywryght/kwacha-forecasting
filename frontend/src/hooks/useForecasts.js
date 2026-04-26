import { useState, useEffect } from 'react'
import { getRates, getForecasts, getModels } from '../utils/api'

export function useDashboardData(horizon = 7) {
  const [latestRate,  setLatestRate]  = useState(null)
  const [forecasts,   setForecasts]   = useState(null)
  const [allForecasts,setAllForecasts]= useState(null)
  const [history,     setHistory]     = useState(null)
  const [metrics,     setMetrics]     = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState(null)

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true)
      setError(null)
      try {
        const [rateRes, forecastRes, allForecastRes, histRes, metricsRes] = await Promise.allSettled([
          getRates.latest(),
          getForecasts.latest(horizon, 'ensemble'),
          getForecasts.all(horizon),
          getRates.history(),
          getModels.performance(),
        ])

        if (rateRes.status === 'fulfilled')       setLatestRate(rateRes.value.data)
        if (forecastRes.status === 'fulfilled')   setForecasts(forecastRes.value.data)
        if (allForecastRes.status === 'fulfilled') setAllForecasts(allForecastRes.value.data)
        if (histRes.status === 'fulfilled')       setHistory(histRes.value.data)
        if (metricsRes.status === 'fulfilled')    setMetrics(metricsRes.value.data)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [horizon])

  return { latestRate, forecasts, allForecasts, history, metrics, loading, error }
}