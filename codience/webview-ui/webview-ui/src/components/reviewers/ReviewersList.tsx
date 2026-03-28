import React from "react";
import type { PullRequest } from "../../types/PullRequest";
import { useRecommendedReviewers } from "../../hooks/useRecommendedReviewers";
import type { RecommendedReviewer } from "../../types/Reviewers";

interface Props {
  selectedPR: PullRequest | null;
}

const ReviewersList: React.FC<Props> = ({ selectedPR }) => {
  const {
    data: reviewers,
    loading,
    error,
  } = useRecommendedReviewers(selectedPR);

  const renderRows = () => {
    if (loading)
      return (
        <tr className="loadingRow">
          <td colSpan={3}>Loading recommended reviewers…</td>
        </tr>
      );
    if (error)
      return (
        <tr className="errorRow">
          <td colSpan={3}>{error}</td>
        </tr>
      );
    if (!reviewers || reviewers.length === 0)
      return (
        <tr className="emptyRow">
          <td colSpan={3}>No recommended reviewers found for this PR.</td>
        </tr>
      );
    return reviewers.map((r: RecommendedReviewer, idx) => (
      <tr key={r.reviewerName + idx}>
        <td className="revName">{r.reviewerName}</td>
        <td className="revConfidence">{(r.confidence * 100).toFixed(1)}%</td>
      </tr>
    ));
  };

  return (
    <div>
      {selectedPR ? (
        <>
          <div className="selectedPRBrief">
            <div className="prNumber">#{selectedPR.number}</div>
            <div className="prTitle">{selectedPR.title}</div>
            <div className="prState">{selectedPR.state}</div>
          </div>

          <table className="reviewersTable">
            <thead>
              <tr>
                <th>Reviewer</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>{renderRows()}</tbody>
          </table>
        </>
      ) : (
        <div className="noSelection">
          Click a PR to see recommended reviewers
        </div>
      )}
    </div>
  );
};

export default ReviewersList;
