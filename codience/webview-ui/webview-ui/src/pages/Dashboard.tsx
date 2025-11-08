import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import PRsTable from "../components/PRsTable";
import type { PullRequest } from "../types/PullRequest";
import "./styles/Dashboard.css";

interface Props {
  prs: PullRequest[] | null;
  projectName: string | null;
}

type ReviewerEntry = {
  confidence: number;
  reviewerName: string;
};

type ReviewersResponse = {
  skills: string[];
  topReviewers: ReviewerEntry[];
};

const REVIEWERS_API =
  "https://fordless-samella-unexpendable.ngrok-free.dev/api/recommend";

const Dashboard: React.FC<Props> = ({ prs, projectName }) => {
  const [selectedPR, setSelectedPR] = useState<PullRequest | null>(null);
  const [reviewers, setReviewers] = useState<ReviewerEntry[] | null>(null);
  const [loadingReviewers, setLoadingReviewers] = useState(false);
  const [reviewersError, setReviewersError] = useState<string | null>(null);

  // 🧩 NEW: local copy of PRs that includes risk updates
  const [updatedPRs, setUpdatedPRs] = useState<PullRequest[] | null>(prs);

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

  const renderReviewersRows = () => {
    if (loadingReviewers) {
      return (
        <tr className="loadingRow">
          <td colSpan={3}>Loading recommended reviewers…</td>
        </tr>
      );
    }
    if (reviewersError) {
      return (
        <tr className="errorRow">
          <td colSpan={3}>{reviewersError}</td>
        </tr>
      );
    }
    if (!reviewers || reviewers.length === 0) {
      return (
        <tr className="emptyRow">
          <td colSpan={3}>No recommended reviewers found for this PR.</td>
        </tr>
      );
    }
    return reviewers.map((r, idx) => (
      <tr key={r.reviewerName + idx}>
        <td className="revName">{r.reviewerName}</td>
        <td className="revConfidence">{(r.confidence * 100).toFixed(1)}%</td>
        <td className="revActions"></td>
      </tr>
    ));
  };

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
          <div className="cardsContainer">
            <div className="card statCard">
              <div className="cardLabel">Your PRs</div>
              <div className="cardValue">
                {updatedPRs ? updatedPRs.length : 0}
              </div>
            </div>
            <div className="card statCard open">
              <div className="cardLabel">Open PRs</div>
              <div className="cardValue">{stats.open}</div>
            </div>
            <div className="card statCard highRisk">
              <div className="cardLabel">High Priority</div>
              <div className="cardValue">{stats.highPriority}</div>
            </div>
            <div className="card statCard highRisk">
              <div className="cardLabel">High Risk</div>
              <div className="cardValue">{stats.highRisk}</div>
            </div>
          </div>

          <div className="tableAndRightPanel">
            <div className="pullRequestsPanel">
              <div className="panelHeader">
                <h3>Pull Requests</h3>
              </div>
              <div className="prsTableWrapper">
                <PRsTable
                  prs={prs}
                  onSelect={handleSelectPR}
                  onRiskUpdate={handleRiskUpdate} // 👈 pass callback
                />
              </div>
            </div>

            <aside className="rightPanel">
              <div className="recommendedBlock">
                <h4 className="blockTitle">Recommended Reviewers</h4>
                <div className="reviewersBox">
                  {selectedPR ? (
                    <>
                      <div className="selectedPRBrief">
                        <div className="prNumber">#{selectedPR.number}</div>
                        <div className="prTitle">{selectedPR.title}</div>
                        <div className="prState">{selectedPR.state}</div>
                      </div>

                      <table className="reviewersTable">
                        <thead>
                          <tr>
                            <th>Reviewer</th>
                            <th>Confidence</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>{renderReviewersRows()}</tbody>
                      </table>
                    </>
                  ) : (
                    <div className="noSelection">
                      Click a PR to see recommended reviewers
                    </div>
                  )}
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
          </div>
        </section>
      </main>
    </div>
  );
};

export default Dashboard;
