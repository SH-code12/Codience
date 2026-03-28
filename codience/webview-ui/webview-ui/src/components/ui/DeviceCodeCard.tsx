import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import type { DeviceCodeResponse } from "../../types/DeviceCode";
import "../styles/DeviceCodeCard.css";
import { exchangeDeviceCode } from "../../services/auth.service";

interface props {
  data: DeviceCodeResponse | null;
}

const DeviceCodeCard = ({ data }: props) => {
  if (!data) return null;

  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    const intervalSeconds = Math.max(1, data.interval ?? 5);
    const expiresMs = (data.expires_in ?? 600) * 1000;

    const poll = async () => {
      setLoading(true);
      try {
        const token = await exchangeDeviceCode(data);
        if (cancelled) return;
        console.log("Token obtained:", token);
        localStorage.setItem("User", token.login);
        navigate("/getRepo");
      } catch (err: any) {
        if (cancelled) return;
        // expected while pending; do not surface to user immediately
        console.log(
          "Poll error (expected while pending):",
          err?.message ?? err,
        );
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    // start immediate poll, then interval
    void poll();
    const id = setInterval(poll, intervalSeconds * 1000);

    // stop polling after expiry
    const timeoutId = setTimeout(() => {
      if (cancelled) return;
      clearInterval(id);
      setError("Device code expired. Please request a new code.");
      setLoading(false);
    }, expiresMs);

    return () => {
      cancelled = true;
      clearInterval(id);
      clearTimeout(timeoutId);
    };
  }, [data, navigate]);

  return (
    <div className="deviceCodeContainer">
      <p>User Code</p>
      <p className="userCode"> {data.user_code}</p>
      <div className="linksContainer">
        <a
          href={data.verification_uri}
          target="_blank"
          className="signInLink"
          rel="noreferrer"
        >
          Open Verification Page
        </a>
      </div>
      {/* status/errors are intentionally not shown in UI; look at console logs */}
    </div>
  );
};

export { DeviceCodeCard };
export default DeviceCodeCard;
