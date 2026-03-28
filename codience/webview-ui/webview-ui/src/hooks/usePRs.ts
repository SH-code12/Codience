import { useEffect, useState } from "react";
import { fetchPRs } from "../services/prs.service";
import type { PullRequest } from "../types/PullRequest";

export const usePRs = () => {
  const [data, setData] = useState<PullRequest[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const res = await fetchPRs();
      setData(res);
    } catch (err) {
      setError("Failed to load PRs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  return { data, loading, error, reload: load };
};

export default usePRs;
