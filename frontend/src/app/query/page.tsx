"use client";

import { useState, useRef, useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Send,
  Zap,
  Search,
  Trophy,
  CheckCircle2,
  Brain,
  Loader2,
  FileText,
} from "lucide-react";
import { streamQuery } from "@/lib/api";

interface PipelineStage {
  id: string;
  label: string;
  icon: React.ElementType;
  status: "waiting" | "running" | "done";
  latency?: number;
  detail?: string;
}

interface Source {
  filename: string;
  page_or_section: string;
  section_title: string;
  relevance_score: number;
  text_preview: string;
}

export default function QueryPage() {
  const [query, setQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const responseRef = useRef<HTMLDivElement>(null);

  // Hydration-safe state initialization
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [response, setResponse] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [tokensIn, setTokensIn] = useState(0);
  const [tokensOut, setTokensOut] = useState(0);
  const [totalLatency, setTotalLatency] = useState(0);
  const [stages, setStages] = useState<PipelineStage[]>([
    { id: "embedding", label: "Query Embedding", icon: Zap, status: "waiting" },
    { id: "retrieval", label: "Hybrid Search", icon: Search, status: "waiting" },
    { id: "reranking", label: "Reranking", icon: Trophy, status: "waiting" },
    { id: "grading", label: "Context Grading", icon: CheckCircle2, status: "waiting" },
    { id: "generation", label: "LLM Generation", icon: Brain, status: "waiting" },
  ]);

  const [isMounted, setIsMounted] = useState(false);

  // Load state from sessionStorage ONLY on the client after first render
  useEffect(() => {
    setIsMounted(true);
    const saved = sessionStorage.getItem("query_state");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed.submittedQuery) setSubmittedQuery(parsed.submittedQuery);
        if (parsed.response) setResponse(parsed.response);
        if (parsed.sources) setSources(parsed.sources);
        if (parsed.tokensIn !== undefined) setTokensIn(parsed.tokensIn);
        if (parsed.tokensOut !== undefined) setTokensOut(parsed.tokensOut);
        if (parsed.totalLatency !== undefined) setTotalLatency(parsed.totalLatency);
        if (parsed.stages) {
          const iconMap: Record<string, any> = { embedding: Zap, retrieval: Search, reranking: Trophy, grading: CheckCircle2, generation: Brain };
          setStages(parsed.stages.map((s: any) => ({ ...s, icon: iconMap[s.id] || Zap })));
        }
      } catch (e) {}
    }
  }, []);

  // Save state to sessionStorage when it changes
  useEffect(() => {
    if (!isMounted) return; // Prevent overwriting with empty state on initial mount
    const stateToSave = {
      submittedQuery,
      response,
      sources,
      tokensIn,
      tokensOut,
      totalLatency,
      stages: stages.map(({ icon, ...rest }) => rest), // Remove non-serializable icon
    };
    sessionStorage.setItem("query_state", JSON.stringify(stateToSave));
  }, [submittedQuery, response, sources, tokensIn, tokensOut, totalLatency, stages, isMounted]);

  useEffect(() => {
    if (responseRef.current) {
      responseRef.current.scrollTop = responseRef.current.scrollHeight;
    }
  }, [response]);

  const resetPipeline = () => {
    setStages((prev) =>
      prev.map((s) => ({ ...s, status: "waiting" as const, latency: undefined, detail: undefined }))
    );
    setResponse("");
    setSources([]);
    setTokensIn(0);
    setTokensOut(0);
    setTotalLatency(0);
    setSubmittedQuery("");
  };

  const updateStage = (stageId: string, updates: Partial<PipelineStage>) => {
    setStages((prev) =>
      prev.map((s) => (s.id === stageId ? { ...s, ...updates } : s))
    );
  };

  const handleSubmit = () => {
    if (!query.trim() || isStreaming) return;
    const currentQuery = query.trim();
    resetPipeline();
    setSubmittedQuery(currentQuery);
    setQuery(""); // Clear input immediately
    setIsStreaming(true);

    streamQuery(
      currentQuery,
      (data) => {
        const stage = data.stage as string;
        const status = data.status as string;

        if (stage === "generation" && data.token) {
          setResponse((prev) => prev + (data.token as string));
          setTokensOut((prev) => prev + 1);
        }

        if (status === "running") {
          updateStage(stage, { status: "running" });
        }
        if (status === "done" && stage !== "complete") {
          updateStage(stage, {
            status: "done",
            latency: data.latency_ms as number | undefined,
            detail: data.detail ? JSON.stringify(data.detail) : undefined,
          });
        }

        if (stage === "complete" && data.detail) {
          // Mark generation as done when the complete event arrives
          updateStage("generation", { status: "done" });

          const detail = data.detail as { metrics?: Record<string, number>; sources?: Source[] };
          if (detail.metrics) {
            setTokensIn(detail.metrics.tokens_in ?? 0);
            setTokensOut(detail.metrics.tokens_out ?? 0);
            setTotalLatency(detail.metrics.latency_total_ms ?? 0);
            updateStage("generation", { status: "done", latency: detail.metrics.latency_generation_ms });
          }
          if (detail.sources) {
            setSources(detail.sources as Source[]);
          }
        }
      },
      () => setIsStreaming(false),
      (err) => {
        setResponse((prev) => prev + `\n\n[Error: ${err}]`);
        setIsStreaming(false);
      }
    );
  };

  if (!isMounted) return null;

  return (
    <div className="flex h-screen">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col p-6">
        <h1 className="text-xl font-bold mb-4">
          <span className="text-primary">AI</span> Query
        </h1>

        {/* Response Area */}
        <Card className="glass border-border/50 flex-1 mb-4 overflow-hidden">
          <ScrollArea className="h-full p-5" ref={responseRef}>
            {submittedQuery ? (
              <div className="space-y-4">
                {/* User Message Bubble */}
                <div className="flex justify-end">
                  <div className="max-w-[75%] px-4 py-2.5 rounded-2xl rounded-br-sm bg-primary/20 border border-primary/30">
                    <p className="text-sm text-foreground">{submittedQuery}</p>
                  </div>
                </div>

                {/* AI Response */}
                {response ? (
                  <div className="flex justify-start">
                    <div className="max-w-[85%]">
                      <div className="prose prose-invert prose-sm max-w-none whitespace-pre-wrap">
                        {response}
                        {isStreaming && (
                          <span className="inline-block w-2 h-4 bg-primary animate-pulse-neon ml-0.5" />
                        )}
                      </div>
                    </div>
                  </div>
                ) : isStreaming ? (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-2 text-muted-foreground text-sm">
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                      Processing your query...
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                Ask a question about your documents...
              </div>
            )}

            {/* Sources */}
            {sources.length > 0 && (
              <div className="mt-6 pt-4 border-t border-border/50">
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">
                  Sources
                </p>
                <div className="grid gap-2">
                  {sources.map((src, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-lg bg-secondary/50 border border-border/30"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <FileText className="h-3.5 w-3.5 text-primary" />
                        <span className="text-xs font-medium">{src.filename}</span>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                          {src.page_or_section}
                        </Badge>
                        <span className="text-[10px] text-neon-green ml-auto">
                          {(src.relevance_score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-[11px] text-muted-foreground line-clamp-2">
                        {src.text_preview}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </ScrollArea>
        </Card>

        {/* Input */}
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder="Ask about your documents..."
            className="flex-1 px-4 py-3 rounded-lg bg-input border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all"
          />
          <Button
            onClick={handleSubmit}
            disabled={isStreaming || !query.trim()}
            className="px-5 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Token Counter Bar */}
        <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
          <div className="flex gap-4">
            <span>
              Input: <span className="text-neon-cyan font-mono">{tokensIn}</span> tokens
            </span>
            <span>
              Output: <span className="text-neon-violet font-mono">{tokensOut}</span> tokens
            </span>
            <span>
              Total: <span className="text-foreground font-mono">{tokensIn + tokensOut}</span>
            </span>
          </div>
          {totalLatency > 0 && (
            <span>
              Latency: <span className="text-neon-green font-mono">{(totalLatency / 1000).toFixed(2)}s</span>
            </span>
          )}
        </div>
      </div>

      {/* Pipeline Visualization Panel */}
      <div className="w-72 border-l border-border p-4 flex flex-col">
        <h2 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider">
          Processing Pipeline
        </h2>

        <div className="space-y-1">
          {stages.map((stage, i) => (
            <div key={stage.id}>
              <div
                className={`flex items-center gap-3 p-3 rounded-lg transition-all duration-300 ${
                  stage.status === "running"
                    ? "bg-primary/10 border border-primary/30"
                    : stage.status === "done"
                    ? "bg-neon-green/5 border border-neon-green/20"
                    : "bg-secondary/30 border border-transparent"
                }`}
              >
                {/* Status Indicator */}
                <div className="relative">
                  {stage.status === "running" ? (
                    <Loader2 className="h-4 w-4 text-primary animate-spin" />
                  ) : stage.status === "done" ? (
                    <CheckCircle2 className="h-4 w-4 text-neon-green" />
                  ) : (
                    <stage.icon className="h-4 w-4 text-muted-foreground/40" />
                  )}
                </div>

                {/* Label */}
                <div className="flex-1 min-w-0">
                  <p
                    className={`text-xs font-medium ${
                      stage.status === "waiting"
                        ? "text-muted-foreground/40"
                        : "text-foreground"
                    }`}
                  >
                    {stage.label}
                  </p>
                </div>

                {/* Latency */}
                {stage.latency !== undefined && (
                  <span className="text-[10px] font-mono text-neon-cyan">
                    {stage.latency.toFixed(0)}ms
                  </span>
                )}
              </div>

              {/* Connector line */}
              {i < stages.length - 1 && (
                <div className="flex justify-center py-0.5">
                  <div
                    className={`w-px h-3 ${
                      stages[i + 1].status !== "waiting"
                        ? "bg-neon-green/40"
                        : "bg-border/30"
                    }`}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
