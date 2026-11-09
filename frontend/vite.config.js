import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Send API calls to Django so the browser sees one site (cookies + CSRF just work).
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
