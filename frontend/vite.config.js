import { defineConfig, searchForWorkspaceRoot } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig(({ command, mode }) => {
  const isProduction = command === 'serve';

  return {
    server: {
      strictPort: true, // Don't randomly try nearby ports
      port: isProduction ? 80 : 5173, // Frontend Port
      hmr: false, // Fast Refresh
    },
    
    // --- PROXY SETUP ---
    proxy: {
      enabled: true, // Enable Proxy for development
      origin: 'http://localhost:8000', // Target Backend API
    },
  };
});