import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import ReviewersList from "../components/reviewers/ReviewersList";
import { usePrSummary } from "../hooks/usePrSummary";
import { fetchBusinessImpactForPR } from "../services/prs.service";
import type { BusinessImpactType } from "../types/BusinessImpactType";
import type { PullRequest } from "../types/PullRequest";
import "./styles/PrSummaryDetails.css";

type LocationState = {
  selectedPR?: PullRequest;
};

const renderSummary = (summary: string) => {
  return summary.split("\n").map((line, index) => {
    const trimmed = line.trim();

    if (!trimmed) return <br key={index} />;

    if (trimmed.startsWith("**") && trimmed.endsWith("**")) {
      return <h3 key={index}>{trimmed.replace(/\*\*/g, "")}</h3>;
    }

    if (trimmed.startsWith("- ")) {
      return (
        <p key={index} className="prSummaryBullet">
          {trimmed.slice(2)}
        </p>
      );
    }

    return <p key={index}>{trimmed.replace(/\*\*/g, "")}</p>;
  });
};

const PrSummaryDetails = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { prNumber } = useParams();
  const selectedPR = (location.state as LocationState | null)?.selectedPR ?? null;
  const parsedPrNumber = Number(prNumber);
  const [businessImpact, setBusinessImpact] =
    useState<BusinessImpactType | null>(selectedPR?.business_impact ?? null);
  const prForReviewers =
    (selectedPR
      ? { ...selectedPR, business_impact: businessImpact }
      : null) ??
    (Number.isFinite(parsedPrNumber)
      ? {
          number: parsedPrNumber,
          title: `PR #${parsedPrNumber}`,
          state: "",
          createdAt: "",
          name: "",
          files_changed: 0,
          risk: null,
          business_impact: null,
        }
      : null);
  const { summary, loading, error } = usePrSummary(
    Number.isFinite(parsedPrNumber) ? parsedPrNumber : null,
  );

  const pageTitle = prForReviewers?.title ?? `PR #${prNumber ?? ""}`;

  useEffect(() => {
    if (!Number.isFinite(parsedPrNumber)) return;

    const currentScore = businessImpact?.weighted_score;
    if (
      currentScore !== undefined &&
      currentScore !== null &&
      currentScore !== "Loading..."
    ) {
      return;
    }

    let cancelled = false;

    fetchBusinessImpactForPR(parsedPrNumber)
      .then((nextBusinessImpact) => {
        if (!cancelled) {
          setBusinessImpact(nextBusinessImpact);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setBusinessImpact({
            weighted_score: "N/A",
            tier: "unknown",
            ai_summary: "Business impact is unavailable.",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [parsedPrNumber, businessImpact?.weighted_score]);

  return (
    <div className="prSummaryPage">
      <section className="prSummaryCard">
        <header className="prSummaryHeader">
          <div>
            <p className="prSummaryEyebrow">Pull request summary</p>
            <h2>{pageTitle}</h2>
            <span>#{prNumber}</span>
          </div>
          <button
            type="button"
            className="prSummaryBackButton"
            onClick={() => navigate(-1)}
          >
            Back
          </button>
        </header>

        <div className="prSummaryGrid">
          <article className="prSummaryPanel">
            <h3>Summary</h3>
            {loading && <div className="prSummaryState">Loading summary...</div>}
            {error && <div className="prSummaryState prSummaryError">{error}</div>}
            {!loading && !error && summary && (
              <div className="prSummaryText">{renderSummary(summary)}</div>
            )}
            {!loading && !error && !summary && (
              <div className="prSummaryState">No summary returned for this PR.</div>
            )}
          </article>

          <aside className="prSummaryPanel">
            <h3>Recommended Reviewers</h3>
            <ReviewersList selectedPR={prForReviewers} />
          </aside>

          <article className="prSummaryPanel prSummaryFullWidth">
            <h3>Business Impact</h3>
            <div className="prSummaryText">
              <p>
                <strong>Weighted Score:</strong>{" "}
                {prForReviewers?.business_impact?.weighted_score ?? "Loading..."}
              </p>
              <p>
                <strong>Tier:</strong>{" "}
                {prForReviewers?.business_impact?.tier ?? "Loading..."}
              </p>
              <p>
                <strong>AI Summary:</strong>{" "}
                {prForReviewers?.business_impact?.ai_summary ?? "Loading..."}
              </p>
            </div>
          </article>
        </div>
      </section>
    </div>
  );
};

export default PrSummaryDetails;
