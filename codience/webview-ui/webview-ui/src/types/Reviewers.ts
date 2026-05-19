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
}

export interface ReviewerRecommendationRequest {
  number: number;
  title: string;
  k?: number;
  commitCount?: number;
  reviewerNames?: string[];
  repoName?: string;
}

export interface ReviewerRecommendationSettings {
  repoName: string;
  prNumber: number;
  prTitle: string;
  k: number;
  commitCount: number;
  reviewerNames: string[];
  updatedAt: string;
}
