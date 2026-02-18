import { useState } from 'react';
import {  useNavigate } from 'react-router-dom';
import './styles/GetRepoName.css'
const GetRepoName = () => {
    const [repo, setRepo] = useState<string>("");
    const navigate = useNavigate();
    const getRepo = (name:string) => {
        setRepo(name);
    }
    const submit = () =>{
        localStorage.setItem('RepoName', repo);
        navigate("/home");
    }
  return (
    <div className="getRepoName">
      <div className="repoNameContainer">
        <h3>Enter Repo Name</h3>
        <input
          type="text"
          onKeyUp={(name) => {
            getRepo(name.currentTarget.value);
          }}
        />
        <button onClick={submit}>Submit</button>
      </div>
    </div>
  );
}

export default GetRepoName
