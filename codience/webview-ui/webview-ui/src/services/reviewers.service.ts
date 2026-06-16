import axios from "axios";
import type {
  ReviewersAnalyticsResponse,
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

export const fetchReviewersAnalytics =
  async (): Promise<ReviewersAnalyticsResponse> => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          reviewers: [
            {
              id: "1",
              name: "Fady Mohammed",
              reviewedPRs: 20,
              avgReviewTime: "2 days",
              aiRecommendations: 15,
            },
            {
              id: "2",
              name: "Sami Mostafa",
              reviewedPRs: 10,
              avgReviewTime: "3 days",
              aiRecommendations: 11,
            },
            {
              id: "3",
              name: "Farida Ahmed",
              reviewedPRs: 18,
              avgReviewTime: "2 days",
              aiRecommendations: 17,
            },
            {
              id: "4",
              name: "Omar Yasser",
              reviewedPRs: 25,
              avgReviewTime: "2 days",
              aiRecommendations: 15,
            },
            {
              id: "5",
              name: "Mahmoud Ahmed",
              reviewedPRs: 12,
              avgReviewTime: "2 days",
              aiRecommendations: 18,
            },
          ],
          workload: [
            {
              reviewerId: "1",
              reviewerName: "Fady Mohammed",
              weeklyLoad: [8, 11, 11, 0],
            },
            {
              reviewerId: "2",
              reviewerName: "Sami Mostafa",
              weeklyLoad: [12, 1, 6, 0],
            },
            {
              reviewerId: "3",
              reviewerName: "Omar Yasser",
              weeklyLoad: [2, 8, 11, 0],
            },
            {
              reviewerId: "4",
              reviewerName: "Farida Ahmed",
              weeklyLoad: [6, 3, 3, 0],
            },
            {
              reviewerId: "5",
              reviewerName: "Mahmoud Ahmed",
              weeklyLoad: [8, 2, 1, 0],
            },
          ],
        });
      }, 500);
    });
  };

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

export default { fetchReviewersAnalytics, fetchRecommendedReviewers };
