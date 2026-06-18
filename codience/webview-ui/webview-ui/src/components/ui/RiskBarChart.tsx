import React from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";

interface Item {
  level: string;
  range?: string | number;
  count: number;
}

interface Props {
  data: Item[];
}

const RiskBarChart: React.FC<Props> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
        <CartesianGrid stroke="#1a1a1a" />
        <XAxis dataKey="level" tick={{ fill: "#bbb", fontSize: 12 }} />
        <YAxis tick={{ fill: "#bbb", fontSize: 12 }} allowDecimals={false} />
        <Tooltip />
        <Bar dataKey="count" radius={[8, 8, 0, 0]}>
          {data.map((entry) => {
            const color =
              entry.level === "low"
                ? "#298f22"
                : entry.level === "medium"
                  ? "#b06a35"
                  : "#821b1b";
            return <Cell key={entry.level} fill={color} />;
          })}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default RiskBarChart;
