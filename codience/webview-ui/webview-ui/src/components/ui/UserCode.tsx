import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import type { DeviceCodeResponse } from "../../types/DeviceCode";
import {
  fetchDeviceCode,
  exchangeDeviceCode,
} from "../../services/auth.service";
import "../styles/DeviceCodeCard.css";

const DeviceCodeCard = () => {
  const navigate = useNavigate();

  const [deviceData, setDeviceData] = useState<DeviceCodeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const runAuthFlow = async () => {
      try {
        setLoading(true);
        setError(null);

        console.log("🔵 Fetching device code...");

        // 1️⃣ Fetch device code
        const deviceResponse = await fetchDeviceCode();

        console.log("✅ Device Code API Response:", deviceResponse);

        setDeviceData(deviceResponse);

        console.log("🔵 Sending device code to exchange API...");

        // 2️⃣ Exchange device code
        const token = await exchangeDeviceCode(deviceResponse);

        console.log("✅ Exchange API Response:", token);

        // 3️⃣ Save username
        localStorage.setItem("User", token.login);

        console.log("📦 Username stored in localStorage:", token.login);

        // 4️⃣ Navigate if success
        navigate("/getRepo");
      } catch (err: any) {
        console.error("❌ Authentication flow failed:", err);
        setError(err?.message || "Authentication failed");
      } finally {
        setLoading(false);
      }
    };

    runAuthFlow();
  }, [navigate]);

  return (
    <div className="deviceCodeContainer">
      <p>User Code</p>

      {deviceData && (
        <>
          <p className="userCode">{deviceData.user_code}</p>

          <div className="linksContainer">
            <a
              href={deviceData.verification_uri}
              target="_blank"
              className="signInLink"
              rel="noreferrer"
            >
              Open Verification Page
            </a>
          </div>
        </>
      )}

      {loading && <p>Loading authentication...</p>}

      {error && <p className="errorText">{error}</p>}
    </div>
  );
};

export default DeviceCodeCard;
