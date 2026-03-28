import React, { useEffect, useMemo, useState } from "react";
import PRsTable from "../components/prs/PRsTable";
import CardsRow from "../components/ui/CardsRow";
import PRsCharts from "../components/prs/PRsCharts";
import ReviewersList from "../components/reviewers/ReviewersList";
import RiskBarChart from "../components/ui/RiskBarChart";
import type { PullRequest } from "../types/PullRequest";
import "./styles/Dashboard.css";
import { usePRs } from "../hooks/usePRs";

// Reviewer fetching moved into ReviewersList component

const Dashboard: React.FC = () => {
  const projectName: string | null = localStorage.getItem("RepoName");
  const { data: prs, loading, error } = usePRs();
  const [selectedPR, setSelectedPR] = useState<PullRequest | null>(null);
  // reviewers state and loading moved into ReviewersList component

  // 🧩 NEW: local copy of PRs that includes risk updates
  const [updatedPRs, setUpdatedPRs] = useState<PullRequest[] | null>(prs);
  // visiblePRs: the PRs after table filtering (if provided)
  const [visiblePRs, setVisiblePRs] = useState<PullRequest[] | null>(null);

  // Select first PR by default when PRs arrive
  useEffect(() => {
    if (!selectedPR && prs && prs.length > 0) {
      setSelectedPR(prs[0]);
    }
    // keep dependency only on prs to run when list changes
  }, [prs]);

  useEffect(() => {
    setUpdatedPRs(prs);
  }, [prs]);
  const userName = localStorage.getItem("User");

  // 🧠 Compute stats using the UPDATED PRs (not the initial ones)
  const stats = useMemo(() => {
    let open = 0;
    let highRisk = 0;
    let highPriority = 0;
    if (!updatedPRs) return { open, highRisk, highPriority };
    updatedPRs.forEach((p) => {
      if (p.state === "open") open++;
      const anyP = p as any;
      if (anyP?.risk?.risk_level === "high") highRisk++;
    });
    return { open, highRisk, highPriority };
  }, [updatedPRs]);

  const handleSelectPR = (pr: PullRequest) => {
    setSelectedPR(pr);
  };

  // 🧩 Handler to receive risk updates from PRsTable
  const handleRiskUpdate = (newPRs: PullRequest[]) => {
    setUpdatedPRs(newPRs);
  };

  // 🔁 Fetch reviewers when selectedPR changes
  /*
  // Original reviewers fetch logic (kept commented to avoid external API calls):
  useEffect(() => {
    if (!selectedPR) {
      setReviewers(null);
      setReviewersError(null);
      setLoadingReviewers(false);
      return;
    }

    let cancelled = false;
    setLoadingReviewers(true);
    setReviewersError(null);

    const body = {
      number: selectedPR.number,
      title: selectedPR.title,
    };

    axios
      .post<ReviewersResponse>(REVIEWERS_API, body, {
        headers: { "Content-Type": "application/json" },
        timeout: 8000,
      })
      .then((res) => {
        if (cancelled) return;
        const arr = res.data?.topReviewers ?? [];
        arr.sort((a, b) => b.confidence - a.confidence);
        setReviewers(arr);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error("Reviewers fetch error:", err);
        setReviewersError("Failed to load recommended reviewers");
        setReviewers(null);
      })
      .finally(() => {
        if (!cancelled) setLoadingReviewers(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedPR]);
  */

  // reviewers fetching/logic moved into ReviewersList component

  // Build chart data: one bar per risk level. For each level compute min-max score and count.
  const chartData = useMemo(() => {
    const levels = ["low", "medium", "high"] as const;
    const source = visiblePRs ?? updatedPRs;
    if (!source) {
      return levels.map((l) => ({ level: l, range: "-", count: 0 }));
    }

    return levels.map((level) => {
      const prsForLevel = source.filter(
        (p) => (p as any)?.risk?.risk_level === level,
      );
      if (prsForLevel.length === 0) return { level, range: "-", count: 0 };

      const scores = prsForLevel
        .map((p) => {
          const raw = (p as any)?.risk?.risk_score;
          const s = typeof raw === "string" ? parseFloat(raw) : raw;
          return Number.isFinite(s) ? Math.max(0, Math.min(100, s)) : null;
        })
        .filter((v): v is number => v !== null && v !== undefined);

      if (scores.length === 0)
        return { level, range: "-", count: prsForLevel.length };

      const min = Math.min(...scores);
      const max = Math.max(...scores);
      return {
        level,
        range: `${Math.round(min)}-${Math.round(max)}`,
        count: prsForLevel.length,
      };
    });
  }, [visiblePRs, updatedPRs]);

  // Line chart: number of PRs per day (dummy-friendly). Uses updatedPRs dates when available,
  // otherwise falls back to a simple distribution across the last 7 days.
  const prsPerDay = useMemo(() => {
    const days = 7;
    const now = new Date();
    // build labels for the last `days` days
    const labels: string[] = [];
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - i);
      labels.push(
        d.toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      );
    }

    const counts: Record<string, number> = {};
    labels.forEach((l) => (counts[l] = 0));

    const source = visiblePRs ?? updatedPRs ?? prs ?? [];
    source.forEach((pr) => {
      const date = pr.createdAt ? new Date(pr.createdAt) : null;
      if (!date || Number.isNaN(date.getTime())) return;
      const label = date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      });
      if (counts[label] === undefined) counts[label] = 0;
      counts[label]++;
    });

    // If no PRs had dates, fabricate a gentle dummy distribution
    const hasAny = Object.values(counts).some((v) => v > 0);
    if (!hasAny) {
      // gentle ramp-up dummy counts
      labels.forEach(
        (l, idx) =>
          (counts[l] = Math.max(
            1,
            Math.round((idx + 1) * ((prs?.length ?? 5) / days)),
          )),
      );
    }

    return labels.map((l) => ({ date: l, count: counts[l] ?? 0 }));
  }, [visiblePRs, updatedPRs, prs]);

  // Pie data for open vs closed PRs
  const openClosedData = useMemo(() => {
    const source = visiblePRs ?? updatedPRs ?? prs ?? [];
    let open = 0;
    let closed = 0;
    source.forEach((p) => {
      if (p.state === "open") open++;
      else closed++;
    });
    // ensure non-zero values for chart visibility
    if (open === 0 && closed === 0) {
      open = 1;
      closed = 0;
    }
    return [
      { name: "Open", value: open },
      { name: "Closed", value: closed },
    ];
  }, [visiblePRs, updatedPRs, prs]);

  if (loading) return <p className="loading">Loading...</p>;
  if (error) return <p className="loading">{error}</p>;

  return (
    <div className="dashboardRoot">
      <main className="mainArea">
        <header className="topHeader">
          <h2 className="projectTitle">{projectName ?? "ProjectName"}</h2>
          <div className="searchUser">
            <input placeholder="Search..." className="searchInput" />
            <div className="userBadge">{userName}</div>
          </div>
        </header>

        <section className="topCardsAndTable">
          <div className="leftColumn">
            <CardsRow
              items={[
                {
                  label: "Your PRs",
                  value: updatedPRs ? updatedPRs.length : 0,
                },
                { label: "Open PRs", value: stats.open, className: "open" },
                {
                  label: "High Priority",
                  value: stats.highPriority,
                  className: "highRisk",
                },
                {
                  label: "High Risk",
                  value: stats.highRisk,
                  className: "highRisk",
                },
              ]}
            />
            <div className="pullRequestsPanel">
              <div className="panelHeader">
                <h3>Pull Requests</h3>
              </div>
              <div className="prsTableWrapper">
                <PRsTable
                  prs={prs}
                  onSelect={handleSelectPR}
                  onRiskUpdate={handleRiskUpdate}
                  onVisibleChange={(v) => setVisiblePRs(v)}
                />
                <PRsCharts
                  prsPerDay={prsPerDay}
                  openClosedData={openClosedData}
                />
              </div>
            </div>
          </div>

          <div className="rightColumn">
            <aside className="rightPanel">
              <div className="recommendedBlock">
                <h4 className="blockTitle">Recommended Reviewers</h4>
                <div className="reviewersBox">
                  <ReviewersList selectedPR={selectedPR} />
                </div>
              </div>

              <div className="prInfoBlock">
                <h4 className="blockTitle">PR Info</h4>
                {selectedPR ? (
                  <div className="prInfoCard">
                    <div className="infoRow">
                      <div className="infoLabel">Risk Score</div>
                      <div className="infoValue">
                        {selectedPR.risk?.risk_score}
                      </div>
                    </div>
                    <div className="infoRow">
                      <div className="infoLabel">#Files Changed</div>
                      <div className="infoValue">
                        {selectedPR.files_changed}
                      </div>
                    </div>
                    <div className="infoRow">
                      <div className="infoLabel">Risk Level</div>
                      <div className="infoValue">
                        {selectedPR.risk?.risk_level}
                      </div>
                    </div>
                    <div className="infoRow">
                      <div className="infoLabel">Assigned Reviewer</div>
                      <div className="infoValue">Not Assigned Yet</div>
                    </div>
                  </div>
                ) : (
                  <div className="noSelection">Select a PR to view details</div>
                )}
              </div>
            </aside>
            <div className="bottomChartContainer">
              <RiskBarChart data={chartData} />
            </div>
          </div>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;
