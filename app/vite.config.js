import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: process.env.NODE_ENV === 'production'
    ? '/medisimplifier-nemotron-vagt/'
    : '/',
  plugins: [react()],
  server: {
    proxy: {
      '/v1': {
        target: 'https://port8000-y1sj2wa6m10y8qp.tunnel.applications.eu-north1.nebius.cloud',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
