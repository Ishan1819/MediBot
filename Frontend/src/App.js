"use client"

import { useState, useEffect } from "react"
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom"
import ChatInterface from "./components/chat-interface"
import HomePage from "./components/home-page"
import SignIn from "./components/sign-in"
import SignUp from "./components/sign-up"
import ProtectedRoute from "./components/ProtectedRoute"
import { ThemeProvider } from "./components/theme-provider"
import "./index.css"

function App() {
  const [user, setUser] = useState(null)

  // Helper function to check if session cookie exists
  const hasSessionCookie = () => {
    return document.cookie.split("; ").some((row) => row.startsWith("session_id="));
  };

  // Check authentication on app mount and sync user data
  useEffect(() => {
    if (hasSessionCookie()) {
      const email = localStorage.getItem("email");
      if (email) {
        setUser({ email });
      }
    }
  }, [])

  const handleLogin = (userData) => {
    console.log("Login handler called with:", userData);
    setUser(userData);
    // Note: isLoggedIn state removed - session cookie is the source of truth
  }

  const handleLogout = async () => {
    try {
      // Call backend logout to invalidate session
      await fetch("http://localhost:8002/api/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      // Clear localStorage
      localStorage.removeItem("user_id");
      localStorage.removeItem("email");
      // Session cookie is cleared by backend (httpOnly)
      setUser(null);
    }
  }

  return (
    <ThemeProvider defaultTheme="light" attribute="class">
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/signin" element={<SignIn onLogin={handleLogin} />} />
          <Route path="/signup" element={<SignUp onLogin={handleLogin} />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatInterface handleLogout={handleLogout} />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  )
}

export default App

