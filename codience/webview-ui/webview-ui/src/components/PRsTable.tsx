import axios from "axios";
import type { PullRequest } from "../types/PullRequest";
import "./styles/PRsTable.css";
import { useEffect, useState } from "react";
import type { RiskType } from "../types/RiskType";
type props = {
  prs: PullRequest[] | null;
};
const PRsTable = ({ prs }: props) => {
  if (!prs) return null;
  const repoName: string | null = localStorage.getItem("RepoName");
  const [riskData, setRiskData] = useState<RiskType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [myLoading, setLoading] = useState<boolean>(true);
  useEffect(() => {
    const ComputeRiskScores = async () => {
      try {
        prs.map(async (pr) => {
          setLoading(true);
          const response = await axios.post<RiskType>(
            "https://codience.onrender.com/api/risk",
            {
              repo: repoName,
              problem_statement: "",
              patch: pr.title,
            }
          );
          console.log(response.data);
          setRiskData(response.data);
          pr.risk = response.data;
        });
      } catch (e) {
        setError("error");
        console.log("error", e);
      } finally {
        setLoading(false);
        console.log(myLoading);
      }
      console.log(myLoading);
    };
    ComputeRiskScores();
  }, []);
  return (
    <table className="prsTable">
      <thead>
        <tr>
          <th>PR Title</th>
          {/* <th>Author</th> */}
          <th>Risk Score</th>
          <th>Risk Level</th>
          {/* <th>Priority</th> */}
          <th>Created At</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {prs.map((pr) => (
          <tr>
            <td className="titleCell"> {pr.title} </td>
            {/* <td>{pr.auhtor}</td> */}
            {/* <RiskCell risk_score={pr.risk_score} />
            <PriorityCell priority={pr.priority_score} /> */}
            {myLoading && <td>Calc..</td>}
            {myLoading && <td>Calc..</td>}
            {!myLoading && <td>{pr.risk?.risk_score}</td>}
            {!myLoading && <RiskCell risk_level={pr.risk?.risk_level} />}
            {/* <td>{ pr.risk_level}</td> */}
            <td>
              {pr.createdAt}
              {/* {pr.createdAt.getHours()}:{pr.createdAt.getMinutes()}{" "} */}
            </td>
            {pr.state == "open" ? (
              <td className="status open">{pr.state}</td>
            ) : (
              <td className="status closed">{pr.state}</td>
            )}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default PRsTable;

type risk = {
  risk_level: string | null | undefined;
};
const RiskCell = ({ risk_level }: risk) => {
  const risk_score = risk_level;
  if (risk_score == "low") {
    return <td className="riskCell low">{risk_score}</td>;
  } else if (risk_score == "medium") {
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
