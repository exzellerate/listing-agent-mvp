import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    host: true, // Allow external access
    allowedHosts: [
      'listing-agent-ebay.loca.lt', // Localtunnel host for eBay OAuth
      'localhost',
      '127.0.0.1',
      'exzellerate.com'
    ]
  }
})
