import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom"
import AppLayout from "@/components/layout/AppLayout"
import LoginPage from "@/pages/LoginPage"
import DashboardPage from "@/pages/DashboardPage"
import ChatPage from "@/pages/ChatPage"
import NetworkPage from "@/pages/NetworkPage"
import TestPage from "@/pages/TestPage"
import SettingsPage from "@/pages/SettingsPage"
import LogsPage from "@/pages/LogsPage"

function NotFoundPage() {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-6">
      <div className="text-7xl font-bold text-muted-foreground/30">404</div>
      <p className="text-lg text-muted-foreground">页面不存在</p>
    </div>
  )
}

const router = createBrowserRouter([
  {
    path: "/admin/login",
    element: <LoginPage />,
  },
  {
    path: "/admin",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/admin/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "chat", element: <ChatPage /> },
      { path: "network", element: <NetworkPage /> },
      { path: "test", element: <TestPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "logs", element: <LogsPage /> },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
])

export default function App() {
  return <RouterProvider router={router} />
}
