import { useEffect, useState } from "react";
import {
  fetchGitHubProfile,
  type GitHubProfile,
} from "../services/profile.service";

export const useGitHubProfile = (username: string | null) => {
  const [profile, setProfile] = useState<GitHubProfile | null>(null);
  const [loading, setLoading] = useState(Boolean(username));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!username) {
      setProfile(null);
      setLoading(false);
      setError("No username available. Sign in again to load your profile.");
      return;
    }

    let cancelled = false;

    const loadProfile = async () => {
      try {
        setLoading(true);
        setError(null);

        const data = await fetchGitHubProfile(username);

        if (!cancelled) {
          setProfile(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError("Failed to load profile data.");
          setProfile(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadProfile();

    return () => {
      cancelled = true;
    };
  }, [username]);

  return { profile, loading, error };
};

export default useGitHubProfile;