"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Zap,
  Clock,
  Shield,
  FileText,
  Activity,
  Cpu,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";
import { TokenChart } from "@/components/dashboard/token-chart";
import { SystemStatus } from "@/components/dashboard/system-status";

interface Metrics {
  total_queries: number;
  total_documents: number;
  total_chunks: number;
  avg_latency_ms: number;
  total_tokens_processed: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_saved_usd: number;
  queries_history: Array<{
    tokens_in: number;
    tokens_out: number;
    latency_total_ms: number;
  }>;
}

interface Health {
  status: string;
  version: string;
  components: {
    ollama: { status: string; model: string };
    chromadb: { status: string; chunks: number };
    langfuse: { status: string };
  };
}

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [m, h] = await Promise.all([
          api.getPipelineMetrics(),
          api.getHealth(),
        ]);
        setMetrics(m);
        setHealth(h);
      } catch {
        /* backend not running */
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const kpis = [
    {
      label: "Tokens Processed",
      value: metrics?.total_tokens_processed?.toLocaleString() ?? "0",
      icon: Zap,
      color: "text-neon-cyan",
      bgColor: "bg-neon-cyan/10",
      glowClass: "glow-cyan",
    },
    {
      label: "Avg Latency",
      value: metrics?.avg_latency_ms ? `${(metrics.avg_latency_ms / 1000).toFixed(2)}s` : "0s",
      icon: Clock,
      color: "text-neon-violet",
      bgColor: "bg-neon-violet/10",
      glowClass: "glow-violet",
    },
    {
      label: "Documents",
      value: metrics?.total_documents?.toString() ?? "0",
      icon: FileText,
      color: "text-neon-green",
      bgColor: "bg-neon-green/10",
      glowClass: "",
    },
    {
      label: "Total Chunks",
      value: metrics?.total_chunks?.toLocaleString() ?? "0",
      icon: Cpu,
      color: "text-neon-pink",
      bgColor: "bg-neon-pink/10",
      glowClass: "",
    },
    {
      label: "Cost Saved",
      value: `$${(metrics?.total_cost_saved_usd ?? 0).toFixed(4)}`,
      icon: TrendingUp,
      color: "text-neon-green",
      bgColor: "bg-neon-green/10",
      glowClass: "",
      subtitle: "vs GPT-4o",
    },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            <span className="text-primary">Codex</span>{" "}
            <span className="text-foreground">One</span>
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Enterprise RAG Intelligence Dashboard
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            variant="outline"
            className={`${
              health?.status === "healthy"
                ? "border-neon-green text-neon-green"
                : "border-destructive text-destructive"
            }`}
          >
            <Activity className="h-3 w-3 mr-1" />
            {health?.status ?? "connecting..."}
          </Badge>
          <Badge variant="outline" className="border-primary text-primary">
            <Shield className="h-3 w-3 mr-1" />
            100% Local
          </Badge>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {kpis.map((kpi) => (
          <Card
            key={kpi.label}
            className={`glass border-border/50 ${kpi.glowClass} transition-all hover:scale-[1.02]`}
          >
            <CardContent className="p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    {kpi.label}
                  </p>
                  <p className={`text-2xl font-bold mt-1 ${kpi.color}`}>
                    {kpi.value}
                  </p>
                </div>
                <div className={`p-2.5 rounded-lg ${kpi.bgColor}`}>
                  <kpi.icon className={`h-5 w-5 ${kpi.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Token Usage Chart */}
        <Card className="glass border-border/50 lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              Token Usage Over Time
            </CardTitle>
            <CardDescription className="text-xs">
              Input vs Output tokens per query
            </CardDescription>
          </CardHeader>
          <CardContent>
            <TokenChart history={metrics?.queries_history ?? []} />
          </CardContent>
        </Card>

        {/* System Status */}
        <Card className="glass border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Cpu className="h-4 w-4 text-neon-violet" />
              System Components
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SystemStatus health={health} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
