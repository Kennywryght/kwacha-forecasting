import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

export const getRates = {
  latest:  ()                          => api.get('/rates/latest'),
  history: (start, end)                => api.get('/rates/history', { params: { start, end } }),
  status:  ()                          => api.get('/rates/status'),
}

export const getForecasts = {
  latest:  (horizon = 7, model = 'ensemble') => api.get('/forecasts/latest', { params: { horizon, model } }),
  all:     (horizon = 7)                      => api.get('/forecasts/all',    { params: { horizon } }),
  generate:(horizon = 7)                      => api.post('/forecasts/generate', null, { params: { horizon } }),
}

export const getModels = {
  performance: () => api.get('/models/performance'),
}

export const getPipeline = {
  status:  () => api.get('/pipeline/status'),
  retrain: () => api.post('/pipeline/retrain'),
}

export default api