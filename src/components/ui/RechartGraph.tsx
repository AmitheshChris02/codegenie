"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

type ChartType = "bar" | "line" | "pie";

type Props = {
  chartType: ChartType;
  data: Array<Record<string, unknown>>;
  xKey?: string;
  yKey?: string;
  title?: string;
};

const COLORS = ["#319696", "#4cb0b0", "#7fcaca", "#acdfdf", "#226265"];

export default function RechartGraph({ chartType, data, xKey = "name", yKey = "value", title }: Props) {
  const chart =
    chartType === "bar" ? (
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#64748b44" />
        <XAxis dataKey={xKey} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey={yKey} fill={COLORS[0]} radius={[8, 8, 0, 0]} />
      </BarChart>
    ) : chartType === "line" ? (
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#64748b44" />
        <XAxis dataKey={xKey} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey={yKey} stroke={COLORS[1]} strokeWidth={3} />
      </LineChart>
    ) : (
      <PieChart>
        <Tooltip />
        <Legend />
        <Pie data={data} dataKey={yKey} nameKey={xKey} outerRadius={110} fill={COLORS[0]} label />
      </PieChart>
    );

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      {title ? <h3 className="mb-3 text-sm font-semibold text-slate-900 dark:text-slate-100">{title}</h3> : null}
      <div className="h-72 w-full">
        <ResponsiveContainer>{chart}</ResponsiveContainer>
      </div>
    </div>
  );
}
