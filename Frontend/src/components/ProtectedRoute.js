import { Navigate } from "react-router-dom";

/**
 * ProtectedRoute component
 * Uses session cookie as the single source of truth for authentication
 * No dependency on React state - backend session is the authority
 */
export default function ProtectedRoute({ children }) {
  // Check if session_id cookie exists
  const hasSessionCookie = () => {
    const cookies = document.cookie;
    console.log("🍪 All cookies:", cookies);
    
    const hasSession = cookies
      .split("; ")
      .some((row) => row.startsWith("session_id="));
    
    console.log("🔒 Has session cookie:", hasSession);
    return hasSession;
  };

  // If no session cookie, redirect to sign-in
  if (!hasSessionCookie()) {
    console.log("❌ No session cookie found, redirecting to sign-in");
    return <Navigate to="/signin" replace />;
  }

  // Session cookie exists - render the protected content
  console.log("✅ Session cookie valid, rendering protected content");
  return children;
}
