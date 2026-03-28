import React from "react";
import MetricCard from "./MetricCard";

type CardItem = {
  label: string;
  value: React.ReactNode;
  className?: string;
};

interface Props {
  items: CardItem[];
}

const CardsRow: React.FC<Props> = ({ items }) => {
  return (
    <div className="cardsContainer">
      {items.map((it, idx) => (
        <MetricCard
          key={idx}
          label={it.label}
          value={it.value}
          className={it.className}
        />
      ))}
    </div>
  );
};

export default CardsRow;
