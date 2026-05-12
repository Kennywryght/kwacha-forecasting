import React from 'react'
import Navbar from '../components/Navbar'

export default function MainLayout({ children }) {
  return (
    <div className="min-h-screen bg-slate-900 text-white flex flex-col">

      {/* NAVBAR */}
      <Navbar />

      {/* PAGE CONTENT WRAPPER */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
        {children}
      </main>

    </div>
  )
}