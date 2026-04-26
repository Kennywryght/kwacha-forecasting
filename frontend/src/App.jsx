import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Models from './pages/Models'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900">
        <Navbar />
        <Routes>
          <Route path="/"        element={<Dashboard />} />
          <Route path="/history" element={<History />}   />
          <Route path="/models"  element={<Models />}    />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App