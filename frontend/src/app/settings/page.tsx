"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Cpu,
  Brain,
  Database,
  Layers,
  Shield,
  Zap,
  HardDrive,
  Server,
} from "lucide-react";

interface SystemConfig {
  app_name: string;
  app_version: string;
  ollama_model: string;
  embed_model: string;
  llm_temperature: number;
  llm_context_window: number;
  llm_max_tokens: number;
  chunk_size: number;
  chunk_overlap: number;
  top_k_retrieval: number;
  top_k_rerank: number;
  top_k_retrieval: number;
  top_k_rerank: number;
  langfuse_enabled: boolean;
  pii_scrubbing: boolean;
  quarantine_enabled: boolean;
}

export default function SettingsPage() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [togglingQuarantine, setTogglingQuarantine] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/health")
      .then((res) => res.json())
      .then((data) => {
        // Build config from health and known defaults
        setConfig({
          app_name: data.app || "Codex One v2",
          app_version: data.version || "2.0.0",
          ollama_model: "phi4-mini",
          embed_model: "nomic-embed-text",
          llm_temperature: 0.2,
          llm_context_window: 8192,
          llm_max_tokens: 2048,
          chunk_size: 512,
          chunk_overlap: 64,
          top_k_retrieval: 20,
          top_k_rerank: 5,
          langfuse_enabled: data.components?.langfuse?.status === "configured",
          pii_scrubbing: true,
          quarantine_enabled: data.security?.quarantine_enabled || false,
        });
        setLoading(false);
      })
      .catch(() => {
        setConfig({
          app_name: "Codex One v2",
          app_version: "2.0.0",
          ollama_model: "phi4-mini",
          embed_model: "nomic-embed-text",
          llm_temperature: 0.2,
          llm_context_window: 8192,
          llm_max_tokens: 2048,
          chunk_size: 512,
          chunk_overlap: 64,
          top_k_retrieval: 20,
          top_k_rerank: 5,
          langfuse_enabled: true,
          pii_scrubbing: true,
          quarantine_enabled: false,
        });
        setLoading(false);
      });
  }, []);

  const toggleQuarantine = async () => {
    if (!config || togglingQuarantine) return;
    setTogglingQuarantine(true);
    try {
      const newState = !config.quarantine_enabled;
      const res = await fetch(`http://localhost:8000/api/v1/settings/quarantine?enabled=${newState}`, {
        method: "POST",
      });
      if (res.ok) {
        setConfig({ ...config, quarantine_enabled: newState });
      }
    } catch (e) {
      console.error("Failed to toggle quarantine", e);
    } finally {
      setTogglingQuarantine(false);
    }
  };

  if (loading || !config) {
    return (
      <div className="flex items-center justify-center h-screen text-muted-foreground">
        Loading configuration...
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold">
          <span className="text-primary">System</span> Configuration
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Read-only view of the current engine parameters. Edit <code className="text-primary/80 bg-primary/10 px-1.5 py-0.5 rounded text-xs">.env</code> or <code className="text-primary/80 bg-primary/10 px-1.5 py-0.5 rounded text-xs">config.py</code> to change settings.
        </p>
      </div>

      {/* LLM Configuration */}
      <Card className="glass border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4 text-primary" />
            LLM Engine
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <ConfigItem label="Generation Model" value={config.ollama_model} badge="Local" badgeColor="neon-green" />
            <ConfigItem label="Embedding Model" value={config.embed_model} badge="Local" badgeColor="neon-green" />
            <ConfigItem label="Temperature" value={config.llm_temperature.toString()} />
            <ConfigItem label="Context Window" value={`${config.llm_context_window.toLocaleString()} tokens`} />
            <ConfigItem label="Max Output Tokens" value={config.llm_max_tokens.toLocaleString()} />
            <ConfigItem label="Provider" value="Ollama (On-Device)" badge="Zero Egress" badgeColor="neon-cyan" />
          </div>
        </CardContent>
      </Card>

      {/* RAG Pipeline */}
      <Card className="glass border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Layers className="h-4 w-4 text-neon-cyan" />
            RAG Pipeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <ConfigItem label="Chunk Size" value={`${config.chunk_size} characters`} />
            <ConfigItem label="Chunk Overlap" value={`${config.chunk_overlap} characters`} />
            <ConfigItem label="Top-K Retrieval" value={config.top_k_retrieval.toString()} />
            <ConfigItem label="Top-K Rerank" value={config.top_k_rerank.toString()} />
            <ConfigItem label="Search Strategy" value="Hybrid (Dense + BM25)" badge="RRF" badgeColor="neon-violet" />
            <ConfigItem label="Chunking" value="Recursive + Semantic" />
          </div>
        </CardContent>
      </Card>

      {/* Privacy & Observability */}
      <Card className="glass border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Shield className="h-4 w-4 text-neon-green" />
            Privacy & Observability
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <ConfigItem label="PII Scrubbing" value={config.pii_scrubbing ? "Enabled" : "Disabled"} badge={config.pii_scrubbing ? "Presidio" : undefined} badgeColor="neon-green" />
            
            <div className="flex flex-col gap-1">
              <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
                Threat Quarantine Gate
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={toggleQuarantine}
                  disabled={togglingQuarantine}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${config.quarantine_enabled ? 'bg-red-500' : 'bg-muted'} focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-background disabled:opacity-50`}
                >
                  <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${config.quarantine_enabled ? 'translate-x-4' : 'translate-x-1'}`} />
                </button>
                <span className={`text-sm font-medium ${config.quarantine_enabled ? 'text-red-500' : 'text-muted-foreground'}`}>
                  {config.quarantine_enabled ? "Active (Blocks Threats)" : "Disabled (Log Only)"}
                </span>
                {config.quarantine_enabled && (
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-red-500/30 text-red-500">
                    Strict Mode
                  </Badge>
                )}
              </div>
            </div>

            <ConfigItem label="Langfuse Tracing" value={config.langfuse_enabled ? "Enabled" : "Disabled"} badge="LLMOps" badgeColor="neon-cyan" />
            <ConfigItem label="Audit Logging" value="JSONL (Append-Only)" badge="LGPD" badgeColor="neon-green" />
            <ConfigItem label="Token Counter" value="tiktoken (Precise)" />
          </div>
        </CardContent>
      </Card>

      {/* Hardware Profile */}
      <Card className="glass border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Cpu className="h-4 w-4 text-neon-violet" />
            Hardware Profile
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <ConfigItem label="CPU" value="Intel i5 12th Gen" />
            <ConfigItem label="GPU" value="GTX 3050 4GB VRAM" />
            <ConfigItem label="Docker CPU Limit" value="4 Cores" />
            <ConfigItem label="Docker RAM Limit" value="4 GB" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ConfigItem({
  label,
  value,
  badge,
  badgeColor,
}: {
  label: string;
  value: string;
  badge?: string;
  badgeColor?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] text-muted-foreground uppercase tracking-wider">
        {label}
      </span>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-foreground">{value}</span>
        {badge && (
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 border-${badgeColor}/30 text-${badgeColor}`}
          >
            {badge}
          </Badge>
        )}
      </div>
    </div>
  );
}
