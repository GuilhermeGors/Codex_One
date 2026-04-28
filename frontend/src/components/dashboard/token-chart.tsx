"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface Props {
  history: Array<{
    tokens_in: number;
    tokens_out: number;
    latency_total_ms: number;
  }>;
}

export function TokenChart({ history }: Props) {
  const data = history.map((h, i) => ({
    query: `Q${i + 1}`,
    input: h.tokens_in,
    output: h.tokens_out,
    total: h.tokens_in + h.tokens_out,
  }));

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
        No queries yet. Start asking questions to see token analytics.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorInput" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="oklch(0.75 0.15 195)" stopOpacity={0.4} />
            <stop offset="95%" stopColor="oklch(0.75 0.15 195)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorOutput" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="oklch(0.65 0.25 290)" stopOpacity={0.4} />
            <stop offset="95%" stopColor="oklch(0.65 0.25 290)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.25 0.015 260)" />
        <XAxis
          dataKey="query"
          stroke="oklch(0.5 0 0)"
          fontSize={10}
          tickLine={false}
        />
        <YAxis stroke="oklch(0.5 0 0)" fontSize={10} tickLine={false} />
        <Tooltip
          contentStyle={{
            background: "oklch(0.15 0.01 260)",
            border: "1px solid oklch(0.25 0.015 260)",
            borderRadius: "8px",
            fontSize: "12px",
          }}
        />
        <Area
          type="monotone"
          dataKey="input"
          stroke="oklch(0.75 0.15 195)"
          fillOpacity={1}
          fill="url(#colorInput)"
          name="Tokens In"
        />
        <Area
          type="monotone"
          dataKey="output"
          stroke="oklch(0.65 0.25 290)"
          fillOpacity={1}
          fill="url(#colorOutput)"
          name="Tokens Out"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
