interface Props {
  title: string;
  value: string | number;
  highlightColor?: string;
}

const StatsCard: React.FC<Props> = ({ title, value, highlightColor }) => {
  return (
    <div className="stats-card">
      <p className="stats-title">{title}</p>
      <h2 style={{ color: highlightColor }}>{value}</h2>
    </div>
  );
};

export default StatsCard;
