// frontend/src/config.js
const config = {
  API_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  PRODUCTION_API_URL: 'https://kwachacast-api.onrender.com',
};

export const getApiUrl = () => {
  if (import.meta.env.PROD) {
    return config.PRODUCTION_API_URL;
  }
  return config.API_URL;
};

export default config;
