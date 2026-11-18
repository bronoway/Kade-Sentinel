import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev only: `npm run dev` forwards /api to the FastAPI backend, so the app never hardcodes an IP.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
