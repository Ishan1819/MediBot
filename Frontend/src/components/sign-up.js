"use client";

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ArrowLeft } from "lucide-react";

export default function SignUp({ onLogin }) {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear password error when user types in either password field
    if (name === "password" || name === "confirmPassword") {
      setPasswordError("");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      setPasswordError("Passwords do not match");
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8002/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // Required to receive and send cookies
        body: JSON.stringify({
          name: formData.name,
          email: formData.email,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        setPasswordError(errData.detail || "Signup failed");
        throw new Error(errData.detail || "Signup failed");
      }

      const result = await response.json();
      
      // After successful signup, redirect to sign-in page
      // User needs to log in to create a session
      navigate("/signin");
    } catch (error) {
      console.error("Signup error:", error);
      // Error is already displayed via setPasswordError
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate("/")}
            className="back-button"
          >
            <ArrowLeft className="icon" />
          </Button>
          <h1 className="auth-title">
            Create your medi<span className="text-sky-500 font-bold">BOT</span>{" "}
            account
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="name">Full Name</label>
            <Input
              id="name"
              name="name"
              type="text"
              value={formData.name}
              onChange={handleChange}
              required
              placeholder="Enter your full name"
              className="auth-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <Input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              required
              placeholder="Enter your email"
              className="auth-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <Input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              required
              placeholder="Create a password"
              className="auth-input"
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <Input
              id="confirmPassword"
              name="confirmPassword"
              type="password"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              placeholder="Confirm your password"
              className={`auth-input ${passwordError ? "error" : ""}`}
            />
            {passwordError && <p className="error-message">{passwordError}</p>}
          </div>

          <div className="terms-privacy">
            <p>
              By signing up, you agree to our{" "}
              <a href="#" className="terms-link">
                Terms of Service
              </a>{" "}
              and{" "}
              <a href="#" className="privacy-link">
                Privacy Policy
              </a>
              .
            </p>
          </div>

          <Button
            type="submit"
            className="auth-submit-button"
            disabled={isLoading}
          >
            {isLoading ? "Creating account..." : "Create Account"}
          </Button>
        </form>

        <div className="auth-footer">
          <p>
            Already have an account?{" "}
            <Button
              variant="link"
              onClick={() => navigate("/signin")}
              className="auth-link"
            >
              Sign in
            </Button>
          </p>
        </div>
      </div>
    </div>
  );
}
