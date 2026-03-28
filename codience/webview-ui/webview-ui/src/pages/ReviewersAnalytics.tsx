import ReviewerTable from "../components/analytics/ReviewerTable";
import StatsCard from "../components/analytics/StatsCard";
import WorkloadHeatmap from "../components/analytics/WorkloadHeatmap";
import { useReviewersAnalytics } from "../hooks/useReviewersAnalytics";
import { getWorkloadColor } from "../utils/workloadColors";
import "./styles/ReviewersAnlaytics.css";
const RepoName = localStorage.getItem("RepoName");

const ReviewersAnalytics = () => {
  const { data, loading, error } = useReviewersAnalytics();

  if (loading) return <p className="loading">Loading...</p>;
  if (error || !data) return <p>{error}</p>;

  const { workload } = data;

  // 🔥 Calculate overloads (values > 10)
  const overloadCount = workload.reduce((count, reviewer) => {
    return count + reviewer.weeklyLoad.filter((value) => value > 10).length;
  }, 0);

  // 🔥 Calculate average PRs per reviewer
  const avgPRs =
    workload.reduce((sum, reviewer) => {
      const total = reviewer.weeklyLoad.reduce((acc, value) => acc + value, 0);
      return sum + total;
    }, 0) / workload.length;

  const roundedAvg = Math.round(avgPRs);
  return (
    <div className="analytics-page">
      <div className="analytics-left">
        <h2 className="projectTitle">{RepoName ?? "ProjectName"}</h2>
        <div className="analytics-container">
          <div className="analytics-content">
            <div className="analytics-stats">
              <StatsCard title="Recommendation Accuracy" value={`70%`} />
              <StatsCard
                title="Avg PRs / Reviewer"
                value={roundedAvg}
                highlightColor={getWorkloadColor(roundedAvg)}
              />
              <StatsCard
                title="Overloads"
                value={overloadCount}
                highlightColor={getWorkloadColor(11)}
              />
            </div>
            <div className="analytics-main">
              <h2 className="section-title">Team Reviewers</h2>
              <ReviewerTable reviewers={data.reviewers} />
              <WorkloadHeatmap workload={data.workload} />{" "}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReviewersAnalytics;
