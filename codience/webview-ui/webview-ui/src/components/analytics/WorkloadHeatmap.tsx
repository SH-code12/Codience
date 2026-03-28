import React from "react";
import type { WeeklyWorkloadEntry } from "../../types/Reviewers";
import { getWorkloadColor } from "../../utils/workloadColors";

interface Props {
  workload: WeeklyWorkloadEntry[];
}

const WorkloadHeatmap: React.FC<Props> = ({ workload }) => {
  const weeks = ["Week 1", "Week 2", "Week 3", "Week 4"];

  return (
    <div className="heatmap-container">
      <h2 className="section-title">Month Workload</h2>

      <div
        className="heatmap-grid"
        style={{
          gridTemplateColumns: `120px repeat(${workload.length}, 1fr)`,
        }}
      >
        {/* Empty corner */}
        <div />

        {/* Reviewer Headers */}
        {workload.map((reviewer) => (
          <div key={reviewer.reviewerId} className="heatmap-header">
            {reviewer.reviewerName}
          </div>
        ))}

        {/* Week Rows */}
        {weeks.map((week, weekIndex) => (
          <React.Fragment key={week}>
            <div className="heatmap-week-label">{week}</div>

            {workload.map((reviewer) => {
              const value = reviewer.weeklyLoad[weekIndex];

              return (
                <div
                  key={`${reviewer.reviewerId}-${weekIndex}`}
                  className="heatmap-cell"
                  style={{ backgroundColor: getWorkloadColor(value) }}
                >
                  {value}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default WorkloadHeatmap;
