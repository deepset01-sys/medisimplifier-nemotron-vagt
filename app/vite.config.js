import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/v1': {
        target: 'https://port8000-n5qwhak1n451qq2.tunnel.applications.eu-north1.nebius.cloud',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
