import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard"  // SimpleDashboard;
import History from "./pages/History";
import Models from "./pages/Models";
import Home from "./pages/Home";
import About from "./pages/About";
import ApiDocs from "./pages/ApiDocs";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950 text-white">
        <Navbar />
        <main className="pb-12">
          <Routes>
            {/* USER-FACING PAGES */}
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/about" element={<About />} />
            
            {/* HIDDEN PAGES - accessible via direct URL for admin later */}
            <Route path="/models" element={<Models />} />
            <Route path="/api-docs" element={<ApiDocs />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}