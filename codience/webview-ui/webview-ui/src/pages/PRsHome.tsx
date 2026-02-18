import { useEffect, useState } from "react";
import PRsTable from "../components/PRsTable";
import type { PullRequest } from "../types/PullRequest";
import "./styles/PRsHome.css";

interface Props {
  prs: PullRequest[] | null;
  projectName: string | null;
}

const PRsHome = ({ prs, projectName }: Props) => {
  const [localPRs, setLocalPRs] = useState<PullRequest[] | null>(prs);
  const [openPrs, setOpenPrs] = useState(0);
  const [highPriority] = useState(0);
  const [highRisk, setHighRisk] = useState(0);

  // Update counts whenever PRs (or their risk) change
  useEffect(() => {
    if (!localPRs) return;
    let openCount = 0;
    let highRiskCount = 0;

    localPRs.forEach((pr) => {
      if (pr.state === "open") openCount++;
      if (pr.risk?.risk_level === "high") highRiskCount++;
    });

    setOpenPrs(openCount);
    setHighRisk(highRiskCount);
  }, [localPRs]);

  if (!localPRs) return null;

  return (
    <div className="home">
      <h2 className="projectTitle">{projectName}</h2>
      <div className="cardsContainer">
        <div className="card open">
          <p>Open PRs</p>
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
      <PRsTable prs={localPRs} onRiskUpdate={setLocalPRs} />
    </div>
  );
};

export default PRsHome;
