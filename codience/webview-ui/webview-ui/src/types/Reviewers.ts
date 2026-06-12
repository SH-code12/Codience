export interface Reviewer {
  id: string;
  name: string;
  reviewedPRs: number;
  avgReviewTime: string;
  aiRecommendations: number;
}

export interface WeeklyWorkloadEntry {
  reviewerId: string;
  reviewerName: string;
  weeklyLoad: number[]; // [week1, week2, week3, week4]
}
export interface ReviewersAnalyticsResponse {
  reviewers: Reviewer[];
  workload: WeeklyWorkloadEntry[];
}

export interface RecommendedReviewer {
  reviewerName: string;
  confidence: number; // 0..1
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
