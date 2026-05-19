import type {
  ReviewersAnalyticsResponse,
  RecommendedReviewer,
  ReviewerRecommendationRequest,
} from "../types/Reviewers";

export const fetchReviewersAnalytics =
  async (): Promise<ReviewersAnalyticsResponse> => {
    // 🔥 Replace with real API later
    // const res = await fetch("/api/reviewers/analytics");
    // return await res.json();

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
): Promise<RecommendedReviewer[]> => {
  if (!pr) return [];

  return new Promise((resolve) => {
    setTimeout(() => {
      const basePool: RecommendedReviewer[] = [
        { reviewerName: "alice", confidence: 0.92 },
        { reviewerName: "bob", confidence: 0.85 },
        { reviewerName: "carol", confidence: 0.78 },
        { reviewerName: "david", confidence: 0.74 },
        { reviewerName: "eva", confidence: 0.7 },
      ];

      const reviewerNames = (pr.reviewerNames ?? [])
        .map((name) => name.trim().toLowerCase())
        .filter(Boolean);

      const filteredPool =
        reviewerNames.length > 0
          ? basePool.filter((candidate) =>
              reviewerNames.includes(candidate.reviewerName.toLowerCase()),
            )
          : basePool;

      const commitBoost = Math.min(0.12, Math.max(0, (pr.commitCount ?? 0) / 500));
      const k = Math.max(1, pr.k ?? 3);

      const dummy = (filteredPool.length > 0 ? filteredPool : basePool)
        .map((reviewer, idx) => ({
          ...reviewer,
          confidence: Math.max(
            0,
            Math.min(1, reviewer.confidence + commitBoost - idx * 0.02),
          ),
        }))
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, k);

      resolve(dummy);
    }, 300);
  });
};

export default { fetchReviewersAnalytics, fetchRecommendedReviewers };
