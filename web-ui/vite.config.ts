import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    {
      name: 'static-html-routes',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url?.startsWith('/proteodies')) {
            const filePath = path.resolve(__dirname, 'public/proteodies/index.html')
            res.setHeader('Content-Type', 'text/html')
            res.end(fs.readFileSync(filePath))
            return
          }
          next()
        })
      }
    }
  ],
  server: {
    port: 3000,
    host: true,
    allowedHosts: ['calounette.ddns.net', 'brunold.ddns.net'],
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: 'ws://127.0.0.1:8001',
        ws: true,
        changeOrigin: true
      }
    }
  }
})
