import type { PullRequest } from "../types/PullRequest";
import "./styles/PRsTable.css";
type props = {
  prs: PullRequest[] | null;
};
const PRsTable = ({ prs }: props) => {
  if (!prs) return null;
  return (
    <table className="prsTable">
      <thead>
        <tr>
          <th>PR Title</th>
          <th>Author</th>
          <th>Risk Score</th>
          <th>Priority</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {prs.map((pr) => (
          <tr>
            <td className="titleCell"> {pr.pr_title} </td>
            <td>{pr.auhtor}</td>
            <RiskCell risk_score={pr.risk_score} />
            <PriorityCell priority={pr.priority_score} />
            {pr.status == "open" ? (
              <td className="status open">{pr.status}</td>
            ) : (
              <td className="status closed">{pr.status}</td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default PRsTable;

type risk = {
  risk_score: number;
};
const RiskCell = ({ risk_score }: risk) => {
  if (risk_score < 30) {
    return <td className="riskCell low">{risk_score}</td>;
  } else if (risk_score < 60) {
    return <td className="riskCell med">{risk_score}</td>;
  }
  return <td className="riskCell high">{risk_score}</td>;
};

type priority = {
  priority: number;
};

const PriorityCell = ({ priority }: priority) => {
  let pr: string = "priorityCell ";

  if (priority < 30) {
    pr += "low";
  } else if (priority < 60) {
    pr += "med";
  } else {
    pr += "high";
  }
  return (
    <td className={pr}>
      <span>{priority}</span>
    </td>
  );
};
