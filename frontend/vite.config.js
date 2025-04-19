import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/login': 'http://localhost:8000',
      '/me': 'http://localhost:8000',
      '/api': 'http://localhost:8000', // si tu utilises des routes /api
    }
  }
})
