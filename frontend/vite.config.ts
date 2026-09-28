import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

// https://vitejs.dev/config/
export default defineConfig({
  // basicSsl generates/serves a locally-trusted self-signed cert so Vite runs
  // on https://localhost:5173 — eBay's OAuth RuName only accepts https:// redirect URLs.
  plugins: [react(), basicSsl()],
  server: {
    port: 5173,
    strictPort: true,
    host: true, // Allow external access
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'exzellerate.com'
    ],
    // The dev server is https (see basicSsl above) but the backend is plain
    // http://localhost:8000 — browsers block that as mixed content. Proxying
    // here keeps every browser-visible request on the https origin; Vite
    // forwards to the backend itself (Node-to-Node, no browser involved).
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/uploads': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true }
    }
  }
})
