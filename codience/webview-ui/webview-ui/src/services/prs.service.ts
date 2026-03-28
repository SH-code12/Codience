import axios from "axios";
import type { PullRequest } from "../types/PullRequest";

export const fetchPRs = async (): Promise<PullRequest[]> => {
  const url =
    "https://codience.onrender.com/api/GitHubAuth/SamaAshrafAhmed/api_test/pulls";

  console.log("🔵 Fetching PRs from API...");
  console.log("API URL:", url);

  try {
    const res = await axios.get(url);

    console.log("✅ API Status:", res.status);
    console.log("✅ API Response:", res.data);

    const prs: PullRequest[] = res.data.map((pr: any) => {
      // Generate random risk score
      const score = 10 + Math.random() * 50;

      const risk_level = score <= 30 ? "low" : score <= 40 ? "medium" : "high";

      return {
        ...pr,
        createdAt:
          pr.createdAt === "0001-01-01T00:00:00"
            ? new Date().toISOString()
            : pr.createdAt,
        files_changed: pr.files_changed ?? 0,
        risk: {
          risk_score: score.toFixed(2),
          risk_level,
          comments: Math.floor(Math.random() * 10),
          files_changed: Math.floor(Math.random() * 10) + 1,
        },
      };
    });

    console.log("📦 Processed PRs with risk values:", prs);

    return prs;
  } catch (error: any) {
    console.error("❌ Failed to fetch PRs:", error?.message || error);
    throw new Error("Failed to fetch pull requests");
  }
};

export default { fetchPRs };
