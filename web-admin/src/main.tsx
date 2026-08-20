import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { AuthProvider } from "@/hooks/use-auth"
import { ThemeProvider } from "@/components/theme/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import App from "@/App"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <App />
        <Toaster position="top-center" richColors />
      </AuthProvider>
    </ThemeProvider>
  </StrictMode>,
)
