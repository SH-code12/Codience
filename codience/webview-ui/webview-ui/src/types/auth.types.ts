export interface SignUpPayload {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}
export interface LoginPayload {
  username: string;
  password: string;
}


export interface AuthResponse {
  token: string;
  user: {
    id: string;
    username: string;
    email?: string;
  };
}

