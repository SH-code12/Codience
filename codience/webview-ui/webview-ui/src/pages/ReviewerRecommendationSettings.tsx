import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import type { PullRequest } from "../types/PullRequest";
import {
  getDefaultReviewerRecommendationSettings,
  loadReviewerRecommendationSettings,
  normalizeReviewerNames,
  saveReviewerRecommendationSettings,
} from "../utils/reviewerRecommendationSettings";
import "./styles/ReviewerRecommendationSettings.css";

type LocationState = {
  selectedPR?: PullRequest;
};

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
  const [reviewerNames, setReviewerNames] = useState("");
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
    setReviewerNames(fallback.reviewerNames.join("\n"));
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

    const nextSettings = {
      repoName,
      prNumber: parsedPrNumber,
      prTitle: prTitle.trim() || (selectedPR?.title ?? ""),
      k,
      commitCount,
      reviewerNames: normalizeReviewerNames(reviewerNames),
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
            Reviewer names
            <textarea
              rows={7}
              value={reviewerNames}
              onChange={(event) => setReviewerNames(event.target.value)}
              placeholder="Enter one reviewer per line or separate with commas"
            />
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