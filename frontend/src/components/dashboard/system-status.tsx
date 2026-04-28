"use client";

import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, XCircle, Cpu, Database, Eye } from "lucide-react";

interface Health {
  status: string;
  version: string;
  components: {
    ollama: { status: string; model: string };
    chromadb: { status: string; chunks: number };
    langfuse: { status: string };
  };
}

export function SystemStatus({ health }: { health: Health | null }) {
  if (!health) {
    return (
      <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
        Connecting to backend...
      </div>
    );
  }

  const components = [
    {
      name: "Ollama LLM",
      icon: Cpu,
      status: health.components.ollama.status,
      detail: health.components.ollama.model,
    },
    {
      name: "ChromaDB",
      icon: Database,
      status: health.components.chromadb.status,
      detail: `${health.components.chromadb.chunks} chunks`,
    },
    {
      name: "Langfuse",
      icon: Eye,
      status: health.components.langfuse.status,
      detail: health.components.langfuse.status,
    },
  ];

  return (
    <div className="space-y-3">
      {components.map((comp, i) => (
        <div key={comp.name}>
          <div className="flex items-center justify-between py-1">
            <div className="flex items-center gap-2.5">
              <comp.icon className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">{comp.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">{comp.detail}</span>
              {comp.status === "up" || comp.status === "configured" ? (
                <CheckCircle2 className="h-4 w-4 text-neon-green" />
              ) : (
                <XCircle className="h-4 w-4 text-destructive" />
              )}
            </div>
          </div>
          {i < components.length - 1 && <Separator className="bg-border/50" />}
        </div>
      ))}

      <Separator className="bg-border/50" />

      <div className="flex items-center justify-between pt-1">
        <span className="text-xs text-muted-foreground">Version</span>
        <Badge variant="outline" className="text-xs border-primary/30 text-primary">
          v{health.version}
        </Badge>
      </div>
    </div>
  );
}
