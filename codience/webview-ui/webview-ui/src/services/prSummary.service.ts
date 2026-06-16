import axios from "axios";

interface PrSummaryResponse {
  summary?: string;
}

const SUMMARY_BASE_URL = "http://127.0.0.1:8002/summarize";

const getGitHubSummaryContext = () => {
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

export const fetchPrSummary = async (prNumber: number): Promise<string> => {
  if (!Number.isFinite(prNumber)) {
    throw new Error("The PR number is missing or invalid.");
  }

  const { owner, repo } = getGitHubSummaryContext();
  const url = `${SUMMARY_BASE_URL}/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/pulls/${prNumber}`;
  const response = await axios.get<PrSummaryResponse>(url);

  return response.data?.summary ?? "";
};

export default { fetchPrSummary };
