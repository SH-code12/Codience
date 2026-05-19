import type {
  ReviewerRecommendationSettings,
} from "../types/Reviewers";

const STORAGE_PREFIX = "ReviewerRecommendationSettings";

export const getReviewerSettingsKey = (
  repoName: string,
  prNumber: number,
) => `${STORAGE_PREFIX}:${repoName.trim() || "default-repo"}:${prNumber}`;

export const normalizeReviewerNames = (value: string): string[] =>
  value
    .split(/\r?\n|,/)
    .map((name) => name.trim())
    .filter(Boolean);

export const getDefaultReviewerRecommendationSettings = (
  repoName: string,
  prNumber: number,
  prTitle = "",
): ReviewerRecommendationSettings => ({
  repoName,
  prNumber,
  prTitle,
  k: 3,
  commitCount: 0,
  reviewerNames: [],
  updatedAt: new Date().toISOString(),
});

export const loadReviewerRecommendationSettings = (
  repoName: string,
  prNumber: number,
): ReviewerRecommendationSettings | null => {
  try {
    const raw = localStorage.getItem(getReviewerSettingsKey(repoName, prNumber));
    if (!raw) return null;

    const parsed = JSON.parse(raw) as ReviewerRecommendationSettings;
    if (
      typeof parsed?.k !== "number" ||
      typeof parsed?.commitCount !== "number" ||
      !Array.isArray(parsed?.reviewerNames)
    ) {
      return null;
    }

    return parsed;
  } catch {
    return null;
  }
};

export const saveReviewerRecommendationSettings = (
  settings: ReviewerRecommendationSettings,
): ReviewerRecommendationSettings => {
  localStorage.setItem(
    getReviewerSettingsKey(settings.repoName, settings.prNumber),
    JSON.stringify(settings),
  );

  return settings;
};
