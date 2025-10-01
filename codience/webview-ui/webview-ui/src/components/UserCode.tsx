import { useEffect, useState } from "react";
import type { DeviceCodeResponse } from "../types/DeviceCode";
import axios from "axios";
import DeviceCodeCard from "./DeviceCodeCard";
import "./styles/GetDeviceCode.css";

const UserCode = () => {
  const [data, setData] = useState<DeviceCodeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");
  useEffect(() => {
    const fetchDeviceCode = async () => {
      try {
        const response = await axios.get<DeviceCodeResponse>(
          "https://codience.onrender.com/api/GitHubAuth/device-code"
        );
        setData(response.data);
      } catch (err) {
        setError("❌ Failed to fetch device code.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDeviceCode();
  }, []);

  return (
    <>
      <div className="App">
        <h1>GitHub Login</h1>
        {loading && <p className="loading">Loading...</p>}
        {error && (
          <p style={{ color: "red" }} className="error">
            {error}
          </p>
        )}
        {!loading && !error && <DeviceCodeCard data={data} />}
      </div>
    </>
  );
};

export default UserCode;
