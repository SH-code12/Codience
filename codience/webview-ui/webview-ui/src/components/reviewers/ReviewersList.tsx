import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { PullRequest } from "../../types/PullRequest";
import { useRecommendedReviewers } from "../../hooks/useRecommendedReviewers";
import type { RecommendedReviewer } from "../../types/Reviewers";
import { useReviewerRecommendationSettings } from "../../hooks/useReviewerRecommendationSettings";
import "./ReviewersList.css";

interface Props {
  selectedPR: PullRequest | null;
}

const ReviewersList: React.FC<Props> = ({ selectedPR }) => {
  const navigate = useNavigate();

  const [expandedReviewer, setExpandedReviewer] = useState<string | null>(null);

  const { settings } = useReviewerRecommendationSettings(selectedPR);

  const hasJiraAuth =
    Boolean(localStorage.getItem("JiraAccessToken")) &&
    Boolean(localStorage.getItem("JiraCloudId")) &&
    Boolean(localStorage.getItem("JiraProjectKey"));

  const {
    data: reviewers,
    loading,
    error,
  } = useRecommendedReviewers(
    hasJiraAuth ? selectedPR : null,
    settings
  );

  if (!hasJiraAuth) {
    return (
      <div className="noSelection reviewersAuthPrompt">
        <p>
          Authenticate with Jira to load reviewer recommendations for this
          service.
        </p>

        <button
          type="button"
          className="reviewersAuthButton"
          onClick={() => navigate("/jira-login")}
        >
          Authenticate with Jira
        </button>
      </div>
    );
  }

  const renderRows = () => {
    if (loading)
      return (
        <tr className="loadingRow">
          <td colSpan={2}>Loading recommended reviewers…</td>
        </tr>
      );

    if (error)
      return (
        <tr className="errorRow">
          <td colSpan={2}>{error}</td>
        </tr>
      );

    if (!reviewers || reviewers.length === 0)
      return (
        <tr className="emptyRow">
          <td colSpan={2}>
            No recommended reviewers found for this PR.
          </td>
        </tr>
      );

    return reviewers.map((r: RecommendedReviewer, idx) => (
      <React.Fragment key={r.reviewerName + idx}>
        <tr
          onClick={() =>
            setExpandedReviewer(
              expandedReviewer === r.reviewerName
                ? null
                : r.reviewerName
            )
          }
          style={{ cursor: "pointer" }}
        >
          <td className="revName">{r.reviewerName}</td>

          <td className="revConfidence">
            {(r.confidence * 100).toFixed(1)}%
          </td>
        </tr>

        {r.justification &&
          expandedReviewer === r.reviewerName && (
            <tr className="justificationRow">
              <td colSpan={2}>
                <div className="reviewerJustification">
                  <div className="reviewerJustificationTitle">
                    Why this reviewer?
                  </div>

                  <p>{r.justification}</p>
                </div>
              </td>
            </tr>
          )}
      </React.Fragment>
    ));
  };

  return (
    <div>
      {selectedPR ? (
        <>
          <div className="selectedPRBrief">
            <div className="prNumber">
              #{selectedPR.number}
            </div>

            <div className="prTitle">
              {selectedPR.title}
            </div>

            <div className="prState">
              {selectedPR.state}
            </div>
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