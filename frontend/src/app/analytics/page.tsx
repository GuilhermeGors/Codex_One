"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart3,
  TrendingUp,
  Zap,
  Clock,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { api } from "@/lib/api";

export default function AnalyticsPage() {
  const [tokenData, setTokenData] = useState<{
    total_tokens_in: number;
    total_tokens_out: number;
    total_tokens: number;
    avg_tokens_per_query: number;
    total_queries: number;
    cost_analysis?: {
      cloud_equivalent?: Record<string, number>;
      savings_vs_gpt4o?: number;
    };
    history: Array<{ tokens_in: number; tokens_out: number; latency_ms: number }>;
  } | null>(null);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        setTokenData(await api.getTokenUsage());
      } catch { /* offline */ }
    };
    fetch_();
    const iv = setInterval(fetch_, 5000);
    return () => clearInterval(iv);
  }, []);

  const chartData = (tokenData?.history ?? []).map((h, i) => ({
    query: `Q${i + 1}`,
    input: h.tokens_in,
    output: h.tokens_out,
    latency: h.latency_ms,
  }));

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-bold">
        <span className="text-neon-violet">Token</span> Analytics
      </h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        {[
          { label: "Total Queries", value: tokenData?.total_queries ?? 0, icon: BarChart3, color: "text-primary" },
          { label: "Tokens In", value: tokenData?.total_tokens_in?.toLocaleString() ?? "0", icon: Zap, color: "text-neon-cyan" },
          { label: "Tokens Out", value: tokenData?.total_tokens_out?.toLocaleString() ?? "0", icon: TrendingUp, color: "text-neon-violet" },
          { label: "Avg / Query", value: tokenData?.avg_tokens_per_query?.toFixed(0) ?? "0", icon: Clock, color: "text-neon-green" },
        ].map((item) => (
          <Card key={item.label} className="glass border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <item.icon className={`h-5 w-5 ${item.color}`} />
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{item.label}</p>
                  <p className={`text-lg font-bold ${item.color}`}>{item.value}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Token Distribution Bar Chart */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Token Distribution</CardTitle>
            <CardDescription className="text-xs">Input vs Output per query</CardDescription>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="flex items-center justify-center h-[220px] text-muted-foreground text-sm">
                No data yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.25 0.015 260)" />
                  <XAxis dataKey="query" stroke="oklch(0.5 0 0)" fontSize={10} />
                  <YAxis stroke="oklch(0.5 0 0)" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      background: "oklch(0.15 0.01 260)",
                      border: "1px solid oklch(0.25 0.015 260)",
                      borderRadius: "8px",
                      fontSize: "11px",
                    }}
                  />
                  <Bar dataKey="input" fill="oklch(0.75 0.15 195)" radius={[4, 4, 0, 0]} name="Input" />
                  <Bar dataKey="output" fill="oklch(0.65 0.25 290)" radius={[4, 4, 0, 0]} name="Output" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Latency Line Chart */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Latency Trend</CardTitle>
            <CardDescription className="text-xs">End-to-end response time (ms)</CardDescription>
          </CardHeader>
          <CardContent>
            {chartData.length === 0 ? (
              <div className="flex items-center justify-center h-[220px] text-muted-foreground text-sm">
                No data yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.25 0.015 260)" />
                  <XAxis dataKey="query" stroke="oklch(0.5 0 0)" fontSize={10} />
                  <YAxis stroke="oklch(0.5 0 0)" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      background: "oklch(0.15 0.01 260)",
                      border: "1px solid oklch(0.25 0.015 260)",
                      borderRadius: "8px",
                      fontSize: "11px",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="latency"
                    stroke="oklch(0.7 0.2 350)"
                    strokeWidth={2}
                    dot={{ fill: "oklch(0.7 0.2 350)", r: 3 }}
                    name="Latency (ms)"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Cost Savings + LGPD */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Cost Comparison */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Cost Comparison: Local vs Cloud</CardTitle>
            <CardDescription className="text-xs">
              What this would cost on cloud APIs
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { name: "Codex One (Local)", cost: "$0.0000", color: "text-neon-green", highlight: true },
                { name: "GPT-4o", cost: `$${((tokenData?.cost_analysis?.cloud_equivalent?.["gpt-4o"] ?? 0) as number).toFixed(4)}`, color: "text-destructive", highlight: false },
                { name: "GPT-4o-mini", cost: `$${((tokenData?.cost_analysis?.cloud_equivalent?.["gpt-4o-mini"] ?? 0) as number).toFixed(4)}`, color: "text-muted-foreground", highlight: false },
                { name: "Claude 3.5 Sonnet", cost: `$${((tokenData?.cost_analysis?.cloud_equivalent?.["claude-3.5-sonnet"] ?? 0) as number).toFixed(4)}`, color: "text-muted-foreground", highlight: false },
              ].map((row) => (
                <div
                  key={row.name}
                  className={`flex items-center justify-between p-2.5 rounded-lg ${
                    row.highlight ? "bg-neon-green/5 border border-neon-green/20" : "bg-secondary/30"
                  }`}
                >
                  <span className="text-sm">{row.name}</span>
                  <span className={`text-sm font-mono font-bold ${row.color}`}>{row.cost}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* LGPD + Privacy */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Privacy & Compliance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { label: "Data Processing", value: "100% Local", badge: "LGPD" },
                { label: "External API Calls", value: "Zero", badge: "Privacy" },
                { label: "Data Sovereignty", value: "On-Device Only", badge: "Secure" },
                { label: "Audit Trail", value: "Full Traceability", badge: "Compliant" },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-muted-foreground">{item.label}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm">{item.value}</span>
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-neon-green/30 text-neon-green">
                      {item.badge}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
