import { useEffect, useState } from "react";
import PRsTable from "../components/prs/PRsTable";
import type { PullRequest } from "../types/PullRequest";
import "./styles/PRsHome.css";
import CardsRow from "../components/ui/CardsRow";
import { usePRs } from "../hooks/usePRs";

const PRsHome = () => {
  const projectName: string | null = localStorage.getItem("RepoName");
  const { data: prs, loading, error } = usePRs();

  const [localPRs, setLocalPRs] = useState<PullRequest[] | null>(null);
  const [openPrs, setOpenPrs] = useState(0);
  const [highPriority] = useState(0);
  const [highRisk, setHighRisk] = useState(0);

  useEffect(() => {
    setLocalPRs(prs);
  }, [prs]);

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

  if (loading) return <p className="loading">Loading...</p>;
  if (error) return <p className="loading">{error}</p>;
  if (!localPRs) return null;

  return (
    <div className="home">
      <h2 className="projectTitle">{projectName}</h2>
      <CardsRow
        items={[
          { label: "Open PRs", value: openPrs, className: "open" },
          {
            label: "High Priority",
            value: highPriority,
            className: "priority",
          },
          { label: "High Risk", value: highRisk, className: "risk" },
        ]}
      />
      <h2 className="tableCaption">Pull Requests</h2>
      <PRsTable prs={localPRs} onRiskUpdate={setLocalPRs} />
    </div>
  );
};

export default PRsHome;
