import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./styles/GetRepoName.css";
import { useRepo } from "../hooks/useRepo";

const GetRepoName = () => {
  const [local, setLocal] = useState("");
  const navigate = useNavigate();
  const { setRepo } = useRepo();

  const submit = () => {
    if (!local) return;
    setRepo(local);
    navigate("/home");
  };

  return (
    <div className="getRepoName">
      <div className="repoNameContainer">
        <h3>Enter Repo Name</h3>
        <input
          type="text"
          value={local}
          onChange={(e) => setLocal(e.currentTarget.value)}
          placeholder="owner/repo"
        />
        <button onClick={submit} disabled={!local}>
          Submit
        </button>
      </div>
    </div>
  );
};

export default GetRepoName;
