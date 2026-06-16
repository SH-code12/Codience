import { useLocation, useNavigate, useParams } from "react-router-dom";
import ReviewersList from "../components/reviewers/ReviewersList";
import { usePrSummary } from "../hooks/usePrSummary";
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
  const prForReviewers =
    selectedPR ??
    (Number.isFinite(parsedPrNumber)
      ? {
          number: parsedPrNumber,
          title: `PR #${parsedPrNumber}`,
          state: "",
          createdAt: "",
          name: "",
          files_changed: 0,
          risk: null,
        }
      : null);
  const { summary, loading, error } = usePrSummary(
    Number.isFinite(parsedPrNumber) ? parsedPrNumber : null,
  );

  const pageTitle = prForReviewers?.title ?? `PR #${prNumber ?? ""}`;

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
        </div>
      </section>
    </div>
  );
};

export default PrSummaryDetails;
