import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

interface Props {
  prsPerDay: { date: string; count: number }[];
  openClosedData: { name: string; value: number }[];
}

const PRsCharts: React.FC<Props> = ({ prsPerDay, openClosedData }) => {
  return (
    <div
      style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12 }}
    >
      <div style={{ flex: 1, height: 160 }}>
        <ResponsiveContainer>
          <LineChart
            data={prsPerDay}
            margin={{ top: 6, right: 6, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#222" />
            <XAxis dataKey="date" tick={{ fill: "#bbb", fontSize: 12 }} />
            <YAxis tick={{ fill: "#bbb", fontSize: 12 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#57B36A"
              strokeWidth={2}
              dot={{ r: 3, fill: "#57B36A" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ width: 160, height: 160 }}>
        <ResponsiveContainer>
          <PieChart>
            <Pie
              data={openClosedData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={36}
              outerRadius={56}
              label={false}
            >
              {openClosedData.map((entry) => {
                const color = entry.name === "Open" ? "#298f22" : "#821b1b";
                return <Cell key={entry.name} fill={color} />;
              })}
            </Pie>
            <Tooltip />
            <Legend
              verticalAlign="bottom"
              align="center"
              wrapperStyle={{ color: "#bbb", fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default PRsCharts;
