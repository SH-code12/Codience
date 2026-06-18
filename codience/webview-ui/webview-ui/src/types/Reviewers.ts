export interface RecommendedReviewer {
  reviewerName: string;
  confidence: number;
  justification?: string;
}

export interface RequiredReviewer {
  username: string;
  jiraUsername: string;
}

export interface ReviewerRecommendationRequest {
  owner: string;
  repo: string;
  pr_number: number;
  options: {
    top_k: number;
  };
  jira_token: string;
  jira_cloud_id: string;
  jira_project_key: string;
  required_reviewers?: RequiredReviewer[];
}

export interface ReviewerRecommendationSettings {
  repoName: string;
  prNumber: number;
  prTitle: string;
  k: number;
  commitCount: number;
  requiredReviewers: RequiredReviewer[];
  updatedAt: string;
}
