import PRsTable from "../components/PRsTable";
import type { PullRequest } from "../types/PullRequest";
import "./styles/PRsHome.css";
interface props  {
  prs: PullRequest[] | null;
  projectName: string | null;
}
const PRsHome = ({ prs, projectName}: props) => {
  if (!prs) return;
  let openPrs: number = 0;
  let highPriority: number = 0;
  let highRisk: number = 0;

  prs.forEach((element) => {
    if (element.state == "open") openPrs++;
    if (element.risk?.risk_level == "high") highRisk++;
    // if (element.risk_score > 60) highRisk++;
    // if (element.priority_score > 60) highPriority++;
  });
  return (
    <div className="home">
      <h2 className="projectTitle">{projectName}</h2>
      <div className="cardsContainer">
        <div className="card open">
          <p>Open Prs</p>
          <span>{openPrs}</span>
        </div>
        <div className="card priority">
          <p>High Priority</p>
          <span>{highPriority}</span>
        </div>
        <div className="card risk">
          <p>High Risk</p>
          <span>{highRisk}</span>
        </div>
      </div>
      <h2 className="tableCaption">Pull Requests</h2>
      <PRsTable prs={prs} />
    </div>
  );
};

export default PRsHome;
