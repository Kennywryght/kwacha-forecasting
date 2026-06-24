import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
// LanguageProvider removed

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* LanguageProvider removed */}
      <App />
    {/* /LanguageProvider */}
  </React.StrictMode>
)