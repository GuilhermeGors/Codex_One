"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  ShieldAlert,
  AlertTriangle,
  FileWarning,
  Activity,
  TerminalSquare,
  Search,
} from "lucide-react";

interface ThreatFinding {
  threat_id: string;
  name: string;
  category: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  description: string;
  matched_text: string;
  context_snippet: string;
  filename: string;
  page: string;
  detected_at: string;
}

interface ThreatSummary {
  total_threats: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  risk_score: number;
  affected_documents: string[];
  findings: ThreatFinding[];
}

export default function SecurityDashboardPage() {
  const [data, setData] = useState<ThreatSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchThreats = () => {
    fetch("http://localhost:8000/api/v1/metrics/threats")
      .then((res) => res.json())
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        console.error("Failed to fetch threat intelligence", e);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchThreats();
    const interval = setInterval(fetchThreats, 5000); // Polling every 5s
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        Loading Threat Intelligence...
      </div>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "text-red-500 border-red-500/30 bg-red-500/10";
      case "HIGH":
        return "text-orange-500 border-orange-500/30 bg-orange-500/10";
      case "MEDIUM":
        return "text-yellow-500 border-yellow-500/30 bg-yellow-500/10";
      default:
        return "text-blue-500 border-blue-500/30 bg-blue-500/10";
    }
  };

  return (
    <div className="p-6 h-screen flex flex-col max-w-[1600px] mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <ShieldAlert className="h-6 w-6 text-red-500 animate-pulse" />
          <span className="text-red-500">Security</span> Intelligence
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Real-time pattern-based threat detection engine scanning documents prior to vectorization.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="glass border-red-500/30">
          <CardContent className="p-6 flex flex-col justify-center items-center h-full">
            <span className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Total Threats Detected</span>
            <span className="text-5xl font-mono text-red-500">{data?.total_threats || 0}</span>
          </CardContent>
        </Card>

        <Card className="glass border-orange-500/30">
          <CardContent className="p-6 flex flex-col justify-center items-center h-full">
            <span className="text-sm text-muted-foreground uppercase tracking-wider mb-2">Aggregate Risk Score</span>
            <span className="text-5xl font-mono text-orange-500">{data?.risk_score || 0}</span>
          </CardContent>
        </Card>

        <Card className="glass border-border/50 col-span-2">
          <CardContent className="p-6">
            <span className="text-sm text-muted-foreground uppercase tracking-wider mb-4 block">Threats by Category</span>
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(data?.by_category || {}).length > 0 ? (
                Object.entries(data!.by_category).map(([cat, count]) => (
                  <div key={cat} className="flex justify-between items-center bg-secondary/50 p-2 rounded">
                    <span className="text-sm font-medium">{cat}</span>
                    <Badge variant="outline" className="text-neon-cyan border-neon-cyan/30">{count}</Badge>
                  </div>
                ))
              ) : (
                <div className="col-span-2 text-sm text-muted-foreground text-center py-4">No threats detected.</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        {/* Affected Files List */}
        <Card className="glass border-border/50 lg:col-span-1 flex flex-col overflow-hidden min-h-0 h-full">
          <CardHeader className="py-4 border-b border-border/50">
            <CardTitle className="text-sm flex items-center gap-2">
              <FileWarning className="h-4 w-4 text-orange-500" />
              Compromised Documents
            </CardTitle>
          </CardHeader>
          <ScrollArea className="h-full p-4 flex-1">
            <div className="space-y-3">
              {data?.affected_documents?.length ? (
                data.affected_documents.map((doc, i) => (
                  <div key={i} className="p-3 bg-red-500/5 border border-red-500/20 rounded-lg flex items-start gap-3">
                    <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-foreground break-all">{doc}</p>
                      <p className="text-[10px] text-muted-foreground mt-1 uppercase tracking-wider">Quarantined / Tagged</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-sm text-muted-foreground py-8">
                  All documents are clean.
                </div>
              )}
            </div>
          </ScrollArea>
        </Card>

        {/* Detailed Threat Logs */}
        <Card className="glass border-border/50 lg:col-span-2 flex flex-col overflow-hidden min-h-0 h-full">
          <CardHeader className="py-4 border-b border-border/50 flex flex-row items-center justify-between">
            <CardTitle className="text-sm flex items-center gap-2">
              <Activity className="h-4 w-4 text-neon-cyan" />
              Threat Inspection Logs
            </CardTitle>
            <Badge variant="outline" className="text-xs">
              Latest {data?.findings?.length || 0} Events
            </Badge>
          </CardHeader>
          <ScrollArea className="h-full p-4 flex-1">
            <div className="space-y-4">
              {data?.findings?.length ? (
                // Reverse to show newest first
                [...data.findings].reverse().map((finding, i) => (
                  <div key={i} className={`p-4 rounded-lg border ${getSeverityColor(finding.severity).replace('text-', 'border-').split(' ')[1]}`}>
                    
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={getSeverityColor(finding.severity)}>
                          {finding.severity}
                        </Badge>
                        <span className="text-sm font-bold text-foreground">{finding.name}</span>
                      </div>
                      <span className="text-xs font-mono text-muted-foreground">
                        {new Date(finding.detected_at).toLocaleTimeString()}
                      </span>
                    </div>

                    <p className="text-xs text-muted-foreground mb-3">{finding.description}</p>

                    <div className="bg-background/50 rounded p-3 mb-3 border border-border/50">
                      <div className="flex items-center gap-2 mb-2">
                        <TerminalSquare className="h-3 w-3 text-neon-violet" />
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">Payload Context Snippet</span>
                      </div>
                      <p className="text-xs font-mono text-foreground break-all">
                        {/* Highlight the matched payload */}
                        {finding.context_snippet.split(finding.matched_text).map((part, index, array) => (
                          <span key={index}>
                            {part}
                            {index < array.length - 1 && (
                              <span className="bg-red-500/20 text-red-400 px-1 rounded mx-0.5 font-bold">
                                {finding.matched_text}
                              </span>
                            )}
                          </span>
                        ))}
                      </p>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground border-t border-border/30 pt-2">
                      <div className="flex items-center gap-1">
                        <Search className="h-3 w-3" />
                        <span>File: <span className="text-foreground">{finding.filename}</span> (Pg: {finding.page})</span>
                      </div>
                      <span className="font-mono">ID: {finding.threat_id}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <ShieldAlert className="h-12 w-12 text-muted-foreground/30 mb-4" />
                  <p>No security threats detected in document ingestion pipeline.</p>
                </div>
              )}
            </div>
          </ScrollArea>
        </Card>
      </div>
    </div>
  );
}
