import React from "react";
import { AuthCard } from "../components/auth/AuthCard";
import { LoginForm } from "../components/auth/LoginForm";
import "./styles/auth.css";
import Logo from "../assets/Codience Logo (3).png";

const LoginPage: React.FC = () => {
  return (
    <div className="auth-page">
      <div className="auth-brand">
        <img src={Logo} alt="Codience logo" />
      </div>

      <AuthCard>
        <LoginForm />
      </AuthCard>
    </div>
  );
};

export default LoginPage;
