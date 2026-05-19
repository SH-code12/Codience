import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./styles/GetRepoName.css";
import { useRepo } from "../hooks/useRepo";
import type { GitHubRepo } from "../types/GitHubRepo";
import { storeOwnerNameFromRepoUrl } from "../services/repos.service";

const REPOS_URL = "http://localhost:5051/api/GithubAuth/repos";

interface RepoApiItem {
  name: string;
  url: string;
  description: string | null;
}

const getRepoUrlParts = (url: string) => {
  try {
    const parsedUrl = new URL(url);
    const parts = parsedUrl.pathname.split("/").filter(Boolean);
    return {
      owner: parts[0] ?? "",
      repo: parts[1] ?? "",
    };
  } catch {
    return { owner: "", repo: "" };
  }
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

const fetchUserRepos = async (
  userName: string,
  page = 1,
  pageSize = 50,
): Promise<GitHubRepo[]> => {
  const response = await fetch(
    `${REPOS_URL}?userName=${encodeURIComponent(userName)}&page=${page}&pageSize=${pageSize}`,
  );

  if (!response.ok) {
    throw new Error("Failed to load repositories.");
  }

  const data = (await response.json()) as
    | RepoApiItem[]
    | { items?: RepoApiItem[]; data?: RepoApiItem[] };

  const repos = Array.isArray(data) ? data : data.items ?? data.data ?? [];

  return repos.map(normalizeRepo);
};

const GetRepoName = () => {
  const [query, setQuery] = useState("");
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setRepo } = useRepo();
  const userName = localStorage.getItem("User") ?? "";

  const getRepoLabel = (repo: GitHubRepo) => {
    return repo.name;
  };

  useEffect(() => {
    if (!userName) {
      setError("No username found in local storage.");
      return;
    }

    const loadRepos = async () => {
      try {
        setLoading(true);
        setError(null);
        const fetchedRepos = await fetchUserRepos(userName, 1, 50);
        setRepos(fetchedRepos);
      } catch (err: any) {
        setError(err?.message || "Failed to load repositories.");
      } finally {
        setLoading(false);
      }
    };

    void loadRepos();
  }, [userName]);

  const matches = useMemo(() => {
    const search = query.trim().toLowerCase();

    if (!search) return [];

    return repos.filter((repo) => {
      const repoName = repo.name?.toLowerCase() ?? "";

      return repoName.includes(search);
    });
  }, [query, repos]);

  const pickRepo = (repo: GitHubRepo) => {
    const repoName = getRepoLabel(repo);
    setSelectedRepo(repo);
    setQuery(repoName);
  };

  const submit = () => {
    if (!selectedRepo) return;

    const repoName = getRepoLabel(selectedRepo);
    if (selectedRepo.html_url) {
      storeOwnerNameFromRepoUrl(selectedRepo.html_url);
    }
    setRepo(repoName);
    navigate("/home");
  };

  return (
    <div className="getRepoName">
      <div className="repoNameContainer">
        <h3>Select Repo</h3>

        <div className="repoSearchBox">
          <input
            type="text"
            value={query}
            onChange={(e) => {
              const value = e.currentTarget.value;
              setQuery(value);
              setSelectedRepo(null);
            }}
            placeholder="Repo Name..."
            aria-label="Search repositories"
            autoComplete="off"
          />

          {query.trim().length > 0 && (
            <div className="repoMenu" role="listbox" aria-label="Repository suggestions">
              {loading && <div className="repoMenuState">Loading repositories...</div>}
              {!loading && error && <div className="repoMenuState repoMenuError">{error}</div>}
              {!loading && !error && matches.length === 0 && (
                <div className="repoMenuState">No matching repositories found.</div>
              )}
              {!loading &&
                !error &&
                matches.map((repo) => {
                  const repoName = getRepoLabel(repo);

                  return (
                    <button
                      key={repo.id ?? repoName}
                      type="button"
                      className="repoMenuItem"
                      onMouseDown={(event) => {
                        event.preventDefault();
                        pickRepo(repo);
                      }}
                    >
                      <span className="repoMenuItemTitle">{repoName}</span>
                    </button>
                  );
                })}
            </div>
          )}
        </div>

        <button onClick={submit} disabled={!selectedRepo}>
          Continue
        </button>
      </div>
    </div>
  );
};

export default GetRepoName;
