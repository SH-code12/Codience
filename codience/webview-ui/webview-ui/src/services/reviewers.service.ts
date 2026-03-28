import type {
  ReviewersAnalyticsResponse,
  RecommendedReviewer,
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
  pr: { number: number; title: string } | null,
): Promise<RecommendedReviewer[]> => {
  if (!pr) return [];

  return new Promise((resolve) => {
    setTimeout(() => {
      const dummy: RecommendedReviewer[] = [
        { reviewerName: "alice", confidence: 0.92 },
        { reviewerName: "bob", confidence: 0.85 },
        { reviewerName: "carol", confidence: 0.78 },
      ].map((r, idx) => ({
        ...r,
        confidence: Math.max(0, r.confidence - idx * 0.03),
      }));

      dummy.sort((a, b) => b.confidence - a.confidence);
      resolve(dummy);
    }, 300);
  });
};

export default { fetchReviewersAnalytics, fetchRecommendedReviewers };
