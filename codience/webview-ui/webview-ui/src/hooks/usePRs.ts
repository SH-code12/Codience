import { useEffect, useState } from "react";
import {
  enrichPRsWithFilesChanged,
  enrichPRsWithRisk,
  fetchPRs,
} from "../services/prs.service";
import type { PullRequest } from "../types/PullRequest";

type PRCache = {
  data: PullRequest[] | null;
  loading: boolean;
  error: string | null;
  promise: Promise<PullRequest[]> | null;
  repo: string | null;
  subscribers: Set<() => void>;
};

const prCache: PRCache = {
  data: null,
  loading: true,
  error: null,
  promise: null,
  repo: null,
  subscribers: new Set(),
};

const emitPRCacheUpdate = () => {
  prCache.subscribers.forEach((subscriber) => subscriber());
};

const setPRCache = (next: Partial<Pick<PRCache, "data" | "loading" | "error" | "promise" | "repo">>) => {
  Object.assign(prCache, next);
  emitPRCacheUpdate();
};

const isResolvedFilesChanged = (value: PullRequest["files_changed"]) =>
  typeof value === "number" || value === "Error";

const mergePRCacheItem = (updatedPR: PullRequest) => {
  if (!prCache.data) return;

  setPRCache({
    data: prCache.data.map((pr) => {
      if (pr.number !== updatedPR.number) return pr;

      const nextFilesChanged = isResolvedFilesChanged(pr.files_changed)
        ? pr.files_changed
        : updatedPR.files_changed;

      const mergedRisk = {
        risk_score: updatedPR.risk?.risk_score ?? pr.risk?.risk_score ?? "N/A",
        risk_level:
          updatedPR.risk?.risk_level ?? pr.risk?.risk_level ?? "unknown",
        comments: updatedPR.risk?.comments ?? pr.risk?.comments ?? 0,
        files_changed: nextFilesChanged,
      };

      return {
        ...pr,
        ...updatedPR,
        files_changed: nextFilesChanged,
        risk: mergedRisk,
      };
    }),
  });
};

export const usePRs = () => {
  const [data, setData] = useState<PullRequest[] | null>(prCache.data);
  const [loading, setLoading] = useState(prCache.loading);
  const [error, setError] = useState<string | null>(prCache.error);

  const syncFromCache = () => {
    setData(prCache.data);
    setLoading(prCache.loading);
    setError(prCache.error);
  };

  const load = async (force = false) => {
    const currentRepo = localStorage.getItem("RepoName");

    if (!force && prCache.repo && currentRepo && prCache.repo !== currentRepo) {
      force = true;
    }

    if (!force) {
      if (prCache.data) {
        syncFromCache();
        return prCache.data;
      }

      if (prCache.promise) {
        syncFromCache();
        return prCache.promise;
      }
    }

    if (force) {
      setPRCache({ data: null, loading: true, error: null, promise: null, repo: null });
    } else {
      setPRCache({ loading: true, error: null });
    }

    const request = (async () => {
      try {
        const res = await fetchPRs();

        setPRCache({ data: res, loading: false, error: null, repo: currentRepo ?? null });

        void enrichPRsWithFilesChanged(res, (updatedPR) => {
          mergePRCacheItem(updatedPR);
        }).catch((filesErr) => {
          console.error("Files changed enrichment failed:", filesErr);
        });

        void enrichPRsWithRisk(res, (updatedPR) => {
          mergePRCacheItem(updatedPR);
        }).catch((riskErr) => {
          console.error("Risk enrichment failed:", riskErr);
        });

        return res;
      } catch (err) {
        setPRCache({ error: "Failed to load PRs", loading: false });
        throw err;
      } finally {
        setPRCache({ promise: null });
      }
    })();

    setPRCache({ promise: request });
    return request;
  };

  useEffect(() => {
    syncFromCache();
    prCache.subscribers.add(syncFromCache);

    const handleRepoChange = (_e: Event) => {
      void load(true);
    };

    window.addEventListener("repoChanged", handleRepoChange);

    void load();

    return () => {
      prCache.subscribers.delete(syncFromCache);
      window.removeEventListener("repoChanged", handleRepoChange);
    };
  }, []);

  return { data, loading, error, reload: load };
};

export default usePRs;
