import type {
  RequiredReviewer,
  ReviewerRecommendationSettings,
} from "../types/Reviewers";

type LegacyReviewerRecommendationSettings = Partial<ReviewerRecommendationSettings> & {
  reviewerNames?: string[];
};

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
  requiredReviewers: [],
  updatedAt: new Date().toISOString(),
});

export const normalizeRequiredReviewer = (
  reviewer: Partial<RequiredReviewer>,
): RequiredReviewer => ({
  username: reviewer.username?.trim() ?? "",
  jiraUsername: reviewer.jiraUsername?.trim() ?? "",
});

export const normalizeRequiredReviewers = (
  reviewers: Array<Partial<RequiredReviewer>>,
): RequiredReviewer[] =>
  reviewers
    .map(normalizeRequiredReviewer)
    .filter((reviewer) => reviewer.username.length > 0 || reviewer.jiraUsername.length > 0);

export const loadReviewerRecommendationSettings = (
  repoName: string,
  prNumber: number,
): ReviewerRecommendationSettings | null => {
  try {
    const raw = localStorage.getItem(getReviewerSettingsKey(repoName, prNumber));
    if (!raw) return null;

    const parsed = JSON.parse(raw) as
      | ReviewerRecommendationSettings
      | LegacyReviewerRecommendationSettings;

    const legacyParsed = parsed as LegacyReviewerRecommendationSettings;

    const requiredReviewers = Array.isArray(parsed?.requiredReviewers)
      ? normalizeRequiredReviewers(parsed.requiredReviewers)
      : Array.isArray(legacyParsed.reviewerNames)
        ? legacyParsed.reviewerNames
            .map((name: string) => ({ username: name, jiraUsername: "" }))
            .filter((reviewer: RequiredReviewer) => reviewer.username.length > 0)
        : [];

    if (
      typeof parsed?.k !== "number" ||
      typeof parsed?.commitCount !== "number" ||
      !Array.isArray(requiredReviewers)
    ) {
      return null;
    }

    return {
      repoName: parsed.repoName ?? repoName,
      prNumber: parsed.prNumber ?? prNumber,
      prTitle: parsed.prTitle ?? "",
      k: parsed.k,
      commitCount: parsed.commitCount,
      requiredReviewers,
      updatedAt: parsed.updatedAt ?? new Date().toISOString(),
    };
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
