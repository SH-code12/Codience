import type { Reviewer } from "../../types/Reviewers";

interface Props {
  reviewers: Reviewer[];
}

const ReviewerTable: React.FC<Props> = ({ reviewers }) => {
  return (
    <table className="reviewer-table">
      <thead>
        <tr>
          <th>Reviewer</th>
          <th>No. of Reviewed PRs</th>
          <th>Avg Review Time</th>
          <th>No. of AI Recommendations</th>
        </tr>
      </thead>
      <tbody>
        {reviewers.map((r) => (
          <tr key={r.id}>
            <td>{r.name}</td>
            <td>{r.reviewedPRs}</td>
            <td>{r.avgReviewTime}</td>
            <td>{r.aiRecommendations}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default ReviewerTable;
