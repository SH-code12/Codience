import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import type { PullRequest } from "../types/PullRequest";
import {
  getDefaultReviewerRecommendationSettings,
  loadReviewerRecommendationSettings,
  normalizeRequiredReviewer,
  normalizeRequiredReviewers,
  saveReviewerRecommendationSettings,
} from "../utils/reviewerRecommendationSettings";
import type { RequiredReviewer } from "../types/Reviewers";
import "./styles/ReviewerRecommendationSettings.css";

type LocationState = {
  selectedPR?: PullRequest;
};

type ReviewerRowState = RequiredReviewer & {
  id: string;
};

const createReviewerRow = (reviewer?: Partial<RequiredReviewer>): ReviewerRowState => ({
  id:
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `reviewer-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  ...normalizeRequiredReviewer(reviewer ?? {}),
});

const ReviewerRecommendationSettingsPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { prNumber } = useParams();
  const selectedPR = (location.state as LocationState | null)?.selectedPR ?? null;
  const repoName = localStorage.getItem("RepoName") ?? "default-repo";
  const parsedPrNumber = Number(prNumber);
  const storedSettings = useMemo(
    () =>
      Number.isFinite(parsedPrNumber)
        ? loadReviewerRecommendationSettings(repoName, parsedPrNumber)
        : null,
    [parsedPrNumber, repoName],
  );

  const [k, setK] = useState(3);
  const [requiredReviewers, setRequiredReviewers] = useState<ReviewerRowState[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fallback =
      storedSettings ??
      getDefaultReviewerRecommendationSettings(
        repoName,
        Number.isFinite(parsedPrNumber) ? parsedPrNumber : 0,
        selectedPR?.title ?? "",
      );

    setK(fallback.k);
    setRequiredReviewers(
      fallback.requiredReviewers.length > 0
        ? fallback.requiredReviewers.map((reviewer) => createReviewerRow(reviewer))
        : [createReviewerRow()],
    );
  }, [repoName, parsedPrNumber, selectedPR?.title, storedSettings]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!Number.isFinite(parsedPrNumber)) {
      setError("The PR number is missing or invalid.");
      return;
    }

    if (!Number.isInteger(k) || k <= 0) {
      setError("Top k reviewers must be a positive integer.");
      return;
    }

    const trimmedReviewers = normalizeRequiredReviewers(requiredReviewers);
    const hasIncompleteReviewer = requiredReviewers.some((reviewer) => {
      const username = reviewer.username.trim();
      const jiraUsername = reviewer.jiraUsername.trim();

      return (username.length > 0 || jiraUsername.length > 0) && (!username || !jiraUsername);
    });

    if (hasIncompleteReviewer) {
      setError("Each reviewer row must include both a GitHub username and a Jira username.");
      return;
    }

    const nextSettings = {
      repoName,
      prNumber: parsedPrNumber,
      prTitle: selectedPR?.title ?? storedSettings?.prTitle ?? "",
      k,
      commitCount: storedSettings?.commitCount ?? 0,
      requiredReviewers: trimmedReviewers,
      updatedAt: new Date().toISOString(),
    };

    saveReviewerRecommendationSettings(nextSettings);
    navigate(-1);
  };

  return (
    <div className="reviewerSettingsPage">
      <div className="reviewerSettingsCard">
        <div className="reviewerSettingsHeader">
          <div>
            <p className="eyebrow">Reviewer recommendation settings</p>
            <h2>{selectedPR ? selectedPR.title : `PR #${prNumber ?? ""}`}</h2>
            <p className="subtext">
              Tune reviewer inputs for this pull request.
            </p>
          </div>
          <button
            type="button"
            className="secondaryButton"
            onClick={() => navigate(-1)}
          >
            Back
          </button>
        </div>

        <form className="reviewerSettingsForm" onSubmit={handleSubmit}>
          <label>
            Top k reviewers
            <input
              type="number"
              min={1}
              step={1}
              value={k}
              onChange={(event) => setK(Number(event.target.value))}
            />
          </label>

          <label className="fullWidth">
            Required reviewers
            <div className="reviewerRows">
              {requiredReviewers.map((reviewer, index) => (
                <div key={reviewer.id} className="reviewerRow">
                  <input
                    type="text"
                    value={reviewer.username}
                    onChange={(event) => {
                      const value = event.target.value;
                      setRequiredReviewers((current) =>
                        current.map((row, rowIndex) =>
                          rowIndex === index ? { ...row, username: value } : row,
                        ),
                      );
                    }}
                    placeholder="GitHub username"
                  />
                  <input
                    type="text"
                    value={reviewer.jiraUsername}
                    onChange={(event) => {
                      const value = event.target.value;
                      setRequiredReviewers((current) =>
                        current.map((row, rowIndex) =>
                          rowIndex === index ? { ...row, jiraUsername: value } : row,
                        ),
                      );
                    }}
                    placeholder="Jira username"
                  />
                  <button
                    type="button"
                    className="removeReviewerButton"
                    onClick={() => {
                      setRequiredReviewers((current) =>
                        current.length === 1
                          ? [createReviewerRow()]
                          : current.filter((_, rowIndex) => rowIndex !== index),
                      );
                    }}
                    aria-label={`Remove reviewer row ${index + 1}`}
                  >
                    -
                  </button>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="addReviewerButton"
              onClick={() => setRequiredReviewers((current) => [...current, createReviewerRow()])}
            >
              Add reviewer
            </button>
          </label>

          {error ? <div className="formError">{error}</div> : null}

          <div className="formActions">
            <button type="button" className="ghostButton" onClick={() => navigate(-1)}>
              Cancel
            </button>
            <button type="submit" className="primaryButton">
              Save settings
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ReviewerRecommendationSettingsPage;
