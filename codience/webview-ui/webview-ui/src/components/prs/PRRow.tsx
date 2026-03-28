import React from "react";
import type { PullRequest } from "../../types/PullRequest";

interface Props {
  pr: PullRequest;
  selected?: boolean;
  onSelect?: (pr: PullRequest) => void;
}

export const RiskCell: React.FC<{ risk_level?: string }> = ({ risk_level }) => {
  if (risk_level === "low") return <td className="riskCell low">Low</td>;
  if (risk_level === "medium") return <td className="riskCell med">Medium</td>;
  if (risk_level === "high") return <td className="riskCell high">High</td>;
  return <td className="riskCell unknown">Unknown</td>;
};

const PRRow: React.FC<Props> = ({ pr, selected, onSelect }) => {
  return (
    <tr
      onClick={() => onSelect?.(pr)}
      className={selected ? "selected-row" : ""}
    >
      <td className="titleCell">{pr.title}</td>
      <td>{pr.risk?.risk_score ?? "N/A"}</td>
      <RiskCell risk_level={pr.risk?.risk_level} />
      <td>{pr.files_changed ?? 0}</td>
      <td>{pr.risk?.comments ?? 0}</td>
      <td>{pr.createdAt}</td>
      <td className={`status ${pr.state}`}>{pr.state}</td>
    </tr>
  );
};

export default PRRow;
