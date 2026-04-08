"use client";

import {
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = [
  "#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#4f46e5",
];

type Props = {
  chartType: "bar" | "line" | "pie";
  data: Array<Record<string, unknown>>;
  xKey: string;
  yKey: string;
  title?: string;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function toNumber(value: unknown): number | null {
  if (isFiniteNumber(value)) return value;

  if (value && typeof value === "object") {
    const objectValue = value as Record<string, unknown>;
    const literal = objectValue.literalNumber;
    if (isFiniteNumber(literal)) return literal;

    const literalString = objectValue.literalString;
    if (typeof literalString === "string") {
      const parsedLiteral = toNumber(literalString);
      if (parsedLiteral !== null) return parsedLiteral;
    }

    const nestedValue = objectValue.value;
    if (nestedValue !== undefined) {
      const parsedNested = toNumber(nestedValue);
      if (parsedNested !== null) return parsedNested;
    }
  }

  if (typeof value === "string") {
    const cleaned = value.replace(/,/g, "").trim();
    const direct = Number(cleaned);
    if (Number.isFinite(direct)) return direct;

    const match = cleaned.match(/-?\d+(\.\d+)?/);
    if (match) {
      const extracted = Number(match[0]);
      if (Number.isFinite(extracted)) return extracted;
    }
  }

  return null;
}

function toLabel(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);

  if (value && typeof value === "object") {
    const objectValue = value as Record<string, unknown>;
    const literal = objectValue.literalString;
    if (typeof literal === "string" && literal.trim()) return literal.trim();
  }

  return fallback;
}

function inferKeys(
  rows: Array<Record<string, unknown>>,
  requestedXKey: string,
  requestedYKey: string
): { xKey: string; yKey: string; data: Array<Record<string, unknown>>; hasNumeric: boolean } {
  if (rows.length === 0) {
    return { xKey: requestedXKey, yKey: requestedYKey, data: [], hasNumeric: false };
  }

  const keys = Array.from(new Set(rows.flatMap((row) => Object.keys(row))));

  const yCandidates = keys.filter((key) => rows.some((row) => toNumber(row[key]) !== null));
  const resolvedYKey = yCandidates.includes(requestedYKey)
    ? requestedYKey
    : yCandidates[0] ?? requestedYKey;

  const xCandidates = keys.filter((key) => key !== resolvedYKey);
  const preferredX = [requestedXKey, "name", "label", "category", "module"];
  const resolvedXKey = preferredX.find((key) => xCandidates.includes(key)) ?? xCandidates[0] ?? "__label";

  const hasNumeric = rows.some((row) => toNumber(row[resolvedYKey]) !== null);

  const normalized = rows.map((row, index) => {
    const numeric = toNumber(row[resolvedYKey]);
    return {
      ...row,
      [resolvedYKey]: numeric ?? 0,
      [resolvedXKey]: toLabel(row[resolvedXKey], `Item ${index + 1}`),
    };
  });

  return { xKey: resolvedXKey, yKey: resolvedYKey, data: normalized, hasNumeric };
}

function truncateLabel(text: string, max = 22): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}...`;
}

function formatMetric(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2);
}

export default function RechartGraph({ chartType, data, xKey, yKey, title }: Props) {
  const safeRows = Array.isArray(data) ? data.filter((row) => row && typeof row === "object") : [];
  const resolved = inferKeys(safeRows as Array<Record<string, unknown>>, xKey, yKey);

  const labels = resolved.data.map((row) => String(row[resolved.xKey] ?? ""));
  const maxLabelLength = labels.reduce((max, value) => Math.max(max, value.length), 0);

  const barRows = resolved.data
    .map((row, index) => {
      const parsed = toNumber(row[resolved.yKey]);
      if (parsed === null) return null;
      return {
        label: toLabel(row[resolved.xKey], `Item ${index + 1}`),
        value: parsed,
        color: COLORS[index % COLORS.length],
      };
    })
    .filter((row): row is { label: string; value: number; color: string } => row !== null);

  const maxBarValue = Math.max(1, ...barRows.map((row) => Math.abs(row.value)));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
      {title ? <p className="mb-3 text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</p> : null}

      {!resolved.hasNumeric ? (
        <div className="rounded-lg border border-dashed border-slate-300 px-3 py-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-300">
          Chart data is missing a numeric metric to plot.
        </div>
      ) : chartType === "bar" ? (
        <div className="overflow-x-auto">
          <div className="min-w-[560px] space-y-3">
            {barRows.map((row, index) => {
              const percent = Math.max(2, Math.round((Math.abs(row.value) / maxBarValue) * 100));
              return (
                <div key={`${row.label}-${index}`} className="grid grid-cols-[140px_1fr_64px] items-center gap-3">
                  <div className="truncate text-xs font-medium text-slate-600 dark:text-slate-300" title={row.label}>
                    {row.label}
                  </div>
                  <div className="h-6 rounded-md bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-full rounded-md"
                      style={{
                        width: `${percent}%`,
                        backgroundColor: row.color,
                        boxShadow: "inset 0 0 0 1px rgba(0,0,0,0.08)",
                      }}
                    />
                  </div>
                  <div className="text-right text-xs font-semibold text-slate-700 dark:text-slate-200">
                    {formatMetric(row.value)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          {chartType === "pie" ? (
            <PieChart margin={{ top: 12, right: 24, bottom: 16, left: 24 }}>
              <Pie
                data={resolved.data}
                dataKey={resolved.yKey}
                nameKey={resolved.xKey}
                cx="50%"
                cy="50%"
                outerRadius={110}
                label
              >
                {resolved.data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip wrapperStyle={{ zIndex: 40 }} />
              <Legend />
            </PieChart>
          ) : (
            <LineChart data={resolved.data} margin={{ top: 12, right: 24, bottom: 40, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey={resolved.xKey}
                tick={{ fontSize: 12 }}
                tickFormatter={(value) => truncateLabel(String(value))}
                interval={0}
                angle={maxLabelLength > 14 ? -15 : 0}
                textAnchor={maxLabelLength > 14 ? "end" : "middle"}
                height={maxLabelLength > 14 ? 70 : 40}
              />
              <YAxis tick={{ fontSize: 12 }} width={50} />
              <Tooltip wrapperStyle={{ zIndex: 40 }} />
              <Legend />
              <Line
                type="monotone"
                dataKey={resolved.yKey}
                stroke={COLORS[0]}
                strokeWidth={3}
                dot={{ fill: COLORS[0], r: 4 }}
                activeDot={{ r: 6 }}
                isAnimationActive={false}
              />
            </LineChart>
          )}
        </ResponsiveContainer>
      )}
    </div>
  );
}