import axios from "axios";

export interface GitHubProfile {
  login: string;
  id: number;
  avatar_url: string;
  html_url: string;
  name: string | null;
  company: string | null;
  blog: string;
  location: string | null;
  email: string | null;
  bio: string | null;
  public_repos: number;
  created_at: string;
}

const PROFILE_URL = "http://localhost:5051/api/GitHubProfiling";

export const fetchGitHubProfile = async (
  username: string,
): Promise<GitHubProfile> => {
  const response = await axios.get<GitHubProfile>(
    `${PROFILE_URL}/${encodeURIComponent(username)}`,
  );

  return response.data;
};

export default { fetchGitHubProfile };