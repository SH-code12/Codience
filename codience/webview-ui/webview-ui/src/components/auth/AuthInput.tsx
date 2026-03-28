import React from "react";

interface AuthInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string;
}

export const AuthInput: React.FC<AuthInputProps> = ({ error, ...props }) => {
  return (
    <div className="auth-input-wrapper">
      <input className="auth-input" {...props} />
      {error && <span className="auth-error">{error}</span>}
    </div>
  );
};
