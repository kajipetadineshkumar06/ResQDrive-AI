import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import api from "../api/axios";

const Register = () => {
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");

  const [email, setEmail] = useState("");

  const [phone, setPhone] = useState("");

  const [password, setPassword] = useState("");

  const [confirmPassword, setConfirmPassword] = useState("");

  const [error, setError] = useState("");

  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setError("");

    // ======================================
    // VALIDATION
    // ======================================

    if (!fullName.trim()) {
      setError("Please enter your full name.");

      return;
    }

    if (!email.trim()) {
      setError("Please enter your email.");

      return;
    }

    if (!phone.trim()) {
      setError("Please enter your phone number.");

      return;
    }

    if (password.length < 8) {
      setError("Password must contain at least 8 characters.");

      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");

      return;
    }

    // ======================================
    // SEND REQUEST
    // ======================================

    try {
      setLoading(true);

      const response = await api.post("/auth/register", {
        full_name: fullName.trim(),

        email: email.trim().toLowerCase(),

        password: password,

        phone: phone.trim(),
      });

      console.log("Registration successful:", response.data);

      // ======================================
      // GO TO LOGIN
      // ======================================

      navigate("/login", {
        replace: true,

        state: {
          message: "Account created successfully. Please sign in.",
        },
      });
    } catch (error: any) {
      console.error("Registration error:", error);

      // ======================================
      // 422 VALIDATION ERROR
      // ======================================

      if (error.response?.status === 422) {
        console.error("FastAPI validation details:", error.response.data);

        const detail = error.response.data?.detail;

        if (Array.isArray(detail)) {
          setError(
            detail
              .map((item: any) => `${item.loc?.join(".")}: ${item.msg}`)
              .join(", "),
          );
        } else {
          setError("Invalid registration data.");
        }

        return;
      }

      // ======================================
      // DUPLICATE ACCOUNT
      // ======================================

      if (error.response?.status === 409) {
        setError(
          error.response.data?.detail ||
            "Email or phone number already registered.",
        );

        return;
      }

      // ======================================
      // OTHER BACKEND ERROR
      // ======================================

      if (error.response?.data?.detail) {
        setError(error.response.data.detail);

        return;
      }

      // ======================================
      // SERVER CONNECTION ERROR
      // ======================================

      setError("Unable to create your account. Please try again.");
    } finally {
      setLoading(false);
    }
  };

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

        <h1>Create Account</h1>

        <p className="login-subtitle">Join ResQDrive AI</p>

        {/* ================================= */}
        {/* FORM */}
        {/* ================================= */}

        <form onSubmit={handleSubmit}>
          {/* FULL NAME */}

          <label>Full Name</label>

          <input
            type="text"
            placeholder="Enter your full name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            required
          />

          {/* EMAIL */}

          <label>Email</label>

          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          {/* PHONE */}

          <label>Phone</label>

          <input
            type="tel"
            placeholder="Enter your phone number"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            required
          />

          {/* PASSWORD */}

          <label>Password</label>

          <input
            type="password"
            placeholder="Minimum 8 characters"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          {/* CONFIRM PASSWORD */}

          <label>Confirm Password</label>

          <input
            type="password"
            placeholder="Re-enter your password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />

          {/* ERROR */}

          {error && <div className="login-error">{error}</div>}

          {/* BUTTON */}

          <button type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        {/* ================================= */}
        {/* LOGIN LINK */}
        {/* ================================= */}

        <p
          style={{
            marginTop: "20px",
            textAlign: "center",
          }}
        >
          Already have an account? <Link to="/login">Sign In</Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
