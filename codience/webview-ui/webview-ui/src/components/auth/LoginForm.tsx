import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthInput } from "./AuthInput";
import type { LoginPayload } from "../../types/auth.types";
import { authService } from "../../services/auth.service";
import UserIcon from "../../assets/Sign_up_icon.svg";

export const LoginForm: React.FC = () => {
  const navigate = useNavigate();

  const [form, setForm] = useState<LoginPayload>({
    username: "",
    password: "",
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
    if (!form.username || !form.password) {
      setError("Username and password are required");
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

      const response = await authService.login(form);

      // 🔐 Save token (temporary example)
      localStorage.setItem("token", response.token);

      // Later: Use AuthContext instead
      navigate("/getRepo");
    } catch (err) {
      setError("Invalid username or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <div className="auth-header">
        <img src={UserIcon} alt="User icon" className="auth-header-icon" />

        <h2 className="auth-title">Login</h2>

        <div className="auth-divider" />
      </div>

      <AuthInput
        name="username"
        placeholder="username..."
        value={form.username}
        onChange={handleChange}
      />

      <AuthInput
        name="password"
        type="password"
        placeholder="password..."
        value={form.password}
        onChange={handleChange}
      />

      {error && <div className="auth-error-global">{error}</div>}

      <button type="submit" className="auth-button" disabled={loading}>
        {loading ? "Signing in..." : "Login"}
      </button>

      <span className="auth-link" onClick={() => navigate("/signup")}>
        Create account instead
      </span>
    </form>
  );
};
