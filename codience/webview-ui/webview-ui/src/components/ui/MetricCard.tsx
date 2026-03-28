import React from "react";
import "../styles/MetricCard.css";

interface Props {
  label: string;
  value: React.ReactNode;
  className?: string;
}

const MetricCard: React.FC<Props> = ({ label, value, className }) => {
  return (
    <div className={`metricCard card ${className ?? ""}`.trim()}>
      <div className="cardLabel">{label}</div>
      <div className="cardValue">{value}</div>
    </div>
  );
};

export default MetricCard;
