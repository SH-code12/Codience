import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom"; // ✅ detect current route
import axios from "axios";
import type { PullRequest } from "../types/PullRequest";
import PRsHome from "./PRsHome";
import Dashboard from "./Dashboard";

const Home = () => {
  const user: string | null = localStorage.getItem("User");
  const repoName: string | null = localStorage.getItem("RepoName");
  const [prs, setPrs] = useState<PullRequest[] | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const location = useLocation(); 

  useEffect(() => {
    const fetchPRs = async () => {
      try {
        const response = await axios.get<PullRequest[]>(
          `https://codience.onrender.com/api/GitHubAuth/${user}/${repoName}/pulls`
        );
        setPrs(response.data);
      } catch (err) {
        console.error(err);
        setPrs([]);
      } finally {
        setLoading(false);
      }
    };
    fetchPRs();
  }, [user, repoName]);

  const renderContent = () => {
    if (location.pathname.includes("dashboard")) {
      return <Dashboard prs={prs} projectName={repoName} />;
    }
    return <PRsHome prs={prs} projectName={repoName} />;
  };

  return (
    <div className="Home">
      {loading ? <p className="loading">Loading...</p> : renderContent()}
    </div>
  );
};

export default Home;
