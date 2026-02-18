import {  useNavigate } from "react-router-dom";
import type { DeviceCodeResponse } from "../types/DeviceCode";
import "./styles/DeviceCodeCard.css";
import axios from "axios";
import type { Token } from "../types/Token";

interface props {
  data: DeviceCodeResponse | null;
}

const DeviceCodeCard = ({ data }: props) => {
  if (!data) return null;

  const navigate = useNavigate();
  const forwardToHome = async () => {
    try {
      const response = await axios.post<Token>(
        "https://codience.onrender.com/api/GitHubAuth/token",
        data
      );
      console.log("Forward response:", response.data);
      localStorage.setItem("User", response.data.login);
      navigate("/getRepo");
    } catch (e) {
      console.log(e);
    }
  };
  return (
    <div className="deviceCodeContainer">
      <p>User Code</p>
      <p className="userCode"> {data.user_code}</p>
      <div className="linksContainer">
        <a
          href={data.verification_uri}
          target="_blank"
          className="signInLink"
          onClick={forwardToHome}
        >
          Sign In
        </a>
      </div>
    </div>
  );
};

export default DeviceCodeCard;
