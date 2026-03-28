import { useLocation } from "react-router-dom";
import PRsHome from "./PRsHome";
import Dashboard from "./Dashboard";
import "./styles/Home.css";

const Home = () => {
  const location = useLocation();

  const renderContent = () => {
    if (location.pathname.includes("dashboard")) return <Dashboard />;
    return <PRsHome />;
  };

  const isDashboard = location.pathname.includes("dashboard");

  return (
    <div className={`Home ${isDashboard ? "" : "homeHideScroll"}`}>
      {renderContent()}
    </div>
  );
};

export default Home;
