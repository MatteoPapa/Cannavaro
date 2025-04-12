import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 7000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://backend:7001',
        changeOrigin: true,
        secure: false
      }
    }
  }
  ,
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
