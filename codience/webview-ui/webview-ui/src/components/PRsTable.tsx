import axios from "axios";
import { useEffect, useState } from "react";
import type { PullRequest } from "../types/PullRequest";
import "./styles/PRsTable.css";

type Props = {
  prs: PullRequest[] | null;
  onSelect?: (pr: PullRequest) => void;
  onRiskUpdate?: (updated: PullRequest[]) => void;
};

type FileData = {
  additions: number;
  deletions: number;
  changes: number;
};

const PRsTable = ({ prs, onSelect, onRiskUpdate }: Props) => {
  if (!prs) return null;

  const [updatedPRs, setUpdatedPRs] = useState<PullRequest[]>(
    prs.map((pr) => ({
      ...pr,
      files_changed: 0,
      risk: {
        risk_score: "Loading...",
        risk_level: "unknown",
        comments: 0,
        files_changed: 0,
      } as any,
    }))
  );

  const [selectedPR, setSelectedPR] = useState<number | null>(null);

  const repoName = localStorage.getItem("RepoName");
  const userName = localStorage.getItem("User");

  useEffect(() => {
    if (!prs || !userName || !repoName) return;

    let isCancelled = false;

    const computeRiskScores = async () => {
      const newPRs = [...updatedPRs];

      await Promise.all(
        prs.map(async (pr, index) => {
          try {
            const filesResponse = await axios.get<FileData[]>(
              `https://codience.onrender.com/api/GitHubAuth/${userName}/${repoName}/pulls/${pr.number}/files`
            );

            const files = filesResponse.data;
            const lines_added = files.reduce((sum, f) => sum + f.additions, 0);
            const lines_deleted = files.reduce(
              (sum, f) => sum + f.deletions,
              0
            );
            const total_changes = files.reduce((sum, f) => sum + f.changes, 0);
            const files_changed = files.length;

            const comments = 0;
            const commits = 0;
            const reverted = 0;
            const merged = pr.state === "closed" ? 1 : 0;
            const change_density =
              files_changed > 0 ? total_changes / files_changed : 0;
            const commit_density =
              commits > 0 ? total_changes / commits : total_changes;

            let score = 0;
            try {
              const riskResponse = await axios.post(
                "https://sphery-arlen-nondecorative.ngrok-free.dev/predict",
                {
                  title: pr.title,
                  lines_added,
                  lines_deleted,
                  files_changed,
                  comments,
                  commits,
                  reverted,
                  merged,
                  total_changes,
                  change_density: parseFloat(change_density.toFixed(2)),
                  commit_density: parseFloat(commit_density.toFixed(2)),
                  is_security: pr.title.toLowerCase().includes("security")
                    ? 1
                    : 0,
                  is_database: pr.title.toLowerCase().includes("db") ? 1 : 0,
                }
              );
              score = riskResponse.data.risk_score ?? 0;
            } catch {
              score = 15;
            }

            const risk_level =
              score <= 30 ? "low" : score <= 40 ? "medium" : "high";

            if (!isCancelled) {
              newPRs[index] = {
                ...pr,
                files_changed,
                risk: {
                  risk_score: score.toFixed(2),
                  risk_level,
                  comments,
                  files_changed,
                } as any,
              };

              setUpdatedPRs([...newPRs]);
              onRiskUpdate?.([...newPRs]);
            }
          } catch (error) {
            console.error(`Error updating PR #${pr.number}:`, error);

            if (!isCancelled) {
              newPRs[index] = {
                ...pr,
                files_changed: 0,
                risk: {
                  risk_score: "N/A",
                  risk_level: "unknown",
                  comments: 0,
                  files_changed: 0,
                } as any,
              };

              setUpdatedPRs([...newPRs]);
              onRiskUpdate?.([...newPRs]);
            }
          }
        })
      );
    };

    computeRiskScores();

    return () => {
      isCancelled = true;
    };
  }, [prs, userName, repoName, onRiskUpdate]);

  const handleSelect = (pr: PullRequest) => {
    setSelectedPR(pr.number);
    if (onSelect) onSelect(pr);
  };

  return (
    <table className="prsTable">
      <thead>
        <tr>
          <th>PR Title</th>
          <th>Risk Score</th>
          <th>Risk Level</th>
          <th>Files Changed</th>
          <th>Comments</th>
          <th>Created At</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {updatedPRs.map((pr) => (
          <tr
            key={pr.number}
            onClick={() => handleSelect(pr)}
            className={selectedPR === pr.number ? "selected-row" : ""}
          >
            <td className="titleCell">{pr.title}</td>
            <td>{pr.risk?.risk_score ?? "N/A"}</td>
            <RiskCell risk_level={pr.risk?.risk_level ?? "unknown"} />
            <td>{pr.files_changed ?? 0}</td>
            <td>{pr.risk?.comments ?? 0}</td>
            <td>{pr.createdAt}</td>
            <td className={`status ${pr.state}`}>{pr.state}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default PRsTable;

type RiskProps = {
  risk_level: string;
};

const RiskCell = ({ risk_level }: RiskProps) => {
  if (risk_level === "low") return <td className="riskCell low">Low</td>;
  if (risk_level === "medium") return <td className="riskCell med">Medium</td>;
  if (risk_level === "high") return <td className="riskCell high">High</td>;
  return <td className="riskCell unknown">Unknown</td>;
};
