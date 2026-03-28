import React, { useState } from "react";
import { AuthInput } from "./AuthInput";
import type { SignUpPayload } from "../../types/auth.types";
import { authService } from "../../services/auth.service";
import { useNavigate } from "react-router-dom";
import UserIcon from "../../assets/Sign_up_icon.svg";

export const SignUpForm: React.FC = () => {
  const navigate = useNavigate();

  const [form, setForm] = useState<SignUpPayload>({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const validate = (): boolean => {
    if (!form.username || !form.email || !form.password) {
      setError("All fields are required");
      return false;
    }

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validate()) return;

    try {
      setLoading(true);
      await authService.signUp(form);

      // Later: store token, context, etc.
      navigate("/getRepo");
    } catch (err) {
      setError("Sign up failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div className="auth-header">
        <img src={UserIcon} alt="User icon" className="auth-header-icon" />

        <h2 className="auth-title">Sign Up</h2>

        <div className="auth-divider" />
      </div>

      <AuthInput
        name="username"
        placeholder="username..."
        value={form.username}
        onChange={handleChange}
      />

      <AuthInput
        name="email"
        type="email"
        placeholder="email..."
        value={form.email}
        onChange={handleChange}
      />

      <AuthInput
        name="password"
        type="password"
        placeholder="password..."
        value={form.password}
        onChange={handleChange}
      />

      <AuthInput
        name="confirmPassword"
        type="password"
        placeholder="confirm password..."
        value={form.confirmPassword}
        onChange={handleChange}
      />

      {error && <div className="auth-error-global">{error}</div>}
      <button type="submit" className="auth-button" disabled={loading}>
        {loading ? "Creating account..." : "Sign Up"}
      </button>
      <span className="auth-link" onClick={() => navigate("/login")}>
        Login instead
      </span>
    </form>
  );
};
