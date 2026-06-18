import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import PRsTable from "../components/prs/PRsTable";
import CardsRow from "../components/ui/CardsRow";
import PRsCharts from "../components/prs/PRsCharts";
import ReviewersList from "../components/reviewers/ReviewersList";
import RiskBarChart from "../components/ui/RiskBarChart";
import type { PullRequest } from "../types/PullRequest";
import "./styles/Dashboard.css";
import { usePRs } from "../hooks/usePRs";

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const projectName: string | null = localStorage.getItem("RepoName");
  const { data: prs, loading, error } = usePRs();
  const [selectedPR, setSelectedPR] = useState<PullRequest | null>(null);
  const [updatedPRs, setUpdatedPRs] = useState<PullRequest[] | null>(prs);
  const [visiblePRs, setVisiblePRs] = useState<PullRequest[] | null>(null);

  useEffect(() => {
    if (!selectedPR && prs && prs.length > 0) {
      setSelectedPR(prs[0]);
    }
  }, [prs]);

  useEffect(() => {
    if (!selectedPR || !prs) return;

    const refreshedPR = prs.find((pr) => pr.number === selectedPR.number);
    if (refreshedPR && refreshedPR !== selectedPR) {
      setSelectedPR(refreshedPR);
    }
  }, [prs, selectedPR?.number]);

  useEffect(() => {
    setUpdatedPRs(prs);
  }, [prs]);
  const userName = localStorage.getItem("User");

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

  const handleRiskUpdate = (newPRs: PullRequest[]) => {
    setUpdatedPRs(newPRs);
  };

  const openReviewerSettings = () => {
    if (!selectedPR) return;

    navigate(`/dashboard/reviewer-settings/${selectedPR.number}`, {
      state: { selectedPR },
    });
  };

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

  const prsPerDay = useMemo(() => {
    const days = 7;
    const now = new Date();
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

  const hasAny = Object.values(counts).some((v) => v > 0);

if (!hasAny) {
  labels.forEach((l) => {
    counts[l] = 0;
  });
}

    return labels.map((l) => ({ date: l, count: counts[l] ?? 0 }));
  }, [visiblePRs, updatedPRs, prs]);

  const openClosedData = useMemo(() => {
    const source = visiblePRs ?? updatedPRs ?? prs ?? [];
    let open = 0;
    let closed = 0;
    source.forEach((p) => {
      if (p.state === "open") open++;
      else closed++;
    });
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
          <div className="userArea">
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
                <div className="blockTitleRow">
                  <h4 className="blockTitle">Recommended Reviewers</h4>
                  <button
                    type="button"
                    className="iconSettingsButton"
                    onClick={openReviewerSettings}
                    disabled={!selectedPR}
                    aria-label="Open reviewer recommendation settings"
                    title="Open reviewer recommendation settings"
                  >
                    <span aria-hidden="true">⚙</span>
                  </button>
                </div>
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
                      <div className="infoLabel">Business Impact</div>
                      <div className="infoValue">
                        {selectedPR.business_impact?.weighted_score}
                      </div>
                    </div>
                    <div className="infoRow">
                      <div className="infoLabel">Impact Tier</div>
                      <div className="infoValue">
                        {selectedPR.business_impact?.tier}
                      </div>
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
