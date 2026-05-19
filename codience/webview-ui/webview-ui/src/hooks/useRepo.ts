import { useCallback, useState } from "react";

export const useRepo = (initial?: string | null) => {
  const getStored = () => initial ?? localStorage.getItem("RepoName");
  const [repo, setRepoState] = useState<string | null>(getStored());

  const setRepo = useCallback((value: string) => {
    localStorage.setItem("RepoName", value);
    setRepoState(value);
    try {
      window.dispatchEvent(new CustomEvent("repoChanged", { detail: value }));
    } catch (e) {
      // ignore in environments without window/custom events
    }
  }, []);

  const clearRepo = useCallback(() => {
    localStorage.removeItem("RepoName");
    setRepoState(null);
  }, []);

  return { repo, setRepo, clearRepo };
};

export default useRepo;
