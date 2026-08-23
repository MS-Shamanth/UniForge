import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The built app is served by FastAPI from web/dist, so `base` stays root-relative.
// In dev, /api is proxied to the Python server so the console reads a real run.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
  },
})
