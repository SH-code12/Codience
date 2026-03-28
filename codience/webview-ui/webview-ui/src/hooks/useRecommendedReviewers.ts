import { useEffect, useState, useCallback } from "react";
import { fetchRecommendedReviewers } from "../services/reviewers.service";
import type { RecommendedReviewer } from "../types/Reviewers";
import type { PullRequest } from "../types/PullRequest";

export const useRecommendedReviewers = (selectedPR: PullRequest | null) => {
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
      });
      setData(res);
    } catch (e) {
      setError("Failed to load recommended reviewers");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [selectedPR]);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, loading, error, reload: load };
};

export default useRecommendedReviewers;
