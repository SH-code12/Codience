import React from "react";

interface AuthCardProps {
  children: React.ReactNode;
}

export const AuthCard: React.FC<AuthCardProps> = ({ children }) => {
  return <div className="auth-card">{children}</div>;
};
