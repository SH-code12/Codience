import { useEffect, useState } from "react";
import { fetchPrSummary } from "../services/prSummary.service";

export const usePrSummary = (prNumber: number | null) => {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!prNumber) {
      setSummary(null);
      setError(null);
      setLoading(false);
      return;
    }

    let active = true;

    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await fetchPrSummary(prNumber);
        if (active) setSummary(result);
      } catch (err: any) {
        if (active) {
          setError(err?.message || "Failed to load PR summary.");
          setSummary(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [prNumber]);

  return { summary, loading, error };
};

export default usePrSummary;
