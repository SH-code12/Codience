import axios from "axios";
import type {
  RecommendedReviewer,
  ReviewerRecommendationRequest,
  ReviewerRecommendationSettings,
} from "../types/Reviewers";

const REVIEWER_RECOMMENDATIONS_URL = "http://localhost:8000/api/recommend-reviewers";

const recommendationCache = new Map<string, Promise<RecommendedReviewer[]>>();

interface ReviewerRecommendationApiItem {
  name: string;
  confidence_score: number;
  justification?: string;
}

interface ReviewerRecommendationApiResponse {
  recommended_reviewers?: ReviewerRecommendationApiItem[];
}

const getGitHubContext = () => {
  const owner = (localStorage.getItem("ownerName") ?? "").trim();
  const repo = (localStorage.getItem("RepoName") ?? "").trim();

  if (!owner) {
    throw new Error("GitHub owner is missing. Please re-select the repository.");
  }

  if (!repo) {
    throw new Error("GitHub repository is missing. Please re-select the repository.");
  }

  return { owner, repo };
};

const getJiraContext = () => {
  const jiraToken = (localStorage.getItem("JiraAccessToken") ?? "").trim();
  const jiraCloudId = (localStorage.getItem("JiraCloudId") ?? "").trim();
  const jiraProjectKey = (localStorage.getItem("JiraProjectKey") ?? "").trim();

  if (!jiraToken) {
    throw new Error("Jira access token is missing. Please authenticate with Jira again.");
  }

  if (!jiraCloudId) {
    throw new Error("Jira cloud ID is missing. Please authenticate with Jira again.");
  }

  if (!jiraProjectKey) {
    throw new Error("Jira project key is missing. Please select a Jira project again.");
  }

  return { jiraToken, jiraCloudId, jiraProjectKey };
};

const buildRecommendationRequest = (
  pr: ReviewerRecommendationRequest,
  settings: ReviewerRecommendationSettings | null,
): ReviewerRecommendationRequest & { settingsVersion: string } => {
  const { owner, repo } = getGitHubContext();
  const { jiraToken, jiraCloudId, jiraProjectKey } = getJiraContext();
  const reviewerRows = settings?.requiredReviewers ?? [];
  const requiredReviewers = reviewerRows
    .map((reviewer) => ({
      username: reviewer.username.trim(),
      jiraUsername: reviewer.jiraUsername.trim(),
    }))
    .filter((reviewer) => reviewer.username.length > 0 && reviewer.jiraUsername.length > 0);

  const request: ReviewerRecommendationRequest = {
    owner,
    repo,
    pr_number: pr.pr_number,
    options: {
      top_k: settings?.k ?? pr.options.top_k,
    },
    jira_token: jiraToken,
    jira_cloud_id: jiraCloudId,
    jira_project_key: jiraProjectKey,
  };

  if (requiredReviewers.length > 0) {
    request.required_reviewers = requiredReviewers;
  }

  return {
    ...request,
    settingsVersion: settings?.updatedAt ?? "",
  };
};

const normalizeReviewerResponse = (
  items: ReviewerRecommendationApiItem[] = [],
): RecommendedReviewer[] =>
  items.map((item) => ({
    reviewerName: item.name,
    confidence:
      item.confidence_score > 1 ? item.confidence_score / 100 : item.confidence_score,
    justification: item.justification,
  }));

export const fetchRecommendedReviewers = async (
  pr: ReviewerRecommendationRequest | null,
  settings: ReviewerRecommendationSettings | null = null,
): Promise<RecommendedReviewer[]> => {
  if (!pr) return [];

  const request = buildRecommendationRequest(pr, settings);
  const cacheKey = JSON.stringify(request);

  const cached = recommendationCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  const requestPromise = axios
    .post<ReviewerRecommendationApiResponse>(REVIEWER_RECOMMENDATIONS_URL, request)
    .then((response) => normalizeReviewerResponse(response.data?.recommended_reviewers ?? []))
    .catch((error) => {
      recommendationCache.delete(cacheKey);
      throw error;
    });

  recommendationCache.set(cacheKey, requestPromise);
  return requestPromise;
};

export default { fetchRecommendedReviewers };
