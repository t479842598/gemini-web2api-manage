import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  base: '/admin/',
  build: {
    outDir: fileURLToPath(new URL('../gemini_web2api/admin_static', import.meta.url)),
    emptyOutDir: true
  },
  server: {
    proxy: {
      '/admin/api': 'http://127.0.0.1:8081',
      '/v1': 'http://127.0.0.1:8081',
      '/v1beta': 'http://127.0.0.1:8081'
    }
  }
})
