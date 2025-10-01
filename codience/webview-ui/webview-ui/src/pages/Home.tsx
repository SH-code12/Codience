import { useEffect, useState } from "react";
import type { PullRequest } from "../types/PullRequest";
import axios from "axios";
import PRsHome from "./PRsHome";

const Home = () => {
  const user: string | null = localStorage.getItem("User");
  const repoName: string | null = localStorage.getItem("RepoName");
  const [prs, setPrs] = useState<PullRequest[] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchDeviceCode = async () => {
      console.log("fn");
      try {
        const response = await axios.get<[PullRequest]>(
          `https://codience.onrender.com/api/GitHubAuth/${user}/${repoName}/pulls`
        );
        setPrs(response.data);
      } catch (err) {
        setPrs([]);
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchDeviceCode();
  }, []);

  return (
    <>
      <div className="Home">
        {loading && <p className="loading">Loading...</p>}
        {!loading && <PRsHome prs={prs} projectName={repoName} />}
      </div>
    </>
  );
};

export default Home;
