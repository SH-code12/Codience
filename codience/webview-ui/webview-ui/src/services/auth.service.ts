import type {
  LoginPayload,
  SignUpPayload,
  AuthResponse,
} from "../types/auth.types";
import axios from "axios";
import type { DeviceCodeResponse } from "../types/DeviceCode";
import type { Token } from "../types/Token";

export const authService = {
  async signUp(data: SignUpPayload): Promise<AuthResponse> {
    // Replace with real API call later
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          token: "mock-token",
          user: {
            id: "1",
            username: data.username,
            email: data.email,
          },
        });
      }, 1000);
    });
  },

  async login(data: LoginPayload): Promise<AuthResponse> {
    // 🔁 Replace this with:
    // return axios.post('/api/auth/login', data)

    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (data.username === "admin" && data.password === "1234") {
          resolve({
            token: "mock-login-token",
            user: {
              id: "1",
              username: data.username,
            },
          });
        } else {
          reject(new Error("Invalid credentials"));
        }
      }, 1000);
    });
  },
};

// Exchange a device code response for an access token from the auth backend
export async function exchangeDeviceCode(
  deviceData: DeviceCodeResponse,
): Promise<Token> {
  const url = "https://codience.onrender.com/api/GitHubAuth/token";
  const res = await axios.post<Token>(url, deviceData, {
    validateStatus: () => true,
  });
  console.log("[exchangeDeviceCode] status:", res.status);
  console.log("[exchangeDeviceCode] response:", res.data);
  if (res.status === 200) return res.data;
  throw new Error(`Token exchange failed with status ${res.status}`);
}

// Fetch a device-code from the backend
export async function fetchDeviceCode(): Promise<DeviceCodeResponse> {
  const url = "https://codience.onrender.com/api/GitHubAuth/device-code";
  const res = await axios.get<DeviceCodeResponse>(url);
  console.log("[fetchDeviceCode] status:", res.status);
  console.log("[fetchDeviceCode] response:", res.data);
  if (res.status === 200) return res.data;
  throw new Error(`Failed to fetch device code: ${res.status}`);
}
