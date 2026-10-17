import { FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // =========================================
  // REGISTRATION SUCCESS MESSAGE
  // =========================================

  const registrationMessage =
    (
      location.state as {
        message?: string;
      } | null
    )?.message || "";

  // =========================================
  // LOGIN SUBMIT
  // =========================================

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");

    // =========================================
    // VALIDATION
    // =========================================

    if (!email.trim()) {
      setError("Please enter your email.");

      return;
    }

    if (!password) {
      setError("Please enter your password.");

      return;
    }

    try {
      setLoading(true);

      // =========================================
      // LOGIN
      // =========================================

      await login(email.trim().toLowerCase(), password);

      // =========================================
      // LOGIN SUCCESS
      // =========================================

      navigate("/dashboard", {
        replace: true,
      });
    } catch (error: any) {
      console.error("Login error:", error);

      // =========================================
      // INVALID LOGIN
      // =========================================

      if (error.response?.status === 401) {
        setError("Invalid email or password.");
      }

      // =========================================
      // OTHER SERVER ERROR
      // =========================================
      else if (error.response?.data?.detail) {
        setError(error.response.data.detail);
      } else {
        setError("Unable to connect to ResQDrive AI server.");
      }
    } finally {
      setLoading(false);
    }
  };

  // =========================================
  // UI
  // =========================================

  return (
    <div className="login-page">
      <div className="login-card">
        {/* ================================= */}
        {/* LOGO */}
        {/* ================================= */}

        <div className="login-logo">R</div>

        {/* ================================= */}
        {/* TITLE */}
        {/* ================================= */}

        <h1>ResQDrive AI</h1>

        <p className="login-subtitle">AI-powered roadside assistance</p>

        {/* ================================= */}
        {/* REGISTRATION SUCCESS */}
        {/* ================================= */}

        {registrationMessage && (
          <div
            style={{
              marginBottom: "15px",
              padding: "10px",
              borderRadius: "6px",
              backgroundColor: "#e8f5e9",
              color: "#2e7d32",
              textAlign: "center",
            }}
          >
            {registrationMessage}
          </div>
        )}

        {/* ================================= */}
        {/* LOGIN FORM */}
        {/* ================================= */}

        <form onSubmit={handleSubmit}>
          {/* EMAIL */}

          <label>Email</label>

          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          {/* PASSWORD */}

          <label>Password</label>

          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {/* ERROR */}

          {error && <div className="login-error">{error}</div>}

          {/* LOGIN BUTTON */}

          <button type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {/* ================================= */}
        {/* CREATE ACCOUNT */}
        {/* ================================= */}

        <p
          style={{
            marginTop: "20px",
            textAlign: "center",
          }}
        >
          Don't have an account? <Link to="/register">Create Account</Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
