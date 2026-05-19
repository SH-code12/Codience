import { useEffect, useState, useCallback } from "react";
import { fetchRecommendedReviewers } from "../services/reviewers.service";
import type { RecommendedReviewer } from "../types/Reviewers";
import type { PullRequest } from "../types/PullRequest";
import type { ReviewerRecommendationSettings } from "../types/Reviewers";

export const useRecommendedReviewers = (
  selectedPR: PullRequest | null,
  settings: ReviewerRecommendationSettings | null = null,
) => {
  const [data, setData] = useState<RecommendedReviewer[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!selectedPR) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await fetchRecommendedReviewers({
        number: selectedPR.number,
        title: selectedPR.title,
        k: settings?.k,
        commitCount: settings?.commitCount,
        reviewerNames: settings?.reviewerNames,
        repoName: settings?.repoName,
      });
      setData(res);
    } catch (e) {
      setError("Failed to load recommended reviewers");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedPR, settings]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, loading, error, reload: load };
};

export default useRecommendedReviewers;
