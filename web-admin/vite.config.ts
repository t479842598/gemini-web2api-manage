import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  base: "/admin",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/admin/api": "http://localhost:18081",
      "/v1": "http://localhost:18081",
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../gemini_web2api_manage/admin_static"),
    emptyOutDir: true,
  },
})
