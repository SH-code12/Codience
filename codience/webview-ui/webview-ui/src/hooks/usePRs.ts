import { useEffect, useRef, useState } from "react";
import { enrichPRsWithRisk, fetchPRs } from "../services/prs.service";
import type { PullRequest } from "../types/PullRequest";

export const usePRs = () => {
  const [data, setData] = useState<PullRequest[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const load = async () => {
    const requestId = ++requestIdRef.current;

    try {
      setLoading(true);
      setError(null);
      const res = await fetchPRs();

      if (requestId !== requestIdRef.current) return;

      setData(res);
      setLoading(false);

      void enrichPRsWithRisk(res, (updatedPR) => {
        if (requestId !== requestIdRef.current) return;

        setData((current) => {
          if (!current) return current;
          return current.map((pr) =>
            pr.number === updatedPR.number ? updatedPR : pr,
          );
        });
      })
        .then((enriched) => {
          if (requestId !== requestIdRef.current) return;
          setData(enriched);
        })
        .catch((riskErr) => {
          console.error("Risk enrichment failed:", riskErr);
        });
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setError("Failed to load PRs");
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();

    return () => {
      requestIdRef.current += 1;
    };
  }, []);

  return { data, loading, error, reload: load };
};

export default usePRs;
