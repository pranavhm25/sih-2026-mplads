import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev ports: frontend 5317, backend 8317 (host ports also used by Docker).
// The dev server proxies /api to the backend so components never need the
// backend origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5317,
    proxy: {
      '/api': {
        target: 'http://localhost:8317',
        changeOrigin: true,
      },
    },
  },
})
