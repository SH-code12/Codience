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
  const [commitCount, setCommitCount] = useState(0);
  const [requiredReviewers, setRequiredReviewers] = useState<ReviewerRowState[]>([]);
  const [prTitle, setPrTitle] = useState("");
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
    setCommitCount(fallback.commitCount);
    setRequiredReviewers(
      fallback.requiredReviewers.length > 0
        ? fallback.requiredReviewers.map((reviewer) => createReviewerRow(reviewer))
        : [createReviewerRow()],
    );
    setPrTitle(selectedPR?.title ?? fallback.prTitle ?? "");
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

    if (!Number.isInteger(commitCount) || commitCount < 0) {
      setError("Commit count must be a non-negative integer.");
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
      prTitle: prTitle.trim() || (selectedPR?.title ?? ""),
      k,
      commitCount,
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
              Save the inputs that will be sent with this PR when the API is wired.
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

          <label>
            Commit count for AI model
            <input
              type="number"
              min={0}
              step={1}
              value={commitCount}
              onChange={(event) => setCommitCount(Number(event.target.value))}
            />
          </label>

          <label className="fullWidth">
            Required reviewers
            <div className="reviewerRowsHint">
              Add GitHub and Jira usernames for reviewers that should always be included.
              Leave everything blank to send the API without required reviewers.
            </div>
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
                    Remove
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

          <label className="fullWidth">
            PR title
            <input
              type="text"
              value={prTitle}
              onChange={(event) => setPrTitle(event.target.value)}
              placeholder="Optional title override"
            />
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