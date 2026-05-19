import axios from "axios";
import type { GitHubRepo } from "../types/GitHubRepo";

const REPOS_URL = "http://localhost:5051/api/GithubAuth/repos";

interface RepoApiItem {
  name: string;
  url: string;
  description: string | null;
}

export const getRepoUrlParts = (url: string) => {
  try {
    const parsedUrl = new URL(url);
    const parts = parsedUrl.pathname.split("/").filter(Boolean);
    const owner = parts[0] ?? "";
    const repo = parts[1] ?? "";

    return { owner, repo };
  } catch {
    return { owner: "", repo: "" };
  }
};

export const storeOwnerNameFromRepoUrl = (url: string) => {
  const { owner } = getRepoUrlParts(url);

  if (owner) {
    localStorage.setItem("ownerName", owner);
  } else {
    localStorage.removeItem("ownerName");
  }

  return owner;
};

const normalizeRepo = (item: RepoApiItem): GitHubRepo => {
  const { owner, repo } = getRepoUrlParts(item.url);

  return {
    name: item.name || repo,
    full_name: owner && repo ? `${owner}/${repo}` : item.name || repo,
    html_url: item.url,
    description: item.description,
    owner: owner ? { login: owner } : undefined,
  };
};

export const fetchUserRepos = async (
  userName: string,
  page = 1,
  pageSize = 50,
): Promise<GitHubRepo[]> => {
  const response = await axios.get(REPOS_URL, {
    params: { userName, page, pageSize },
  });

  const repos = Array.isArray(response.data)
    ? response.data
    : response.data?.items ?? response.data?.data ?? [];

  return (repos as RepoApiItem[]).map(normalizeRepo);
};

export default { fetchUserRepos };