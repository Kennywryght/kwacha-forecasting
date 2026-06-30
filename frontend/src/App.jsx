import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import Navbar from "./components/Navbar";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import Models from "./pages/Models";
import Home from "./pages/Home";
import About from "./pages/About";
import ApiDocs from "./pages/ApiDocs";
import AdminDashboard from "./pages/AdminDashboard";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-ink-950 text-stone-100">
        <Navbar />
        <main className="pb-12">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/about" element={<About />} />
            <Route path="/models" element={<Models />} />
            <Route path="/api-docs" element={<ApiDocs />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}