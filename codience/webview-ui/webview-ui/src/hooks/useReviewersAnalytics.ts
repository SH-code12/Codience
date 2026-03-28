import { useEffect, useState } from "react";
import { fetchReviewersAnalytics } from "../services/reviewers.service";
import type { ReviewersAnalyticsResponse } from "../types/Reviewers";

export const useReviewersAnalytics = () => {
  const [data, setData] = useState<ReviewersAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const res = await fetchReviewersAnalytics();
      setData(res);
    } catch (err) {
      setError("Failed to fetch analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return { data, loading, error, reload: loadData };
};
