import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import type { PullRequest } from "../types/PullRequest";
import type { ReviewerRecommendationSettings } from "../types/Reviewers";
import {
  loadReviewerRecommendationSettings,
  saveReviewerRecommendationSettings,
} from "../utils/reviewerRecommendationSettings";

export const useReviewerRecommendationSettings = (
  selectedPR: PullRequest | null,
) => {
  const location = useLocation();

  const getInitialSettings = () => {
    if (!selectedPR) return null;

    const repoName = localStorage.getItem("RepoName") ?? "default-repo";
    return repoName
      ? loadReviewerRecommendationSettings(repoName, selectedPR.number)
      : null;
  };

  const [settings, setSettings] = useState<ReviewerRecommendationSettings | null>(
    getInitialSettings,
  );

  useEffect(() => {
    if (!selectedPR) {
      setSettings(null);
      return;
    }

    setSettings(getInitialSettings());
  }, [selectedPR?.number, selectedPR?.title, location.pathname]);

  const saveSettings = useCallback(
    (nextSettings: ReviewerRecommendationSettings) => {
      const saved = saveReviewerRecommendationSettings(nextSettings);
      setSettings(saved);
      return saved;
    },
    [],
  );

  return { settings, setSettings, saveSettings };
};

export default useReviewerRecommendationSettings;