import React from "react";
import { AuthCard } from "../components/auth/AuthCard";
import { SignUpForm } from "../components/auth/SignUpForm";
import "./styles/Auth.css";
import Logo from "../assets/Codience Logo (3).png";

const SignUpPage: React.FC = () => {
  return (
    <div className="auth-page">
      <div className="auth-brand">
        <img src={Logo} alt="Codience logo" />
      </div>

      <AuthCard>
        <SignUpForm />
      </AuthCard>
    </div>
  );
};

export default SignUpPage;
