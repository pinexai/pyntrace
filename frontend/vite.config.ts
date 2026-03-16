import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/static/app/',
  build: {
    outDir: '../pyntrace/server/static/app',
    emptyOutDir: false,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:7234', changeOrigin: true },
      '/ws':  { target: 'ws://localhost:7234',   ws: true },
    },
  },
})
