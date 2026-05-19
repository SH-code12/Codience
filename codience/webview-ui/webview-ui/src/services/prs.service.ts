import axios from "axios";
import type { PullRequest } from "../types/PullRequest";

type OrchestrateRisk = {
  risk_score?: number | string;
  risk_level?: string;
  comments?: number;
  files_changed?: number | string;
};

const getUserRepo = () => {
  const userName = localStorage.getItem("User");
  const repoName = localStorage.getItem("RepoName");

  if (!userName || !repoName) {
    throw new Error("Username or repository name not found in local storage.");
  }

  return { userName, repoName };
};

const withOneRetry = async <T>(request: () => Promise<T>): Promise<T> => {
  try {
    return await request();
  } catch (firstError) {
    return await request().catch((secondError) => {
      throw secondError ?? firstError;
    });
  }
};

const fetchPRFilesChangedCount = async (
  userName: string,
  repoName: string,
  prNumber: number,
): Promise<number> => {
  const filesUrl = `https://codience.onrender.com/api/GitHubAuth/${encodeURIComponent(userName)}/${encodeURIComponent(repoName)}/pulls/${prNumber}/files`;

  const response = await withOneRetry(() => axios.get(filesUrl));

  if (!Array.isArray(response.data)) {
    return 0;
  }

  return response.data.length;
};

const fetchPRFilesChangedCountWithRetry = async (
  userName: string,
  repoName: string,
  prNumber: number,
) => withOneRetry(() => fetchPRFilesChangedCount(userName, repoName, prNumber));

const mapRiskLevel = (value: unknown): string => {
  const normalized = String(value ?? "").toLowerCase();
  if (normalized === "low" || normalized === "medium" || normalized === "high") {
    return normalized;
  }
  return "unknown";
};

const normalizeRiskScore = (value: unknown): number | string => {
  if (typeof value === "number") return value;
  if (typeof value === "string") return value;
  return "N/A";
};

const parseOrchestrateRisk = (payload: unknown): OrchestrateRisk => {
  if (!payload || typeof payload !== "object") {
    return { risk_score: "N/A", risk_level: "unknown" };
  }

  const record = payload as Record<string, unknown>;

  // API shape example: { "bug_probability": 0.6828987457292666 }
  if (typeof record.bug_probability === "number") {
    const probability = Math.max(0, Math.min(1, record.bug_probability));
    const score = Number((probability * 100).toFixed(2));
    const risk_level =
      probability < 0.33 ? "low" : probability < 0.66 ? "medium" : "high";

    return {
      risk_score: score,
      risk_level,
    };
  }

  const nestedRisk =
    record.risk && typeof record.risk === "object"
      ? (record.risk as Record<string, unknown>)
      : null;

  const risk_score = normalizeRiskScore(
    nestedRisk?.risk_score ?? record.risk_score ?? record.score,
  );
  const risk_level = mapRiskLevel(
    nestedRisk?.risk_level ?? record.risk_level ?? record.level,
  );

  return {
    risk_score,
    risk_level,
    comments:
      (nestedRisk?.comments as number | undefined) ??
      (record.comments as number | undefined),
    files_changed:
      (nestedRisk?.files_changed as number | undefined) ??
      (record.files_changed as number | undefined),
  };
};

export const fetchPRs = async (): Promise<PullRequest[]> => {
  const { userName, repoName } = getUserRepo();

  const url = `https://codience.onrender.com/api/GitHubAuth/${userName}/${repoName}/pulls`;

  console.log("🔵 Fetching PRs from API...");
  console.log("API URL:", url);

  try {
    const res = await axios.get(url);

    console.log("✅ API Status:", res.status);
    console.log("✅ API Response:", res.data);

    const normalizedPRs = res.data.map((pr: any) => ({
      ...pr,
      createdAt:
        pr.createdAt === "0001-01-01T00:00:00"
          ? new Date().toISOString()
          : pr.createdAt,
      files_changed: "Loading...",
      risk:
        pr.risk ??
        ({
          risk_score: "Loading...",
          risk_level: "loading",
          comments: 0,
          files_changed: "Loading...",
        } as PullRequest["risk"]),
    }));

    console.log("📦 PRs fetched without waiting for risk scoring:", normalizedPRs);

    return normalizedPRs as PullRequest[];
  } catch (error: any) {
    console.error("❌ Failed to fetch PRs:", error?.message || error);
    throw new Error("Failed to fetch pull requests");
  }
};

export const enrichPRsWithFilesChanged = async (
  prs: PullRequest[],
  onPRFilesChangedResolved?: (updatedPR: PullRequest, index: number) => void,
): Promise<PullRequest[]> => {
  const { userName, repoName } = getUserRepo();

  try {
    const prsWithFilesChanged = [...prs];

    for (const [index, pr] of prs.entries()) {
      try {
        const filesChanged = await fetchPRFilesChangedCountWithRetry(
          userName,
          repoName,
          pr.number,
        );

        const updatedPR: PullRequest = {
          ...prs[index],
          files_changed: filesChanged,
          risk: prs[index].risk
            ? {
                ...prs[index].risk,
                files_changed: filesChanged,
              }
            : prs[index].risk,
        };

        prsWithFilesChanged[index] = updatedPR;
        onPRFilesChangedResolved?.(updatedPR, index);
      } catch (filesError: any) {
        console.error(
          `❌ Failed to fetch changed files for PR #${pr.number}:`,
          filesError?.message || filesError,
        );

        const updatedPR: PullRequest = {
          ...prs[index],
          files_changed: "Error",
          risk: prs[index].risk
            ? {
                ...prs[index].risk,
                files_changed: "Error",
              }
            : prs[index].risk,
        };

        prsWithFilesChanged[index] = updatedPR;
        onPRFilesChangedResolved?.(updatedPR, index);
      }
    }

    return prsWithFilesChanged;
  } catch (error: any) {
    console.error("❌ Failed to enrich PR files changed:", error?.message || error);
    return prs;
  }
};

export const enrichPRsWithRisk = async (
  prs: PullRequest[],
  onPRRiskResolved?: (updatedPR: PullRequest, index: number) => void,
): Promise<PullRequest[]> => {
  const { userName, repoName } = getUserRepo();

  try {
    const prsWithRisk = [...prs];

    for (const [index, pr] of prs.entries()) {
      let risk: OrchestrateRisk;

      try {
        const riskUrl = `http://127.0.0.1:8000/orchestrate/${encodeURIComponent(userName)}/${encodeURIComponent(repoName)}/${pr.number}`;
        const riskRes = await withOneRetry(() => axios.get(riskUrl));
        risk = parseOrchestrateRisk(riskRes.data);
      } catch (riskError: any) {
        console.error(
          `❌ Failed to fetch risk for PR #${pr.number}:`,
          riskError?.message || riskError,
        );
        risk = { risk_score: "N/A", risk_level: "unknown" };
      }

      const updatedPR: PullRequest = {
        ...prs[index],
        risk: {
          risk_score: risk.risk_score ?? "N/A",
          risk_level: risk.risk_level ?? "unknown",
          comments: risk.comments ?? 0,
          files_changed: prs[index].files_changed ?? risk.files_changed ?? 0,
        },
      };

      prsWithRisk[index] = updatedPR;
      onPRRiskResolved?.(updatedPR, index);
    }

    console.log("📦 PR risk enrichment finished:", prsWithRisk);

    return prsWithRisk;
  } catch (error: any) {
    console.error("❌ Failed to enrich PR risks:", error?.message || error);
    return prs;
  }
};

export default { fetchPRs, enrichPRsWithRisk, enrichPRsWithFilesChanged };
